# 7. Agent Architecture

## 7.1 Agent Components

The system defines 8 graph nodes. Five are agents, one is a router, and two implement the human decision point.

```
                    ┌──────────────┐
        request ───▶│  supervisor  │  classify intent
                    └──────┬───────┘
        ┌──────────┬────────┼────────┬──────────────┐
        ▼          ▼        ▼        ▼              ▼
  resume_agent  policy  calendar  onboarding    leave_agent
        │        agent    agent      agent           │
        │          ▲        │           │        ┌────┴────┐
        │          │        │           │        ▼         ▼
        │          └────────┴───────────┘   (needs policy?)  │
        ▼                                   └────────┬────────┘
  onboarding_agent ──▶ calendar_agent                 ▼
        │                                        human_approval
        ▼                                       (interrupt)
      END                                            │
                                                    ▼
                                            finalize_leave ──▶ END
```

Node inventory:

| Node | Type | Responsibility |
|---|---|---|
| `supervisor` | Router | Classify intent; route to a specialised agent |
| `resume_agent` | Agent | PDF → structured profile → employee record |
| `onboarding_agent` | Agent | Role/department-aware task plan |
| `calendar_agent` | Agent | Schedule against availability constraints |
| `leave_agent` | Agent | Parse, consult policy, apply rules |
| `policy_agent` | Agent | Retrieve and answer from policy corpus |
| `human_approval` | **Interrupt** | Suspend the graph, await a named human decision |
| `finalize_leave` | Agent | Apply the human decision, deduct balance, log |

## 7.2 Tools

Agents have no direct database access. Every side effect goes through one of five tool modules, which is what makes the set of possible state changes enumerable.

| Tool module | Functions | Enforces |
|---|---|---|
| `resume_tools` | PDF text extraction, profile → employee record | Field validation, duplicate detection |
| `employee_tools` | Create employee, assign manager, generate task plan | Role/department templates, ID allocation |
| `calendar_tools` | Availability search, slot finding, meeting CRUD | Working hours (9:00–18:00), lunch break, conflict detection |
| `leave_tools` | Date validation, working-day count, balance check, approval rule, create/decide | **All business rules.** No model involvement |
| `policy_tools` | Corpus loading, chunking, retrieval | Relevance threshold, source attribution |

**The tool layer is the trust boundary.** Because the Leave Agent's decisions are produced by `leave_tools.check_balance` and `leave_tools.requires_human_approval` rather than by a prompt, the leave ledger is reproducible: the same request against the same state yields the same outcome. A prompt asking a model to "check the balance and decide if approval is needed" would produce plausible and occasionally correct answers, with no way to test that property.

## 7.3 Memory

The system uses three distinct memory mechanisms, and conflating them is a common architectural error.

**1. Graph state (working memory).** A single typed object, `OnboardingState`, carrying the current request, the employee being processed, parsed leave intent, retrieved policy context, the accumulated message list, and the human decision when present. It is scoped to one workflow run and is the *only* channel through which agents exchange data. There is no agent-to-agent calling, which means an agent's input is fully determined by the state — a property that makes the whole graph traceable by reading one object.

**2. Checkpointed memory (durable, resumable).** LangGraph's SQLite checkpointer persists state at each step, keyed by a thread ID. This is what makes human-in-the-loop work at all: when a leave request pauses at the interrupt, the state — including the parsed request and the employee context — survives the HTTP request boundary and the process lifetime. The thread ID is stored on the leave record, so a decision made days later resumes the correct execution. Without this, the "resume" would be a simulated step in the same request.

**3. Operational memory (system of record).** The relational database holds employees, tasks, meetings, leave requests and balances, users, and the agent activity log. The activity log is not incidental: it is the artefact that makes the automation auditable, and it is why R12 is satisfiable without modifying agent code — every tool call flows through a layer that can log.

Note what is deliberately **absent**: there is no long-term conversational memory and no per-user memory of prior interactions. For an HR system this is correct. A system that remembered previous exchanges about a leave request would risk surfacing stale balances as current fact.

## 7.4 Reasoning Flow

The canonical reasoning chain for a leave request — the workflow with the most branching — proceeds as follows. Model and code contributions are distinguished, because which is which is the central design question.

```
1.  supervisor          classify intent                       [model + keyword fallback]
      └─ routed to leave_agent

2.  leave_agent         parse "5 days casual next month"       [model — NL → dates]
                         → {type: CASUAL, start, end, reason}
      └─ rule: requests > 2 consecutive days need approval    [code]

3.  policy_agent        retrieve leave policy chunks           [retrieval]
                         → grounded context for the rule

4.  leave_tools         validate dates (not >1yr past)          [code]
                       count working days (excl. weekends)      [code]
                       check balance vs. remaining              [code]
      └─ insufficient → create REJECTED, record reason          [code]
      └─ sufficient + within limit → create + auto-approve      [code]
      └─ sufficient + over limit  → create PENDING, pause       [code]

5.  human_approval      INTERRUPT — checkpoint & suspend        [human]
      └─ awaits named manager/HR via the UI

6.  finalize_leave      apply decision, deduct balance, log      [code]
                         → decided_by = "<name> (<role>)"        [code]
```

**Every step that affects a record or a decision is code.** The model contributes exactly one artefact in this flow: the structured interpretation of the user's sentence. If the model misparses "next month" as the wrong date, the balance check still applies correctly to whatever date it was given — the error is contained rather than propagated.

## 7.5 Agent Interactions

Interactions are governed by three mechanisms, in decreasing order of directness:

| Mechanism | Examples | Coupling |
|---|---|---|
| **Conditional edges** | supervisor → any agent; leave → policy → leave; resume → onboarding → calendar | Explicit routing function, visible in the graph definition |
| **Shared state** | All agent-to-agent data transfer | No direct calls; agents cannot invoke each other |
| **Tool access** | Every DB write and every external call | Uniform interface, uniformly logged |

**There is no A2A protocol, no agent discovery, and no inter-agent messaging.** This is a considered restriction. Multi-agent frameworks commonly support agents calling other agents, which sounds more capable but produces two practical problems: call chains become invisible to static analysis, and a routing bug manifests as a wrong agent's side effects rather than as an error. Constraining agents to act only on shared state means the entire execution path can be read off the graph definition and the state object.

**Coordination, not hierarchy.** The Supervisor is a router, not a manager. It does not assign work, allocate resources, or aggregate results into a report. It classifies and returns. The practical consequence is that adding an agent is a local change — a node, a routing predicate, and a state field — with no modification to the supervisor's logic.

**The human is a graph participant, not an external interrupt.** `human_approval` is a node in the graph like any other. The decision arrives through the same `Command(resume=...)` path as any other input, and the approver's identity is carried in the resumed payload and written to the record. Treating the human as a first-class graph participant is what makes an approval auditable in the same way as an automated action, and it is why the system records `decided_by = "Priya Sharma (MANAGER)"` rather than a generic marker.
