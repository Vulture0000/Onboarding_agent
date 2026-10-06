# 10. Human-in-the-Loop Leave Approval

## 10.1 Design Rationale

Some decisions in an HR system should not be automated, and leave approval is the clearest case in this project. Two properties make it unsuitable for full automation:

**It is inherently normative.** A four-day absence for a family matter and a four-day absence announced on a Friday are the same request under the policy, and they are very different decisions. The policy supplies the *permitted* set; a human judges whether this request, for this person, at this time, should be permitted. Encoding that judgement as a rule is not a simplification — it is a category error, and it would produce a system that is confidently wrong in exactly the cases where the decision matters.

**Automating it produces a worse outcome than not automating it.** An auto-approving leave system that removes the manager from the loop is not a time-saver; it is a system that generates a technically compliant decision and destroys the manager's awareness of their team's availability. The risk is not regulatory, it is operational.

The design principle adopted is therefore: **automate everything up to the decision, so the decision is informed; never automate the decision itself; and record the decision so it is defensible afterwards.** The system is a *preparation* layer for the human judgement, not a substitute for it.

## 10.2 Interrupt and Resume

The mechanism is LangGraph's `interrupt()`, which is a genuine process suspension rather than an application-level wait.

```
POST /api/leave
  leave_agent: intake → parse → validate dates
  policy_agent: retrieve leave policy context
  leave_agent: evaluate_and_create
      balance check ── insufficient ──▶ REJECTED, return 201, workflow ENDS
      days > 2, balance OK ──▶ PENDING, create record, thread_id = uuid4()
  human_approval node
      interrupt()  ──►  LangGraph persists state to the checkpointer
                          and raises out of the graph
  API returns: { status: "PENDING", requires_approval: true, thread_id, ... }
                          (the HTTP request ends here)
```

```
POST /api/leave/{id}/approve        body: { reason?: str }
  thread_is_interrupted(thread_id)?   ── no ──▶ degraded path, §10.4
  resume_workflow(thread_id, "approve", decided_by)
      Command(resume={ decision, decided_by })
      graph resumes AT the interrupt() call, which now returns the payload
  finalize_leave
      decide_leave_request(id, status, decided_by, reason)
          guard: status must be PENDING, else 409   ← concurrency control
          update status + decided_by + decided_at + reason
          deduct balance
      log to agent_logs
  API returns 200 with the updated request and new balance
```

**Why a graph interrupt rather than a background job or a status flag.** A status flag on a database row — `PENDING_APPROVAL` — could implement the same visible behaviour with far less machinery. The graph interrupt was chosen because it keeps the *entire* workflow context in one place. The decision node has the parsed request, the retrieved policy, the computed working-day count, and the balance snapshot, all as it stood at the moment of the request. A status flag would require re-deriving all of it at decision time, and re-derivation is where a system acquires subtle inconsistencies — a request re-parsed three days later may no longer produce the same dates, or may find a balance changed by other requests. The interrupt preserves the analysis; the flag would discard and re-perform it.

**Durability.** State is checkpointed to SQLite via `langgraph-checkpoint-sqlite`, and the thread ID is stored on the leave record. Verified directly: a request was created, the process was restarted, and the approval was applied against the original thread with the original decision context intact.

## 10.3 Decision Capture

The decision interface is designed around one observation from Section 3.2: a manager will not read a document to approve a request, so the basis of the decision must be present at the point of decision.

The approval payload presented to the approver:

| Field | Purpose |
|---|---|
| Employee, leave type, date range | What is being requested |
| Working days requested | The unit the policy is written in — "4 days", not "next Friday to Tuesday" |
| Current and remaining balance, by type | Whether this is affordable, before deciding |
| Whether notice meets policy | A pre-computed yes/no, not something the approver should work out |
| Retrieved policy excerpt | The rule itself, quoted |
| Roster availability in that period | Whether the team is already short-staffed — context a manager would otherwise have to look up |
| Approve / Reject + optional reason | The decision |

**Every field is pre-computed by code.** The balance arithmetic, the working-day count, and the notice-period check are not generated for the approver to verify; they are the system's findings, and the approver's input is the judgement. Rejection requires a reason, which makes the refusal defensible — "your balance is insufficient" is a fact; "not this quarter" is a decision, and it should be written down.

**Approver scope.** Managers may decide only requests from their own reports; HR may decide any pending request. The check is on the decision path, not in the UI: a manager attempting to decide another team's request receives 403.

## 10.4 The Auditable Decision

The final claim of this design is that an approval decision leaves a complete, attributable record. The `leave_requests` table stores:

```
status        PENDING → APPROVED | REJECTED
decided_by    "Priya Sharma (MANAGER)"   ← name AND role, human-ised
decided_at    timestamp
reason        the approver's text
thread_id     the workflow thread, for replay
```

`decided_by` is stored as a **name and role, not a user ID.** An audit log that records only `user_id: 14` requires a join to a table that may itself be modified, and is unreadable to anyone auditing the system. A human-readable attribution survives that problem and is directly reviewable.

**This field was broken and fixed, and the bug is instructive.** In the original implementation, `human_approval` extracted only the `decision` key from the resume payload and discarded the remainder. The approver's identity never reached the record, so `decided_by` was written as the constant `"HR Admin"` — *regardless of who actually decided*. The system looked compliant and was systematically false: every approval in the database was misattributed.

Three things are worth noting about why this survived into a near-complete system:

- **It fails silently and plausibly.** The value was always populated, so nothing looked broken. Only an audit of the *content* rather than the *presence* of the field exposed it.
- **It was destroyed at a process boundary.** The identity existed in the HTTP request and in the resume payload; it was lost in the hop between the interrupt and the decision node. This is the characteristic failure mode of human-in-the-loop flows — the payload is assembled at one point and consumed at another, and any field not explicitly threaded through is discarded.
- **The fix is a data-flow change, not a control-flow change.** A `human_decided_by` field was added to the graph state, populated from the payload, and read by `finalize_leave`. The graph was correct all along; it was being handed incomplete data.

The generalisable lesson, carried into Section 13 as a design rule: **in a suspending workflow, treat the payload as the audit record, because the payload is the only thing that crosses the suspension boundary.**
