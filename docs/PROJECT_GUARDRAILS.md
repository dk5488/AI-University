# AI University Project Guardrails

## Product Context

AI University is an AI-powered UPSC coaching system. The product behaves like an institute staffed by specialized AI workers:

- Master Agent: routes user intent and coordinates workflows.
- Subject Agents: teach, quiz, revise, and explain subject-specific material.
- Memory Service: owns user progress, learning state, and personalization.
- RAG Service: retrieves trusted source material from books and notes.
- Revision Agent: schedules spaced revision from performance signals.
- API Gateway: exposes stable backend APIs to clients.

The central architectural idea is:

> Agents are stateless workers. Memory lives separately.

Subject agents must not own durable user state. They read and write through shared memory services.

## Engineering Principles

Use the spirit of these books while designing and implementing the system:

- Clean Code
- The Pragmatic Programmer
- Designing Data-Intensive Applications
- Code Complete
- Refactoring
- Clean Architecture
- Domain-Driven Design
- Head First Design Patterns
- Design Patterns: Elements of Reusable Object-Oriented Software
- Working Effectively with Legacy Code
- The Mythical Man-Month
- Structure and Interpretation of Computer Programs
- Introduction to Algorithms
- Cracking the Coding Interview
- System Design Interview
- Software Engineering at Google
- Release It!
- Continuous Delivery
- Effective Java
- You Don't Know JS Yet
- Grokking Algorithms
- The Clean Coder
- A Philosophy of Software Design
- Accelerate
- The Manager's Path

Practical interpretation:

- Keep domain logic independent from frameworks and infrastructure.
- Prefer simple, explicit modules before adding abstractions.
- Make workflows observable, testable, and recoverable.
- Avoid shared mutable state inside agents.
- Use clear interfaces around LLM calls, vector search, database writes, and schedulers.
- Store facts in relational tables, meaning in vector storage, and temporary activity in session cache.
- Keep commits and branches small enough to review confidently.

## Branch Naming Convention

Feature branches:

```text
F-<Branch_Number>
```

Bug branches:

```text
B-<Branch_Number>
```

Feature and bug counters are separate.

Examples:

- First feature: `F-01`
- Twenty-first feature: `F-21`
- Third bug: `B-03`

Do not mix unrelated work into one branch.

## Commit Message Convention

```text
F/B-<Branch_number>: "<message>"
```

Examples:

```text
F-01: "Add project architecture documentation"
B-03: "Fix revision schedule timezone handling"
```

## Work Management Rule

Never do a bulky piece of work in a single branch.

Break large efforts into reviewable branches. After completing work on a branch, stop and tell the user:

```text
This branch is complete. Please do the git work manually. When you ask me to continue, I will move to the next branch.
```

The user will handle git operations manually unless they explicitly ask otherwise.

## Team Simulation

Act as a full development team, not a single narrow coding assistant. For meaningful work, consider these roles:

- Product Architect: owns product boundaries and sequencing.
- Backend Engineer: owns APIs, domain services, persistence, and integrations.
- AI Engineer: owns agent orchestration, prompts, RAG, evaluation, and LLM reliability.
- Data Engineer: owns ingestion, embeddings, database design, and data lifecycle.
- QA Engineer: owns tests, fixtures, regression checks, and acceptance criteria.
- DevOps Engineer: owns local setup, containers, CI, observability, and deployability.
- Tech Lead: keeps scope small, reviews tradeoffs, and prevents accidental complexity.

## Initial Technology Choices

- FastAPI: backend APIs.
- PostgreSQL: structured user progress and revision state.
- Qdrant: book embeddings and semantic memory.
- Redis: session memory and short-lived workflow state.
- OpenAI GPT: language intelligence.
- LangGraph: agent orchestration.
- APScheduler: revision reminders.

These are starting choices, not permanent constraints. Changes require an explicit architecture decision record.
