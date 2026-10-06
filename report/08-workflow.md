# 8. Agent Workflow and Orchestration

## 8.1 Workflow Design

Four workflows are defined. They share one graph and differ in the paths taken.

### W1 — Résumé to full onboarding

```
supervisor ──▶ resume_agent ──▶ onboarding_agent ──▶ calendar_agent ──▶ END
                (profile)          (10 tasks)          (meetings)
```

**Trigger:** `POST /api/resumes/upload` (HR only).
**Deterministic path.** A linear chain with three conditional exits to `END` on error. There is no branching on success because the sequence is mandatory: a task plan without an employee record is meaningless, and meetings without tasks lose their context.

**Idempotency and duplication.** The graph routes on an error state — specifically, a duplicate-detection error is *not* treated as a workflow failure, so re-uploading the same résumé returns the existing employee rather than creating a second one. This is handled by a routing predicate that inspects the error text, which is admittedly a fragile coupling and is acknowledged as such in Section 13.

### W2 — Leave request with human approval

```
supervisor ──▶ leave_agent ──▶ policy_agent ──▶ leave_agent(decide)
                 (intake)          (context)         │
                                                    │
        ┌──────────── auto-approved / rejected ─────┤
        │            approval required ─────────────┤
        ▼                                           ▼
      END                                   human_approval (interrupt)
                                                        │ UI: Approve / Reject
                                                        ▼
                                                finalize_leave ──▶ END
```

**Trigger:** `POST /api/leave` (HR/manager) or `POST /api/me/leave` (self-service, identity from token).
**The only workflow with a human decision point**, and the only one that requires durable state.

### W3 — Policy question

```
supervisor ──▶ policy_agent ──▶ END
```

**Trigger:** `POST /api/policy/query`. Any authenticated role. Single hop.

### W4 — Generic agent entry

```
supervisor ──▶ (classification) ──▶ appropriate agent ──▶ END
```

**Trigger:** `POST /api/agent/run` (HR only). Exposes the supervisor for free-text requests that do not correspond to a specific UI action.

## 8.2 Task Decomposition

Decomposition is visible in the state object, which has three complementary representations of "what is being worked on". This is not redundancy — each is authoritative for a different purpose.

| State field | Shape | Authoritative for |
|---|---|---|
| `employee_data` | Structured profile dictionary | Record creation, department/role-derived planning |
| `leave_request` | `{employee_id, leave_type, start_date, end_date, reason}` | The leave decision pipeline |
| `result` | Workflow outcome with `leave_request_id`, `status` | Correlating the graph run with the database record |

**Decomposition is per-node, not per-agent.** A single agent may run as two nodes when a step is suspended. The Leave Agent is the clearest case: intake and decide are separate invocations, because intake must complete and *persist* before the policy context is retrieved, and because the decision step must be able to run days later without re-parsing. A single node cannot express "do the cheap part now, the expensive part after approval".

**Granularity is bounded by what must be independently verifiable.** The leave pipeline is decomposed to the point where each step has an independently testable predicate: dates valid, days counted, balance sufficient, approval required. Below that level, decomposition would create steps with nothing to assert.

## 8.3 Agent Coordination

Coordination is by conditional edges — pure functions of state that return a node name. This is the mechanism worth examining, because the obvious alternative (agents calling each other) is worse for testability.

```python
def route_after_policy(state) -> str:
    # policy context retrieved → hand back to the Leave Agent to decide
    return "leave_agent"

def route_after_leave(state) -> str:
    if state.get("requires_human_approval") and state.get("error") is None:
        return "human_approval"     # needs a person
    return END                        # auto-approved or rejected

def route_after_resume(state) -> str:
    if state.get("error") and "already exists" not in state.get("error", ""):
        return END                   # genuine failure
    return "onboarding_agent"        # duplicate is not a failure
```

Three properties follow from this design:

**Coordination is statically visible.** The full set of possible paths is enumerable by reading the `add_conditional_edges` declarations. A reviewer can determine whether a path is reachable without executing anything. With agent-to-agent calls, reachability is a runtime property.

**Routing is pure and side-effect free.** A route function reads state and returns a string. It cannot fail, cannot perform I/O, and cannot partially update state. This eliminates an entire class of bug where a routing error corrupts data before the work even begins.

**Failure is a routing decision, not an exception.** Errors are written into state and converted into an `END` route. The workflow terminates deliberately rather than unwinding, so partial state is inspectable and the failure is logged.

**The cost of this design is a real limitation.** Routing predicates that inspect *message text* — as `route_after_resume` does with `"already exists"` — couple the graph to the wording of an error string. A wording change upstream silently alters control flow. This is the weakest coupling in the orchestration layer and is listed in Section 13 as a specific item to fix by introducing a typed error code in state.

## 8.4 Orchestration Implementation

**Graph construction.** A `StateGraph` is built with 8 nodes and 6 edges, of which 4 are conditional.

```
Nodes : supervisor, resume_agent, onboarding_agent, calendar_agent,
        leave_agent, policy_agent, human_approval, finalize_leave
Edges : supervisor → (4 conditional)
        resume_agent → onboarding_agent | END
        onboarding_agent → calendar_agent | END
        calendar_agent → END
        policy_agent → leave_agent | END
        human_approval → finalize_leave
        finalize_leave → END
```

**Checkpointing and the interrupt.** The `human_approval` node calls LangGraph's `interrupt()`, which raises out of the graph, persists state to the SQLite checkpointer, and returns control to the caller. The API returns the pending request to the UI. When a manager decides, the API calls `resume_workflow(thread_id, decision, decided_by)`, which invokes the graph with `Command(resume=payload)`. Execution resumes at the `interrupt()` call, which now returns the payload instead of raising.

```
POST /api/leave            POST /api/leave/5/approve
        │                            │
  leave_agent                thread_is_interrupted()?
  evaluate_and_create                 │
  requires_approval=True      resume_workflow(thread, "approve", "Priya Sharma (MANAGER)")
        │                            │
  interrupt() ──► CHECKPOINT    Command(resume={decision, decided_by})
  state persisted                  │
  HTTP 201 returned            finalize_leave
                                 decide_leave_request(decided_by="Priya Sharma (MANAGER)")
                                 deduct balance, log, HTTP 200
```

**Interrupt durability.** Because the thread state lives in the checkpointer and the thread ID is stored on the leave row, a pending approval survives a server restart. A manager can approve a request filed days earlier, and the correct execution resumes. This was verified directly: a leave request was created, the process was restarted, and the approval was applied against the original thread.

**A fallback path, and why it exists.** If the checkpoint thread is unavailable — index corrupted, checkpoint DB removed, thread ID stale — the system does not strand the request. It detects the failure, applies the decision directly through `crud.decide_leave_request`, and logs the degraded path explicitly. The trade-off is deliberate: the audit trail records *which* path executed, so a fallback decision is distinguishable from a graph-resumed one. Correctness of the decision is preserved; the provenance detail is reduced.

**Concurrency.** Decisions are guarded against double-application: re-deciding an already-decided request returns HTTP 409. Two managers clicking Approve simultaneously therefore cannot both deduct the balance, because the status transition is checked and committed as one unit.

**The approver's identity is carried through the graph, not around it.** An early implementation recorded `decided_by = "HR Admin"` regardless of who decided, because the `human_approval` node extracted only the `decision` field from the resume payload and discarded the rest. The fix threaded `decided_by` through the interrupt payload into a new `human_decided_by` state field, so the approver survives suspension. The general lesson is recorded in Section 12.3: **an audit trail is only as good as the data you carry across the boundaries, and process boundaries are where that data is usually lost.**
