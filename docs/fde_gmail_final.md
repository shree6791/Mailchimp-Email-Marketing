# Forward Deployed Engineer — Design Round
## Gmail: Enterprise Support Email Triage AI

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
     "Walk me through how your team handles email today.
      Who reads what, how do they prioritize,
      where does it break down?"

Q2 — Quantify the Pain
     "How many emails per day per agent?
      How long does triage take?
      What is your response SLA and are you hitting it?"

Q3 — Root Cause
     "Is the problem volume, lack of routing,
      no summarization, missed follow-ups — or all of these?"

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

Client:   "We want to improve support email response time"
You:      "What does a slow response cost you —
           SLA penalties, churn, agent burnout?"
Client:   "We breach SLA 15-20% of the time,
           each breach triggers a penalty clause"
You:      "At 10,000 emails/day with 15% breach rate
           that is 1,500 breaches/day.
           If we cut that to under 2% with AI triage,
           what does that mean for your CFO?"
Client:   "That is significant"
You:      "That is the story we tell the board.
           Now let me show you how we build it."
```

```
Engineers ask:               Executives ask:
─────────────────────────    ──────────────────────────────
Which classifier model?      How fast can we reduce breaches?
Fine-tune vs prompt?         What if AI routes it wrong?
Latency p99?                 Can agents override the AI?
Token cost per email?        Will this replace headcount?

Your job as FDE: Answer both sides fluently.
```

## 1.4 Business Case

```
Scenario:
  50-agent support team handling 10,000 emails/day.
  Manual triage is consuming agent capacity.

Capacity check — 1 agent:
  8 hrs/day available
  2 hrs/day spent on triage alone
  = 25% of capacity on non-resolution work

Team level:
  50 agents × 2 hrs/day = 100 agent-hours/day wasted
  100 hrs × $50/hr fully loaded = $5,000/day
  $5,000 × 250 working days = $1.25M/year
  just in triage labor

SLA breach exposure:
  10,000 emails/day × 15% breach rate
  = 1,500 breaches/day
  Each breach → penalty clause + churn risk

Target state:
  Triage time: 2 hrs/agent/day → 20 min/agent/day
  Response time: 4-6 hours → < 30 min
  SLA breach rate: 15-20% → < 2%
```

---

# PART 2 — MVP & PRODUCTION DESIGN

## 2.1 Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│              GMAIL ENTERPRISE SUPPORT TRIAGE AI              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  INGESTION          INDEXING         INTELLIGENCE            │
│                                                              │
│  Gmail API       Vertex Embeddings   LangGraph Agent         │
│  Pub/Sub Watch          ↓                  ↓                 │
│      ↓            Vector Search       Gemini Pro             │
│  Dataflow               ↓             Gemini Flash           │
│  (parse+chunk)       BigQuery               ↓                │
│      ↓              (metadata)         SERVING               │
│     GCS                               Cloud Run             │
│  (raw store)                           Apigee               │
│                                        Redis Cache           │
│                                             ↓                │
│                                        SURFACES              │
│                                        Agent Workspace UI    │
│                                        Gmail Add-on          │
│                                        REST API              │
├──────────────────────────────────────────────────────────────┤
│  OBSERVABILITY                                               │
│  Cloud Logging · Cloud Trace · Vertex Model Monitoring       │
│  BigQuery (audit trail + draft acceptance + routing stats)   │
└──────────────────────────────────────────────────────────────┘
```

## 2.2 Ingestion Layer

```
Gmail API (Pub/Sub Watch)
    ↓ historyId-based incremental sync — not full poll
Pub/Sub Topic
    ↓
Dataflow Pipeline
    ├── Parse    headers, body, attachments, thread context
    ├── Clean    strip HTML, signatures, quoted reply chains
    ├── Enrich   sender domain, thread history, Gmail labels
    └── Chunk    short emails (<200 tokens) → 1 chunk
                 long emails → paragraph boundaries
                 10% overlap on adjacent chunks
                 attachments → Document AI → separate chunks
                               linked to parent email_id
    ↓                   ↓
   GCS               BigQuery
(raw emails,
 immutable)
```

### Chunking Strategy

```
Email type        Strategy
──────────────    ──────────────────────────────────────
Short (<200 tok)  Whole email = 1 chunk
Long (>200 tok)   Paragraph splits, 10% overlap
Threads           Last 2-3 replies included as context
Attachments       Document AI extraction
                  Chunked separately, linked to email_id
```

### BigQuery — 2 Tables

