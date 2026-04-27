# Forward Deployed Engineer — Design Round
## Google Drive: Enterprise Contract Review AI

---

## Interview Structure

```
Phase 1 — Scoping & Discovery      15 min
Phase 2 — MVP & Production Design  25 min
Phase 3 — Scalability & Eval       15 min
Buffer / Q&A                        5 min
```

---

# PART 1 — SCOPING & DISCOVERY

## 1.1 The FDE Mindset

```
Wrong:  Hear problem → start designing
Right:  Hear problem → ask 5 questions
        → find the number that hurts
        → anchor everything to that number
```

## 1.2 The 5-Question Intake

```
Q1 — Current State
     "Walk me through the process today.
      Who does what, and where does it break?"

Q2 — Quantify the Pain
     "How many contracts per month?
      How many hours per contract?
      What is the error or miss rate?"

Q3 — Root Cause
     "Is the problem volume, unstructured data,
      lack of tooling — or all three?"

Q4 — Executive Success Metric
     "What number would your CTO use to call
      this a success in 90 days?"

Q5 — Constraints
     "Data residency requirements?
      Compliance framework — SOC2, HIPAA, GDPR?
      Already on GCP?"
```

## 1.3 The Executive Reframe

```
Pattern:  5 Whys + So What

Client:   "We want to improve contract review quality"
You:      "What does a missed clause cost you
           in dollar terms — rework, legal exposure?"
Client:   "Each miss costs us ~$200K in remediation"
You:      "At 3-4 misses per month that is
           $600-800K in annual exposure.
           If we cut that by 80% with AI-assist
           and human sign-off, what does that mean
           for your CFO?"
Client:   "That is significant"
You:      "That is the story we tell the board.
           Now let me show you how we build it."
```

```
Engineers ask:           Executives ask:
─────────────────────    ──────────────────────────────
Which vector DB?         What does this cost per month?
RAG vs fine-tune?        When do we break even?
Chunk size?              What if the AI is wrong?
Latency p99?             Can we show the board in Q2?

Your job as FDE: Answer both sides fluently.
```

## 1.4 Business Case

```
Scenario:
  Enterprise with 8 years of contracts,
  proposals, and policies in Google Drive.
  Manual review is the bottleneck.

Capacity check — 1 lawyer:
  8 hrs/day × 22 working days = 176 hrs/month
  176 hrs / 3 hrs per contract = ~58 contracts max

For 200 contracts/month:
  200 × 3 hrs = 600 lawyer-hrs needed
  600 / 176   = 3.4 lawyers → round up to 4 lawyers

Before AI:
  4 lawyers × 176 hrs × $300/hr = $211K/month

After AI (30 min/contract):
  200 × 0.5 hrs = 100 hrs/month
  100 / 176     = 1 lawyer handles it comfortably
  1 lawyer × 100 hrs × $300/hr = $30K/month

Monthly savings:  $211K - $30K = $181K/month
Annual savings:   ~$2.2M/year

Missed clause exposure:
  $200K = remediation cost per missed clause
          (legal dispute + settlement + rework)
          NOT the contract face value
  3-4 misses/month = $600-800K annual exposure
  additional savings on top of labor
```

---

# PART 2 — MVP & PRODUCTION DESIGN

## 2.1 Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│               GOOGLE DRIVE CONTRACT REVIEW AI                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  INGESTION          INDEXING         INTELLIGENCE            │
│                                                              │
│  Drive API       Vertex Embeddings   LangGraph Agent         │
│      ↓                  ↓                  ↓                 │
│  Pub/Sub          Vector Search       Gemini Pro             │
│      ↓                  ↓             Gemini Flash           │
│  Dataflow           BigQuery                ↓                │
│  (parse+chunk)     (metadata)          SERVING               │
│      ↓                                Cloud Run             │
│     GCS                                Apigee               │
│  (raw store)                           Redis Cache           │
│                                             ↓                │
│                                        SURFACES              │
│                                        REST API              │
│                                        Workspace Add-on      │
│                                        Chat Bot              │
├──────────────────────────────────────────────────────────────┤
│  OBSERVABILITY                                               │
│  Cloud Logging · Cloud Trace · Vertex Model Monitoring       │
│  BigQuery (audit trail + query patterns)                     │
└──────────────────────────────────────────────────────────────┘
```

## 2.2 Ingestion Layer

```
Google Drive API
    ↓ push notifications on create / update / delete
