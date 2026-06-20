# AI University Architecture

## Architecture Goal

AI University should behave like a personalized UPSC coaching institute:

- It routes each request to the right expert.
- It remembers the student's progress.
- It retrieves trusted book material before answering.
- It turns performance into revision plans.
- It can grow one subject at a time without rewriting the core.

The design keeps agents stateless and moves durable state into shared services.

## System Context

```mermaid
flowchart TD
    User["Student / Client App"] --> API["FastAPI Backend"]
    API --> Master["Master Agent"]
    Master --> Polity["Polity Agent"]
    Master --> History["History Agent"]
    Master --> Economy["Economy Agent"]
    Master --> Revision["Revision Agent"]
    Polity --> Memory["Memory Service"]
    History --> Memory
    Economy --> Memory
    Revision --> Memory
    Polity --> RAG["RAG Service"]
    History --> RAG
    Economy --> RAG
    RAG --> VectorDB["Qdrant"]
    Memory --> Postgres["PostgreSQL"]
    Memory --> Redis["Redis"]
    Polity --> LLM["Google Gemini"]
    History --> LLM
    Economy --> LLM
    Master --> LLM
```

## High-Level Components

### API Layer

Responsibilities:

- Authenticate users.
- Validate requests.
- Expose stable HTTP contracts.
- Attach request IDs.
- Call application services.

Non-responsibilities:

- No direct prompt construction.
- No direct database writes for learning state.
- No subject-specific teaching logic.

### Master Agent

Responsibilities:

- Understand user intent.
- Select the correct subject agent or workflow.
- Provide routing context.
- Handle unsupported or ambiguous requests.

Non-responsibilities:

- Does not teach Polity, History, or Economy.
- Does not own user memory.
- Does not directly query books unless implementing a generic workflow.

### Subject Agents

Responsibilities:

- Teach subject topics.
- Generate quizzes and explanations.
- Use memory for personalization.
- Use RAG for grounded source context.
- Emit learning events back to Memory Service.

Initial subject:

- Polity Agent

Future subjects:

- History Agent
- Economy Agent
- Current Affairs Agent

### Memory Service

Responsibilities:

- Own structured memory in PostgreSQL.
- Own semantic memory writes and retrieval coordination.
- Own session state in Redis.
- Provide a single API for all agents.

Memory types:

- Structured Memory: facts and progress.
- Semantic Memory: meaningful learning observations.
- Session Memory: temporary active-session state.

### RAG Service

Responsibilities:

- Ingest books and notes.
- Chunk source material.
- Create embeddings.
- Retrieve relevant chunks for a query.
- Return source metadata.

Initial sources:

- NCERT PDFs.
- Laxmikanth.

### Revision Agent

Responsibilities:

- Convert weak performance into spaced revision tasks.
- Schedule review reminders.
- Surface due revision items.
- Update revision outcomes after review.

## Request Flow: Teaching

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as FastAPI API
    participant Master as Master Agent
    participant Polity as Polity Agent
    participant Memory as Memory Service
    participant RAG as RAG Service
    participant LLM as Google Gemini

    User->>API: Teach me Fundamental Rights
    API->>Master: route_request(user_id, message)
    Master->>Master: classify subject and intent
    Master->>Polity: teach(topic=Fundamental Rights)
    Polity->>Memory: get_user_learning_context(user_id, Polity, topic)
    Memory-->>Polity: progress, weak areas, last studied
    Polity->>RAG: retrieve(topic query, subject=Polity)
    RAG-->>Polity: relevant book chunks with metadata
    Polity->>LLM: generate personalized grounded answer
    LLM-->>Polity: answer
    Polity->>Memory: record_learning_event()
    Polity-->>Master: response
    Master-->>API: response
    API-->>User: personalized lesson
```

## Request Flow: MCQ Submission

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as FastAPI API
    participant Master as Master Agent
    participant Polity as Polity Agent
    participant Memory as Memory Service
    participant Revision as Revision Agent

    User->>API: Submit answers for 10 MCQs
    API->>Master: evaluate_submission()
    Master->>Polity: evaluate_mcq_attempt()
    Polity->>Memory: store_assessment(score, topic breakdown)
    Polity->>Memory: update_progress_and_confidence()
    Polity->>Revision: plan_revision(user_id, weak topics)
    Revision->>Memory: create_revision_tasks()
    Polity-->>Master: score and explanations
    Master-->>API: result
    API-->>User: score, weak areas, next revision dates
```

## Shared Memory Architecture

```mermaid
flowchart LR
    Polity["Polity Agent"] --> MemoryAPI["Memory Service API"]
    History["History Agent"] --> MemoryAPI
    Economy["Economy Agent"] --> MemoryAPI
    Revision["Revision Agent"] --> MemoryAPI

    MemoryAPI --> Structured["Structured Memory"]
    MemoryAPI --> Semantic["Semantic Memory"]
    MemoryAPI --> Session["Session Memory"]

    Structured --> Postgres["PostgreSQL"]
    Semantic --> Qdrant["Qdrant"]
    Session --> Redis["Redis"]
```

## RAG Pipeline

```mermaid
flowchart TD
    Source["NCERT / Laxmikanth PDFs"] --> Extract["Extract Text"]
    Extract --> Clean["Clean and Normalize"]
    Clean --> Chunk["Chunk by chapter, topic, page"]
    Chunk --> Embed["Create Embeddings"]
    Embed --> Store["Store Vectors + Metadata in Qdrant"]
    Query["User Query"] --> QueryEmbed["Embed Query"]
    QueryEmbed --> Search["Search Qdrant"]
    Search --> Context["Relevant Chunks"]
    Context --> Prompt["Grounded Prompt"]
    Prompt --> Answer["Personalized Answer"]
```

## Deployment View

```mermaid
flowchart TD
    Client["Web / Mobile Client"] --> Backend["FastAPI App"]
    Backend --> Worker["Background Worker"]
    Backend --> Postgres["PostgreSQL"]
    Backend --> Redis["Redis"]
    Backend --> Qdrant["Qdrant"]
    Backend --> Gemini["Gemini API"]
    Worker --> Postgres
    Worker --> Redis
    Worker --> Qdrant
    Worker --> Gemini
```

## Data Ownership

PostgreSQL owns:

- Users.
- Subjects.
- Topics.
- Progress.
- Assessments.
- Revision tasks.
- Book metadata.

Qdrant owns:

- Book chunk embeddings.
- Semantic user learning observations.

Redis owns:

- Active study session state.
- Short-lived workflow state.
- Idempotency locks where needed.

Agents own:

- Runtime reasoning.
- Tool selection.
- Prompt assembly.
- Response shaping.

Agents do not own:

- Durable progress.
- Book storage.
- Scheduled tasks.
- Authentication.

## Reliability Principles

- Every external call has timeout and retry policy.
- LLM calls are wrapped behind interfaces.
- Prompt inputs and outputs are logged safely.
- Workflow steps emit domain events.
- Revision scheduling is idempotent.
- RAG ingestion can be rerun without duplicate chunks.
- Failed background jobs are observable and retryable.

## Security and Privacy Principles

- Do not store raw secrets in code.
- Use environment variables for API keys.
- Keep user memory access scoped by user ID.
- Avoid logging full personal study history in plain logs.
- Store source document metadata separately from user state.
- Make deletion and export of user memory possible later.