```
TABLE 1: emails
┌──────────────────────────────────────────────┐
│  email_id          PK                        │
│  tenant_id                                   │
│  thread_id         group related emails      │
│  sender                                      │
│  recipient_list                              │
│  subject                                     │
│  body_text         full cleaned text         │
│  labels            Gmail labels              │
│  attachment_ids                              │
│  timestamp                                   │
│  created_at                                  │
└──────────────────────────────────────────────┘

TABLE 2: email_embeddings
┌──────────────────────────────────────────────┐
│  email_id          FK → emails               │
│  tenant_id                                   │
│  chunk_id                                    │
│  embedding_model   version tracking          │
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
Email chunks
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
                                tenant A emails to tenant B
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
Tool 1: classify_intent
  Gemini Flash — high volume, low latency
  categories: support / billing / complaint /
              feature request / escalation / spam
  returns: intent label + confidence score

Tool 2: score_priority
  Gemini Flash + rule-based signals
  signals: sentiment, sender history,
           SLA proximity, thread age
  returns: priority score 1–5 + reasoning

Tool 3: route_email
  intent + priority + tenant routing rules
  returns: assigned team + agent_id

Tool 4: summarize_email
  Gemini Flash — compression not reasoning
  returns: 3-line brief for agent

Tool 5: retrieve_similar_threads
  embed email → Vector Search top-K → MMR rerank
  returns: top-K resolved threads for draft context

Tool 6: draft_response
  Gemini Pro — grounded in retrieved resolved threads
  returns: editable draft + source thread citation
```

### LangGraph Routing

```
New Email arrives
    ↓
[Classification Node]      Gemini Flash
    ↓
[Priority Scoring Node]    Gemini Flash + rules
    ↓
intent = spam?
    ├── YES  →  [Auto-Archive Node]
    │            no human needed
    │
    └── NO   →  [Routing Node]
                    ↓
               routing confidence?
                    ├── HIGH  →  [Summarization Node]
                    │                  ↓
                    │           [Draft Response Node]
                    │           RAG on resolved threads
                    │                  ↓
                    │            Agent Workspace UI
                    │            brief + draft ready
                    │
                    └── LOW   →  [Human Review Node]
                                 flag for supervisor
```

### Why LangGraph Over Simple Chain

```
Simple chain:   linear, no state, no conditional routing

LangGraph:      stateful thread tracking across turns
                spam → auto-archive shortcut
                low-confidence → human escalation
                every node logged → full audit trail
                replay any routing decision for compliance
```

### Gemini Model Selection

```
Gemini Flash    →  classification, priority scoring,
                   summarization — high volume tasks
                   optimize for speed + cost

Gemini Pro      →  draft response generation
                   complex complaint analysis
                   multi-turn thread reasoning
```

### System Prompt — Draft Response

```
ROLE:
Enterprise email assistant for {company}.
Help support agents respond to customer emails.

GROUNDING RULES:
Draft responses ONLY using provided resolved threads.
Never invent policies, prices, or commitments.
If no relevant thread exists → say:
  "No similar resolution found.
   Agent should draft manually."

CITATION RULES:
Reference the resolved thread backing each statement.
Format: [Based on Thread: {thread_id}, resolved {date}]

OUTPUT FORMAT:
3-line summary of incoming email first.
Then draft response (editable by agent).
Then citation of reference thread used.

CONTEXT — SIMILAR RESOLVED THREADS:
{threads ordered by similarity score descending}

INCOMING EMAIL:
{email text}
```

### MMR — Maximal Marginal Relevance

```
A retrieval strategy, not a metric.
Applied after Vector Search returns top-K threads.
Re-ranks to maximize relevance AND diversity.

Without MMR:  5 threads all about same billing issue
              no variety in draft response examples
With MMR:     diverse resolution approaches selected
              richer context for Gemini to draft from

Score = λ × sim(thread, incoming_email)
      - (1-λ) × max_sim(thread, already_selected)

λ = 0.5–0.7 in practice
```

### A2A — When It Becomes Relevant

```
MVP:      Single LangGraph agent handles everything

Phase 2:  Connect to other enterprise systems

[Gmail Agent] ←→ A2A ←→ [CRM Agent]
                      ←→ [Billing Agent]
                      ←→ [Ticketing Agent — Jira / SF]

Example:
  Customer emails about a billing dispute
  Gmail Agent   → reads + classifies email
  CRM Agent     → pulls customer account history
  Billing Agent → pulls invoice + payment status
  Orchestrator  → draft with full context

Design A2A-compatible interfaces from day one
even if not wired until Phase 2.
```

## 2.5 Serving Layer