Pub/Sub Topic
    ↓
Dataflow Pipeline
    ├── Parse    PDF, Docs, Sheets via export API
    ├── Clean    strip formatting, normalize whitespace
    └── Chunk    512 tokens, 10% overlap
                 contracts → clause-boundary chunking
                 not fixed token windows
    ↓                   ↓
   GCS               BigQuery
(raw docs,
 immutable)
```

### Chunking Strategy

```
Doc type          Strategy
──────────────    ──────────────────────────────────────
Standard docs     512 tokens, 10% overlap
Contracts         Clause boundaries first
                  Token limit as fallback only
Long reports      Section headers as natural boundaries
```

### Why 10% Overlap

```
Without overlap:  clause cut mid-way at chunk boundary
                  retrieval misses the full context

With overlap:     adjacent chunks share context at edges
                  no semantic information lost
```

### BigQuery — 2 Tables

```
TABLE 1: chunks
┌──────────────────────────────────────────────┐
│  chunk_id        PK                          │
│  tenant_id                                   │
│  doc_id                                      │
│  filename                                    │
│  chunk_text      full cleaned text           │
│  chunk_index     position in document        │
│  created_at                                  │
│  updated_at                                  │
└──────────────────────────────────────────────┘

TABLE 2: chunk_embeddings
┌──────────────────────────────────────────────┐
│  chunk_id        FK → chunks                 │
│  tenant_id                                   │
│  embedding_model version tracking            │
│  embedding_dim                               │
│  vector_search_namespace                     │
│  indexed_at                                  │
└──────────────────────────────────────────────┘
```

### Why 2 Tables Not 1

```
Model upgrade    →  rewrite TABLE 2 only, TABLE 1 untouched
Query speed      →  no large metadata joins at query time
Audit trail      →  full history of model version per vector
Embeddings       →  live in Vertex Vector Search
                    TABLE 2 is the metadata pointer only
```

## 2.3 Indexing Layer

```
Chunks
    ↓
Vertex AI Embeddings API
    model:   text-embedding-004
    batch:   250 texts per API call — never one-by-one
    ↓
Vertex AI Vector Search
    index:     ANN — Approximate Nearest Neighbor
    namespace: per tenant_id — isolation at index level
```

### ANN vs Exact Search

```
                ANN              Exact Search
────────────    ─────────────    ──────────────────
Latency         < 100ms          seconds at scale
Accuracy loss   < 1%             0%
Scale           100M+ vectors    breaks at ~1M
Verdict         ✅ production     ❌ not for prod
```

### Namespace Isolation — Non-Negotiable

```
Shared index + post-filter  →  misconfigured query leaks
                                tenant A data to tenant B
                                compliance failure

Namespace isolation         →  cross-tenant leakage
                                physically impossible
                                cannot be retrofitted later
```

## 2.4 Intelligence Layer — LangGraph Single Agent

### Why Single Agent for MVP

```
Multi-agent needed when:          MVP reality:
──────────────────────────        ─────────────────────────
Reuse across orgs                 One client, one domain
Independent scaling per agent     Single Cloud Run service
Different teams own each agent    One FDE team owns all

Decision:  Single agent + modular tools
           Extract to multi-agent only if
           cross-org reuse is required later
```

### Tool Set

```
Tool 1: retrieve_chunks
  embed query → Vector Search top-K → MMR rerank
  returns ranked chunks with similarity scores

Tool 2: summarize_doc
  Gemini Flash — compression not reasoning
  returns 3-line document brief

Tool 3: compare_clauses
  structured diff across multiple chunk sets
  contract comparison across vendors or time periods

