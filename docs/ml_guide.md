## Machine learning pipeline — worked example (non-technical)

This document explains how the batch pipeline turns tabular trending-video rows into topic-segment ranking rows and AI-written marketing text (summary + email copy), using one small illustrative example. Numbers are representative; production runs depend on the full file and configuration. Implementation detail, paths, and diagrams are in [architecture.md](architecture.md).

---

### 1. Illustrative input

Four rows share a meal preparation theme. `Day` labels two distinct trending dates in chronological order.

| ID | Title | Tags (abbreviated) | Views | Likes | Comments | Day |
|----|--------|--------------------|------:|------:|---------:|:---:|
| V1 | Easy meal prep for the week | meal prep, cooking | 120,000 | 9,000 | 400 | 1 |
| V2 | 5 lunch boxes under 20 dollars | meal prep, budget | 200,000 | 15,000 | 900 | 1 |
| V3 | Meal prep mistakes to avoid | meal prep, kitchen | 90,000 | 5,000 | 350 | 2 |
| V4 | Sunday meal prep routine | meal prep, healthy | 150,000 | 11,000 | 600 | 2 |

---

### 2. Processing sequence

<table>
<colgroup>
<col style="width:2.25em" />
<col style="width:28%" />
<col />
</colgroup>
<thead>
<tr><th scope="col">#</th><th scope="col">Stage</th><th scope="col">Result</th></tr>
</thead>
<tbody>
<tr>
<td>1</td>
<td>Document — concatenate title, tags, and optional description per row.</td>
<td>For V2: <code>5 lunch boxes under 20 dollars meal prep budget</code>.</td>
</tr>
<tr>
<td>2</td>
<td>Normalization — spaCy-based cleanup to lemmas without stop words or noise tokens.</td>
<td>For V2: <code>lunch box 20 dollar meal prep budget</code> (illustrative token string).</td>
</tr>
<tr>
<td>3</td>
<td>Embedding — map each <code>cleaned_text</code> to a 384-dimensional dense vector (default <code>SentenceTransformer</code>). Semantically similar lines yield numerically similar vectors.</td>
<td>First five components for V2, for display only: <code>0.21, -0.05, 0.88, 0.10, -0.33, …</code> — remaining 379 entries omitted.</td>
</tr>
<tr>
<td>4</td>
<td>Topic assignment — BERTopic’s <code>fit_transform</code> takes Step 3 embeddings and Step 2 <code>cleaned_text</code>. Which videos share a topic is determined by embedding geometry. <code>cleaned_text</code> still supplies bag-of-words statistics for cluster descriptions; it is the Step 2 string, not the Step 1 <code>document</code>.</td>
<td>All four rows assigned topic 2 with confidences 0.86, 0.91, 0.79, 0.88. Rows without a cluster get topic −1 and are excluded from scoring.</td>
</tr>
<tr>
<td>5</td>
<td>Topic scoring — topic-level features are expanded into topic-segment ranking rows, then a stability-tuned LambdaMART blend produces final <code>trend_score</code>.</td>
<td>See §2.1.</td>
</tr>
<tr>
<td>6</td>
<td>Offline ranking evaluation — proxy NDCG on the top-<code>N</code> slice (same <code>N</code> as LLM calls); uses blended gain (0.5·CTR-recency + 0.3·volume + 0.2·momentum) against <code>trend_score</code>, immediately after scoring and before topic-keyword columns are attached. Standard demo step before any LLM call; see [architecture.md](architecture.md) §4.</td>
<td>See §2.3.</td>
</tr>
<tr>
<td>7</td>
<td>Topic keywords — attach <code>topic_keywords</code> and <code>topic_label</code> from the fitted topic model for the UI and marketer step.</td>
<td>—</td>
</tr>
<tr>
<td>8</td>
<td>Marketer enrichment — sample titles, taxonomy and coherence checks; for the first N ranked rows (<code>llm_top_n</code>), request OpenAI <code>summary</code> and <code>campaign_copy</code> only when checks pass, otherwise use canned/template outputs and suppress campaign copy when not marketing-safe.</td>
<td>See §2.2.</td>
</tr>
</tbody>
</table>

#### 2.1 Scoring for topic 2 (illustrative)

Scoring now happens on **topic-segment rows**, not only one topic-level aggregate.

- **Topic-segment expansion** — topic 2 can appear in one or more segments in a run (for example, `technology` on one day and `general` on another), based on video-level segment assignment.
- **Per-row signals** — each topic-segment row includes size, momentum, engagement, and recency-aware CTR signals.
- **Grouped ranking** — LambdaMART compares rows inside date+segment groups, so similar rows compete with each other.
- **Relevance labels** — each row gets a simple bucketed relevance score (0–4) from blended engagement/momentum gain within its group.
- **Final score** — `trend_score` combines the model score with stable anchor signals, then the output is merged into one display-friendly ranked list.

#### 2.2 Marketer-facing fields (illustrative)

| Field | Example |
|-------|---------|
| Keywords | meal prep, lunch, budget, kitchen |
| Suggested subject | Meal prep ideas subscribers are searching for now |
| Summary | Short paragraph on why the cluster matters in the window. |

#### 2.3 Offline ranking evaluation (no human labels)

Without editorial judgments, the pipeline surfaces proxy NDCG@N: it compares `trend_score` ordering to an ideal ordering by blended proxy gain on the same top-N ranked rows used for LLM calls. In the current flow those rows are topic-segment ranking rows. This metric is part of the standard run and supports engineering review; it is not a substitute for A/B tests or human evaluation. Set `log_ranking_evaluation=False` on `Settings` only to skip the block (for example in automation). Recompute from a saved CSV: `python -m src.evaluation outputs/topic_insights.csv`.

---

### 3. Related documents

| Document | Contents |
|----------|-----------|
| [architecture.md](architecture.md) | Module layout, diagrams, CSV contracts, `src/evaluation/` |
| [README.md](../README.md) | Install, configuration, execution, offline evaluation |
| [trend_pipeline_walkthrough.ipynb](../notebooks/trend_pipeline_walkthrough.ipynb) | Notebook walkthrough aligned with `main.py` |