```
LangGraph Agent
    ↓
Cloud Run
    min-instances > 0       no cold starts under SLA
    horizontal autoscale    handles email burst volume
    ↓
Apigee Gateway
    Auth                    Workspace identity → IAM
    Rate limiting           per tenant
    Routing                 per-tenant config
    ↓
Redis / Memorystore
    cache key:  hash(email_body + tenant_id)
    TTL:        15 min  ← shorter than Drive
                         email classification goes stale faster
    hit:        < 5ms cached classification + routing
    miss:       full agent pipeline → cache result
    ↓
Surfaces
    Agent Workspace UI      triage dashboard — brief + draft
    Gmail Add-on            sidebar in Gmail for agents
    REST API                Salesforce / Zendesk integration
```

## 2.6 Observability

```
Every agent step          →  Cloud Logging + Cloud Trace
Full reasoning chain      →  BigQuery
                              replay any routing decision
                              for audit or dispute
Classification accuracy   →  BigQuery dashboard
                              intent label distribution
                              routing correction rate
Draft acceptance rate     →  BigQuery
                              used as-is / edited / discarded
                              key signal for model improvement
Agent override rate        →  BigQuery
                              high override = retrain signal
Gemini calls              →  Vertex AI Model Monitoring
Cost attribution          →  GCP labels: tenant_id + tool_name
                              billing export = per-client breakdown
```

---

# PART 3 — SCALABILITY & EVALUATION

## 3.1 Scalability — 3 Axes

### Axis 1 — Data Volume (10x email volume)

```
Layer           Problem                Fix
────────────    ───────────────────    ──────────────────────────────
Pub/Sub         message backlog        increase ack deadline
                                       add parallel consumers
Dataflow        pipeline too slow      autoscale workers vs
                                       Pub/Sub backlog size
Embeddings      API rate limit         batch 250 texts per call
Vector Search   index too large        horizontal sharding
                                       ANN handles 100M+ natively
BigQuery        slow queries           partition by tenant_id + date
                                       cluster by thread_id
```

### Axis 2 — Query Volume (10x concurrent agents)

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
                                       /{tenant_id}/emails/
BigQuery        access control         row-level security via IAM
Routing rules   per-client config      tenant rules in Firestore
                                       loaded at agent init
Cost            attribution            GCP labels by tenant_id
                                       billing export automated
```

### Email Burst Curveball

```
Marketing campaign sends 100K emails in 1 hour
    ↓
Pub/Sub absorbs burst — unbounded buffer
    ↓
Dataflow autoscales workers to drain backlog
    ↓
Gemini Flash handles classification at volume
(chosen for high-throughput, low-cost workloads)
    ↓
Redis cache absorbs repeat classifications
same campaign email → cache hit → no Gemini call
```

### New Email — Incremental Indexing

```
New email arrives via Pub/Sub Watch
    ↓
Dataflow processes + embeds immediately
    ↓
Incremental Vector Search update
    ↓
Available for retrieval in draft generation
within seconds of arrival
```

## 3.2 Evaluation — 3 Layers

### Layer 1 — Retrieval Quality

```
Metric 1: Recall@K
──────────────────────────────────────────────────────
What:     Of all resolved threads that should be
          retrieved for a given email, how many
          appear in top-K results?

Formula:  Recall@K = relevant threads in top-K
                     ─────────────────────────
                     total relevant threads exist

Example:  5 relevant threads exist for an email
          K=5 retrieves 4 → Recall@5 = 0.80

Tune K:   Small K (3–5)    fast, cheap, may miss threads
          Large K (10–20)  better recall, more noise
          Practical        K = 5–10 for draft generation
```

```
Metric 2: MRR — Mean Reciprocal Rank
──────────────────────────────────────────────────────
What:     How high is the FIRST relevant thread ranked?
          LLMs attend more to top-of-context content.

Formula:  MRR = mean(1 / rank of first relevant thread)

Example:  Query 1 → rank 2 → 0.50
          Query 2 → rank 1 → 1.00
          Query 3 → rank 3 → 0.33
          MRR = avg(0.50, 1.00, 0.33) = 0.61

Note:     MRR ≠ MMR
          MRR = evaluation metric
          MMR = retrieval strategy (diversity reranking)
```

### Ground Truth — Where Does It Come From

```
No labeled data upfront in enterprise deployments.

Option 1 — Synthetic (recommended for MVP)
  Each resolved thread → Gemini prompt:
    "Generate 3 realistic incoming emails that this
     resolution would apply to."
  Result: (incoming_email, thread_id) pairs
  Zero human labeling. Scales automatically.

Option 2 — Historical Signal (strong for Gmail)
  Past agent routing decisions = weak ground truth
  Agent followed AI routing  → positive label
  Agent overrode AI routing  → negative label
  Rich signal from day 1 if instrumented correctly.

