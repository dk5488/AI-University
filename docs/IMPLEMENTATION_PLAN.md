# AI University Step-by-Step Implementation Plan

## Delivery Strategy

Build the smallest system that can teach, quiz, remember, retrieve from books, and schedule revision for one subject first.

MVP scope:

1. Master Agent
2. Polity Agent
3. Memory Service
4. Revision Agent
5. RAG for NCERT and Laxmikanth

Do not start with twelve agents. Once the Polity flow works end to end, add History, Economy, and Current Affairs by reusing the same contracts.

## Milestone 0: Project Foundation

Goal: establish repository structure, coding standards, architecture docs, and local development workflow.

Recommended branch:

```text
F-01
```

Deliverables:

- Project docs and guardrails.
- Backend app skeleton.
- Local environment template.
- Docker Compose for PostgreSQL, Redis, and Qdrant.
- Basic test runner.
- CI placeholder.

Acceptance criteria:

- A developer can clone the repo, configure environment variables, and start the empty service locally.
- Tests can run even before feature implementation.
- Architecture and branch conventions are documented.

## Milestone 1: Domain Model and Memory Service

Recommended branch:

```text
F-02
```

Deliverables:

- User, subject, topic, progress, assessment, and revision domain models.
- PostgreSQL schema migrations.
- Memory Service API for reading and writing structured memory.
- Repository interfaces and tests.

Acceptance criteria:

- The system can store and retrieve completion, confidence, revision count, and last studied date per user/topic.
- Subject agents do not write directly to PostgreSQL.

## Milestone 2: Session Memory

Recommended branch:

```text
F-03
```

Deliverables:

- Redis-backed session store.
- Current study session tracking.
- Session lifecycle APIs.
- Expiry and cleanup behavior.

Acceptance criteria:

- A study session can track subject, topic, elapsed time, current score, and in-progress interactions.
- Ending a session persists necessary summary data into structured memory.

## Milestone 3: RAG Ingestion Pipeline

Recommended branch:

```text
F-04
```

Deliverables:

- Document ingestion command.
- PDF/text extraction interface.
- Chunking strategy.
- Embedding writer for Qdrant.
- Metadata model for source, page, chapter, subject, and topic.

Acceptance criteria:

- NCERT and Laxmikanth content can be chunked and indexed.
- Chunks retain enough metadata to cite source context.
- Ingestion is idempotent for the same document version.

## Milestone 4: RAG Retrieval Service

Recommended branch:

```text
F-05
```

Deliverables:

- Query embedding interface.
- Qdrant retrieval adapter.
- Reranking or filtering hooks.
- Retrieval response model.

Acceptance criteria:

- A query like "Explain Article 32" returns relevant chunks from trusted material.
- Retrieval can filter by subject and source.
- Agent code calls a retrieval interface, not Qdrant directly.

## Milestone 5: Master Agent Routing

Recommended branch:

```text
F-06
```

Deliverables:

- Intent classification contract.
- Subject routing rules.
- LangGraph workflow skeleton.
- Fallback behavior for unknown subjects.

Acceptance criteria:

- "Teach me Fundamental Rights" routes to Polity.
- "Generate MCQs on Fundamental Rights" routes to Polity quiz workflow.
- Master Agent stays free of subject teaching logic.

## Milestone 6: Polity Agent Teaching Flow

Recommended branch:

```text
F-07
```

Deliverables:

- Polity Agent interface.
- Personalized teaching prompt builder.
- Memory-aware context assembly.
- RAG-aware answer generation.

Acceptance criteria:

- Polity Agent reads user progress before answering.
- It retrieves source material before generating content.
- Responses are personalized using weak areas and last studied data.

## Milestone 7: MCQ Generation and Evaluation

Recommended branch:

```text
F-08
```

Deliverables:

- MCQ generation workflow.
- Answer submission API.
- Scoring and explanation generation.
- Assessment persistence.

Acceptance criteria:

- The system can generate 10 MCQs for Fundamental Rights.
- User score and weak topics are stored.
- Explanations cite retrieved source context where possible.

## Milestone 8: Revision Agent

Recommended branch:

```text
F-09
```

Deliverables:

- Spaced revision policy.
- APScheduler integration.
- Revision task table.
- APIs for due revision items.

Acceptance criteria:

- A weak score schedules revision for tomorrow, 7 days, and 30 days.
- Revision jobs survive service restarts.
- Timezone behavior is explicit.

## Milestone 9: Observability and Reliability

Recommended branch:

```text
F-10
```

Deliverables:

- Structured logging.
- Request IDs.
- LLM call telemetry.
- Error taxonomy.
- Retry and timeout policies.

Acceptance criteria:

- Failed LLM, DB, Redis, or Qdrant calls produce diagnosable logs.
- External service calls have timeouts.
- Critical workflows expose success/failure metrics.

## Milestone 10: First Usable API Release

Recommended branch:

```text
F-11
```

Deliverables:

- API documentation.
- End-to-end tests for teaching, MCQ, submission, and revision.
- Seed data for a demo user.
- Deployment notes.

Acceptance criteria:

- A user can ask to learn a topic, answer MCQs, receive score feedback, and get revision tasks.
- The release is small but useful for real UPSC study.

## Later Expansion

Add new agents only after the MVP loop is stable.

Recommended sequence:

1. `F-12`: History Agent.
2. `F-13`: Economy Agent.
3. `F-14`: Current Affairs Agent.
4. `F-15`: Cross-subject comparison workflows.
5. `F-16`: Study planner and weekly analytics.

## Bug Branch Examples

Use separate bug counters:

- `B-01`: Fix failed RAG citation metadata.
- `B-02`: Fix duplicate revision jobs.
- `B-03`: Fix Redis session expiry issue.

## Definition of Done

Every implementation branch should include:

- Focused code changes.
- Tests for changed behavior.
- Migration or configuration notes when needed.
- Updated docs for public contracts.
- Manual verification notes.
- No unrelated refactors.

At branch completion, stop and wait for the user's manual git work.
