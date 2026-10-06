# 1. Introduction

## 1.1 Background and Motivation

Employee onboarding is one of the most document-heavy processes in any mid-sized organisation. A single new hire typically triggers a chain of work that no individual owns end to end: HR reads a résumé and transcribes it into a database, an HR or IT administrator drafts an onboarding checklist, a coordinator negotiates meeting slots with the hiring manager and the IT helpdesk, and a leave administrator later validates leave balances against written policy before anyone can approve it.

What makes this process fragile is not any single task but the seams between them. Each task usually lives in a different system — an ATS for résumés, a spreadsheet or HRIS for the checklist, a calendar for meetings, a leave-management module, and a shared drive for policy documents. Information that exists once in a résumé has to be re-entered by hand. Leave rules written in a PDF have to be remembered correctly, at 3pm, by someone who has never read them. When any step is skipped or done inconsistently, the error is usually discovered weeks later, by which point it is expensive to correct.

The cost of this fragility is not merely administrative effort. An employee who is not contacted in their first week, or who is sent wrong equipment, or who has their first leave request rejected for a rule they were never shown, disengages quickly. Turnover among new hires is disproportionately expensive because the replacement cost is repeated: new sourcing, new screening, new onboarding, and the lost institutional knowledge of whoever left.

The underlying reason these problems persist is that onboarding is a **multi-step workflow with conditional branching and a human decision in the middle**, and organisations tend to automate the *steps* rather than the *workflow*. Automating résumé parsing in isolation does not help if the parsed profile never becomes a task list. Automating a leave form does not help if approving it still requires a human to recall a policy that may or may not say what they think it says.

## 1.2 Need for Agentic AI

Agentic AI addresses a different problem from conventional automation. A conventional rule or a single-purpose model is invoked once, produces one output, and stops. An *agent* is a component that maintains goal-directed state, selects its own next action from a set of available tools, observes the result, and decides whether to continue, delegate, or escalate. The distinction matters when the work is sequential, conditional, and cross-domain — which onboarding is, at every stage.

Three properties of the onboarding workflow make agentic design the appropriate one:

**Multi-step composition with dependencies.** A résumé upload is not a complete action. It must become an employee record, which must become a task plan, which must become calendar entries. Each step is meaningless alone and the sequence is only correct end to end. An agentic workflow can hold that pipeline as a single unit with explicit state, where a conventional script requires a caller to correctly chain three independent endpoints and handle partial failure at each boundary.

**Conditional branching on domain facts.** Which onboarding tasks a new hire receives depends on their role and department. Whether a leave request can be auto-approved depends on its length, its type, and the employee's remaining balance. These are not conversational nuances; they are business rules that must be applied consistently. A single prompt-and-response model tends to apply them inconsistently, because a language model is a probabilistic function and the rules here are not.

**Genuine human judgement at one specific point.** Some steps in onboarding should not be automated at all. A manager deciding whether to approve a week's leave is a judgement call about a real person. The correct design is not to automate the decision but to build the system so the decision arrives with all the context needed, is attributed to a named human, and is auditable afterwards.

Agentic AI, correctly applied, is therefore not about removing the human from the loop. It is about putting the human in the loop at exactly the one place where judgement is required, and handling the rest deterministically.

## 1.3 Project Objectives

This project set out to build and evaluate a working agentic system for employee onboarding, with the following objectives:

| # | Objective | Success measure |
|---|---|---|
| O1 | Automate résumé-to-onboarding-plan as a single orchestrated workflow | Upload produces a profile, a task plan, and meetings without manual intervention |
| O2 | Handle leave requests end to end, including human approval | Request validated against policy and balance, then paused for a named approver, then resumed |
| O3 | Ground policy answers in the organisation's actual documents | Answers quote retrieved text; queries outside the corpus return a refusal |
| O4 | Enforce access control by role, not by UI convention | Employee, manager, and HR each reach only their own scope; verified by an automated matrix |
| O5 | Degrade gracefully when the LLM is unavailable | All core CRUD, leave, and calendar logic works with no API key |
| O6 | Keep business-critical rules deterministic | Balances, dates, statuses, and approvals computed in code, never by a model |

O5 and O6 together encode a specific architectural stance that the report defends throughout: **the language model is used for the two things it is genuinely good at — unstructured input and natural-language questions — and is excluded from everything that must be reproducible.** This is the central design decision, and Section 12 evaluates what it costs as well as what it buys.