Option 3 — Draft Acceptance Rate (production signal)
  Agent used draft as-is     → strong positive
  Agent heavily edited draft → weak positive
  Agent discarded draft      → negative
  Most actionable signal for improving draft quality.
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
Failure:  Draft includes commitments not in
          retrieved resolved threads

Example:
  Thread:  "We offer 30-day refunds"
  Draft:   "We offer 30-day refunds and free
            expedited shipping on reorders."
            ↑ invented commitment — legal risk

Stakes:   Agent sends this to customer.
          Company now liable for that commitment.

Fix:      "Draft ONLY using provided resolved threads.
           Never invent policies or commitments."
```

```
Metric 2: Groundedness
──────────────────────────────────────────────────────
Failure:  Draft ignores retrieved threads entirely,
          Gemini drafts from general knowledge instead

Example:  5 similar resolved threads retrieved
          Draft says: "Thank you for contacting us.
                       As per standard policy..."
                       ← generic, not your actual policy
                       ← may contradict real resolution

Faithfulness:  OK  — no contradiction
Groundedness:  LOW — bypassed retrieved threads

Stakes:   Inconsistent responses across agents
          Brand and compliance risk

Fix:      "Cite the thread_id backing each statement
           in the draft response."
```

### Faithfulness vs Groundedness

```
                Faithfulness          Groundedness
────────────    ──────────────────    ─────────────────────────
Catches         Adding beyond         Ignoring context
                context               entirely
Failure         Hallucinated          Generic response
looks like      commitment/policy     not company-specific
Stakes          Legal / liability     Consistency / brand
Fix             Strict grounding      Mandatory thread
                in system prompt      citation per claim
```

### Layer 3 — Business KPIs

```
KPI                         Baseline        Target
─────────────────────────   ──────────      ──────────
Avg email response time     4–6 hours       < 30 min
SLA breach rate             15–20%          < 2%
Triage time per agent       2 hrs/day       20 min/day
Misrouting rate             30%             < 5%
Draft acceptance rate       —               > 60%
Agent override rate         —               < 20%
                                            high = retrain signal
Annual triage cost          $1.25M          < $250K
```

> "I always close the loop back to discovery.
>  If the pain was SLA breach rate and triage time,
>  those are my primary KPIs — not classification accuracy.
>  The system is not successful until those numbers move."

## 3.3 Key Tradeoffs

```
Decision                    Choice            Why
──────────────────────────  ────────────────  ──────────────────────────────
RAG vs fine-tuning          RAG for MVP       no labeled data needed
  for draft generation                        updatable as policies change

Classification fine-tune    Phase 2 only      wait for 10K+ labeled
  (intent routing)                            routing decisions first

LangGraph vs simple chain   LangGraph         stateful thread tracking
                                              spam shortcut
                                              low-confidence escalation
                                              full audit trail

Single vs multi-agent       Single agent      simpler, fewer failure points
                                              A2A later for CRM / billing

Gemini Pro vs Flash         Both              Flash: classification + summary
                                              Pro: draft generation

Redis TTL                   15 min            shorter than Drive (1 hr)
                                              email classification stale faster

ANN vs exact search         ANN               sub-100ms, < 1% accuracy loss

Shared vs namespaced index  Namespaced        compliance non-negotiable
                                              cannot be retrofitted

2 BQ tables vs 1            2 tables          model upgrades without
                                              touching email data
```

## 3.4 Closing Statement (60 Seconds)

```
Discovery:      50 agents × 2 hrs/day triage
                = $1.25M/year wasted labor
                + 15% SLA breach rate
                Target: 20 min/agent/day, < 2% breach

Architecture:   Gmail Pub/Sub Watch → Dataflow → GCS + BigQuery
                Vertex Embeddings → Vector Search (ANN, namespaced)
                LangGraph single agent — 6 modular tools
                Gemini Flash for classification + summarization
                Gemini Pro for draft generation via RAG
                Redis (15min TTL) + Apigee for multi-tenancy

Scalability:    3 axes — email volume, concurrent agents, tenants
                Pub/Sub absorbs marketing email bursts naturally
                Namespace isolation from day one
                Incremental index update per new email

Eval:           Retrieval  → Recall@K + MRR on resolved threads
                             historical routing as ground truth
                Generation → Faithfulness + Groundedness
                             via Vertex AI Evaluation Service
                Business   → response time + SLA breach rate
                Production → draft acceptance + override rate
                             as ongoing retraining signals

Agentic:        LangGraph stateful conditional routing
                A2A-compatible for Phase 2 CRM / Billing integration
```