Tool 4: ask_clarification
  fires when query too ambiguous to retrieve reliably
  returns follow-up question to user before wasting
  a retrieval call
```

### LangGraph Routing

```
User Query
    ↓
[Retrieval Node]
    ↓
confidence check
    ├── HIGH  →  [Reasoning Node — Gemini Pro]
    │                   ↓
    │            [Synthesis Node]
    │                   ↓
    │             Answer + Citations
    │
    └── LOW   →  [Clarification Node]
                        ↓
                 Question back to user
                        ↓
                 [Retrieval Node]  ← retry
```

### Why LangGraph Over Simple Chain

```
Simple chain:   linear, no state, no conditional routing

LangGraph:      stateful conversation across turns
                conditional edges based on confidence
                every node logged → full audit trail
                replay any reasoning chain for compliance
```

### Gemini Model Selection

```
Gemini Flash    →  summarization — high volume, low cost

Gemini Pro      →  complex multi-hop reasoning
                   clause comparison across long docs
                   anywhere quality > speed
```

### System Prompt

```
ROLE:
Enterprise document assistant for {company}.
Internal use only.

GROUNDING RULES:
Answer ONLY using provided context chunks.
Never use general knowledge or training data.
If answer not in context → say so explicitly.
Never speculate beyond what the context states.

CITATION RULES:
Every claim must cite its source.
Format: [Doc: {filename}, Chunk: {chunk_id}]
Cite all supporting chunks, not just the first.

OUTPUT FORMAT:
Direct answer first (1-2 sentences).
Supporting detail from context.
Citations at end.
Under 200 words unless complexity demands more.

CONTEXT:
{chunks ordered by similarity score descending}

QUERY:
{user query}
```

### Why Context Ordered by Similarity Score Descending

```
LLMs attend more to top of context window
Highest confidence chunks go first
Lower confidence chunks serve as supporting context
```

### MMR — Maximal Marginal Relevance

```
A retrieval strategy, not a metric.
Applied after Vector Search returns top-K.
Re-ranks to maximize relevance AND diversity.

Without MMR:  5 near-identical chunks fill context
With MMR:     diverse, complementary results selected

Score = λ × sim(chunk, query)
      - (1-λ) × max_sim(chunk, already_selected)

λ = 0.5–0.7 in practice
```

### A2A — When It Becomes Relevant

```
MVP:      Single LangGraph agent handles everything

Phase 2:  Connect to other enterprise systems

[Drive Agent] ←→ A2A ←→ [CRM Agent]
                      ←→ [Finance Agent]
                      ←→ [HR Policy Agent]

Example:
  "What did we promise Acme on pricing, and does
   that conflict with our current margin targets?"
  Drive Agent   → contract lookup
  Finance Agent → margin data
  Orchestrator  → synthesized answer

Design A2A-compatible interfaces from day one
even if not wired until Phase 2.
```

## 2.5 Serving Layer

```
LangGraph Agent
    ↓
Cloud Run
    min-instances > 0       no cold starts under SLA
    horizontal autoscale    handles concurrency
    ↓
Apigee Gateway
    Auth                    Workspace identity → IAM
    Rate limiting           per tenant
    Routing                 per-tenant config
    ↓
Redis / Memorystore
    cache key:  hash(query + tenant_id)
    TTL:        1 hour
    hit:        < 5ms cached response
    miss:       full agent pipeline → cache result
    ↓
Surfaces
    REST API                custom integrations
    Workspace Add-on        Drive / Docs sidebar
    Google Chat Bot         conversational interface
```

## 2.6 Observability

```
Every agent step      →  Cloud Logging + Cloud Trace
Full reasoning chain  →  BigQuery
                          replay any decision for audit
Gemini calls          →  Vertex AI Model Monitoring
                          latency, error rate, token usage
Query patterns        →  BigQuery dashboard
                          retrieval failure analysis
                          tool invocation frequency
Cost attribution      →  GCP labels: tenant_id + tool_name
                          billing export = per-client breakdown
```

---

# PART 3 — SCALABILITY & EVALUATION

## 3.1 Scalability — 3 Axes

### Axis 1 — Data Volume (10x documents)

```
Layer           Problem                Fix
────────────    ───────────────────    ──────────────────────────────
Dataflow        pipeline too slow      autoscale workers vs
                                       Pub/Sub backlog size
Embeddings      API rate limit         batch 250 texts per call
Vector Search   index too large        horizontal sharding
                                       ANN handles 100M+ natively
BigQuery        slow queries           partition by tenant_id + date
```

### Axis 2 — Query Volume (10x concurrent users)

```
Layer           Problem                Fix
────────────    ───────────────────    ──────────────────────────────
Cloud Run       concurrency limit      horizontal autoscaling
                                       min-instances > 0
Gemini API      rate limit / cost      Redis cache absorbs repeats
                                       async parallel tool calls
                                       where steps are independent
Vector Search   QPS ceiling            scale index replicas
```

### Axis 3 — Multi-tenancy (50 enterprise clients)

```
Layer           Problem                Fix
────────────    ───────────────────    ──────────────────────────────
Vector Search   data isolation         namespace per tenant_id
                                       leakage physically impossible
GCS             data isolation         /{tenant_id}/raw/
                                       /{tenant_id}/chunks/
BigQuery        access control         row-level security via IAM
Cost            attribution            GCP labels by tenant_id
                                       billing export automated
```

### Doc Update — Incremental Indexing

```
Doc updated in Drive
    ↓
Pub/Sub push notification
    ↓
Cloud Function triggered
    ↓
Re-chunk + re-embed ONLY changed doc   ← never full corpus rebuild
    ↓
Incremental Vector Search update
    ↓
Redis cache invalidation for affected chunk_ids only
```

## 3.2 Evaluation — 3 Layers

### Layer 1 — Retrieval Quality

```
Metric 1: Recall@K
──────────────────────────────────────────────────────
What:     Of all chunks that should be retrieved,
          how many appear in top-K results?

Formula:  Recall@K = relevant chunks in top-K
                     ─────────────────────────
                     total relevant chunks exist

Example:  3 relevant chunks exist for a query
          K=5 retrieves 2 → Recall@5 = 0.67

Tune K:   Small K (3–5)    fast, cheap, may miss chunks
          Large K (10–20)  better recall, more noise
          Practical        K = 5–10 for most queries
```

```
Metric 2: MRR — Mean Reciprocal Rank
──────────────────────────────────────────────────────
What:     How high is the FIRST relevant chunk ranked?
          LLMs attend more to top-of-context content.

Formula:  MRR = mean(1 / rank of first relevant chunk)

Example:  Query 1 → rank 2 → 0.50
          Query 2 → rank 1 → 1.00
          Query 3 → rank 4 → 0.25
          MRR = avg(0.50, 1.00, 0.25) = 0.58

Note:     MRR ≠ MMR
          MRR = evaluation metric
          MMR = retrieval strategy (diversity reranking)
```

### Ground Truth — Where Does It Come From

```
No labeled data upfront in enterprise deployments.

Option 1 — Synthetic (recommended for MVP)
  Each chunk → Gemini prompt:
    "Generate 3 realistic questions this chunk answers."
  Result: (question, chunk_id) pairs
  Zero human labeling. Scales with corpus automatically.

Option 2 — Human Annotation (gold standard)
  Domain expert marks relevant chunks per query.
  50–100 queries sufficient for MVP baseline.
  Worth it for high-stakes domains: legal, compliance.

Option 3 — Production Weak Labels (ongoing)
  Thumbs up / down on answers
  Did user click the source citation?
  Did user rephrase immediately? → implicit negative
  Feed back as training signal over time.
```

### Layer 2 — Generation Quality (Vertex AI Evaluation Service)

```
Input:   dataframe — prompt | response | context
Output:  per-row scores + aggregate metrics
Judge:   Gemini evaluates Gemini outputs
```

```
Metric 1: Faithfulness
──────────────────────────────────────────────────────
Failure:  Model adds information not in retrieved chunks

Example:
  Context:  "Termination requires 30 days notice"
  Response: "Termination requires 30 days notice.
             There is also a 10% early exit penalty."
             ↑ not in context — hallucinated

Stakes:   Incorrect legal information sent to lawyers
Fix:      "Answer ONLY using provided context.
           Never extrapolate beyond what is stated."
```

```
Metric 2: Groundedness
──────────────────────────────────────────────────────
Failure:  Model ignores retrieved context entirely,
          answers from parametric memory instead

Example:  5 relevant contract chunks retrieved
          Model gives generic legal answer
          sourced from training data, not your docs

Faithfulness:  OK  — no contradiction
Groundedness:  LOW — bypassed RAG pipeline entirely

Stakes:   Answer is untraceable to any source doc
          Compliance failure in regulated industries

Fix:      "Cite source document and chunk_id
           for every claim made in the response."
```

### Faithfulness vs Groundedness

```
                Faithfulness          Groundedness
────────────    ──────────────────    ─────────────────────────
Catches         Adding beyond         Ignoring context
                context               entirely
Failure         Hallucinated          Correct but
looks like      details appended      untraceable answer
Stakes          Accuracy / legal      Compliance / audit
Fix             Strict grounding      Mandatory citation
                in system prompt      per claim
```

### Layer 3 — Business KPIs

```
KPI                         Baseline      Target
─────────────────────────   ──────────    ──────────
Hours per contract review   3 hrs         30 min
Lawyer headcount needed     4             1
Missed clause rate          3-4/month     < 1/month
Monthly labor cost          $211K         $30K
Cost per query              —             < $0.10
Lawyer adoption rate        0%            > 70%
```

> "I always close the loop back to discovery.
>  If the pain was lawyer hours and missed clause exposure,
>  those are my primary KPIs — not ROUGE or accuracy.
>  The system is not successful until those numbers move."

## 3.3 Key Tradeoffs

```
Decision                    Choice            Why
──────────────────────────  ────────────────  ──────────────────────────────
RAG vs fine-tuning          RAG for MVP       no labeled data needed
                                              updatable without retraining
                                              faster to ship

LangGraph vs simple chain   LangGraph         stateful, conditional routing
                                              full audit trail per decision

Single vs multi-agent       Single agent      simpler, fewer failure points
                                              modular tools → extract later

Gemini Pro vs Flash         Both              Flash: summarization
                                              Pro: reasoning + comparison

ANN vs exact search         ANN               sub-100ms, < 1% accuracy loss
                                              exact breaks at 1M+ vectors

Shared vs namespaced index  Namespaced        compliance non-negotiable
                                              cannot be retrofitted

2 BQ tables vs 1            2 tables          model upgrades without
                                              touching chunk text
                                              fast queries, clean audit trail
```

## 3.4 Closing Statement (60 Seconds)

```
Discovery:      4 lawyers × 200 contracts/month
                = $211K/month labor
                + $600-800K annual clause exposure
                Target: 1 lawyer, $30K/month, < 1 miss/month

Architecture:   Drive API → Pub/Sub → Dataflow → GCS + BigQuery
                Vertex Embeddings → Vector Search (ANN, namespaced)
                LangGraph single agent — 4 modular tools
                Gemini Pro for reasoning, Flash for summarization
                Redis (1hr TTL) + Apigee for multi-tenancy

Scalability:    3 axes — data volume, query volume, tenants
                Namespace isolation from day one
                Incremental re-index only on doc change

Eval:           Retrieval  → Recall@K + MRR
                             synthetic ground truth at ingestion
                Generation → Faithfulness + Groundedness
                             via Vertex AI Evaluation Service
                Business   → hours-per-contract + missed clause rate

Agentic:        LangGraph stateful conditional routing
                A2A-compatible for Phase 2 CRM / Finance integration
```
