# Hiver Take-Home — Build Spec (pre-implementation design doc)

Purpose of this doc: no more design decisions while coding. Every file, schema, and interface is fixed here so implementation is just filling in the blanks in order.

---

## 1. Repo structure

```
hiver-support-agent/
├── README.md
├── DECISIONS.md                     # decision log, append as you go
├── REPORT.md                        # final report (or /report/*.md if you split it)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── Makefile                         # make sample-data / make index / make eval / make serve
│
├── data/
│   ├── raw/                         # .gitignored — full Kaggle CSV goes here, never committed
│   ├── sample/                      # committed — filtered subset for chosen brand (csv/parquet)
│   ├── golden/                      # committed — hand-labeled eval set
│   │   └── golden_set.jsonl
│   └── grounding/                   # committed — indexed resolved-thread pairs (pre-embedding, jsonl)
│       └── resolved_threads.jsonl
│
├── scripts/
│   ├── 01_sample_data.py            # raw CSV -> data/sample/ (brand filter)
│   ├── 02_build_taxonomy.py         # clustering -> data/intent_taxonomy.json
│   ├── 03_build_grounding_corpus.py # thread reconstruction -> data/grounding/resolved_threads.jsonl
│   ├── 04_build_index.py            # embed + write to ChromaDB
│   ├── 05_label_golden_set.py       # CLI labeling helper (optional, can also label by hand in a spreadsheet)
│   └── 06_run_eval.py               # runs harness end-to-end, prints/saves headline table
│
├── frontend/                        # optional but recommended — see §3.5
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api.js                   # thin fetch wrapper around the FastAPI endpoints
│       ├── components/
│       │   ├── MessageInput.jsx
│       │   ├── PipelineTrace.jsx    # shows intent -> retrieval -> draft -> route, step by step
│       │   ├── RetrievedEvidence.jsx
│       │   ├── DecisionBadge.jsx    # auto_handle / escalate + reason
│       │   └── EvalDashboard.jsx    # renders eval/results/*.json as tables/charts
│       └── pages/
│           ├── TryAgent.jsx         # live single-message demo
│           └── EvalResults.jsx      # headline metrics, baseline comparison, confusion matrix
│
├── app/
│   ├── main.py                      # FastAPI app, POST /handle-message
│   ├── config.py                    # env vars, model names, thresholds (all in one place)
│   ├── schemas.py                   # pydantic models (see §4)
│   ├── pipeline/
│   │   ├── graph.py                 # LangGraph wiring of the 4 nodes
│   │   ├── classify.py              # node 1
│   │   ├── retrieve.py              # node 2
│   │   ├── draft.py                 # node 3
│   │   └── route.py                 # node 4
│   ├── baselines/
│   │   ├── trivial.py               # canned reply + rule routing
│   │   └── simple.py                # TF-IDF/logreg classifier + nearest-neighbor reply
│   └── llm/
│       ├── client.py                # multi-provider wrapper (Groq / Gemini / etc.)
│       └── prompts/
│           ├── classify.txt
│           ├── draft.txt
│           └── judge.txt
│
├── eval/
│   ├── harness.py                   # loads golden set, runs all 3 systems, computes metrics
│   ├── metrics.py                   # accuracy/F1/precision/recall/confusion matrix helpers
│   ├── judge.py                     # LLM-as-judge scoring
│   ├── judge_agreement.py           # human vs judge agreement calc (kappa etc.)
│   └── results/                     # output tables/json, committed for the report
│
└── notebooks/
    └── exploration.ipynb            # brand selection, clustering exploration — not graded, keep it honest/messy
```

---

## 2. Data pipeline — exact steps

### 2.1 `01_sample_data.py`

Input: Kaggle `twcs.csv` (or split files) placed manually in `data/raw/` (document this in README — don't try to auto-download, Kaggle auth is annoying and not worth automating for a take-home).

Steps:

1. Load CSV. Columns you need: `tweet_id, author_id, inbound, created_at, text, response_tweet_id, in_response_to_tweet_id`.
2. Identify brand account `author_id` (e.g. `AmericanAir`) — this is the constant for `inbound=False` rows you're targeting.
3. Reconstruct threads: for each brand tweet, walk `in_response_to_tweet_id` backward to the root inbound tweet, and walk `response_tweet_id` forward to see if there's a further customer reply (multi-turn) — for v1, **only keep single-customer-message → brand-reply pairs** (first inbound tweet, first brand reply); flag multi-turn threads as out-of-scope, note the % you dropped (report material).
4. Output: `data/sample/{brand}_threads.parquet` with columns: `thread_id, customer_tweet_id, customer_text, customer_created_at, brand_tweet_id, brand_text, brand_created_at, has_further_customer_reply (bool)`.
5. Print and save summary stats: total threads, date range, median response latency — useful context for the report.

Target subsample size: 3,000–8,000 threads. Enough for clustering + grounding corpus + golden set with room to spare, small enough to run fast and cheap.

### 2.2 `02_build_taxonomy.py`

1. Sample 300 `customer_text` values (stratified by month to avoid recency bias if the CSV is chronological).
2. Embed with a small model (e.g. `sentence-transformers/all-MiniLM-L6-v2` — free to run locally, no API cost).
3. KMeans, try k=8..15, pick by eyeballing silhouette score + manual coherence check (read 10 examples per cluster).
4. For each final cluster: write a name + 1-sentence definition + 3 example texts to `data/intent_taxonomy.json`:

```json
{
  "intents": [
    {
      "id": "flight_delay_cancellation",
      "label": "Flight delay or cancellation",
      "description": "Customer reports a delayed or cancelled flight and wants status, rebooking, or compensation.",
      "examples": ["...", "...", "..."]
    }
  ]
}
```

5. Always append a manual `other_unclear` intent even if no cluster maps cleanly to it.

### 2.3 `03_build_grounding_corpus.py`

1. From `data/sample/{brand}_threads.parquet`, define "resolved" = brand reply text does **not** match a handoff-pattern regex (`\bDM\b`, `\bdirect message\b`, `send.*info`, phone numbers, "call us at") **and** does not simply ask a clarifying question with no content. Keep it simple and rule-based — document the regex in DECISIONS.md, note the false positive/negative risk explicitly (this is real "misleading number" material).
2. For threads that pass, run `02`'s intent classifier (nearest-centroid to taxonomy examples, or just the LLM classifier once built — either is fine, document which) to tag each with an intent.
3. Output: `data/grounding/resolved_threads.jsonl`, one object per line:

```json
{"thread_id": "...", "intent": "flight_delay_cancellation", "customer_text": "...", "brand_text": "..."}
```

Target: 500–2,000 grounding pairs after filtering (expect to lose 40-70% of threads to the handoff filter — report the exact number).

### 2.4 `04_build_index.py`

1. Spin up ChromaDB (persistent client, local dir `data/chroma/`, gitignored — index is rebuildable from `resolved_threads.jsonl`).
2. Collection name: `grounding_v1`.
3. Embed `customer_text` (the query side) with the same embedding model as taxonomy clustering, for consistency.
4. Store metadata: `{intent, brand_text, thread_id}` alongside each vector so retrieval returns the resolution text directly, filterable by intent.

---

## 3. Pipeline nodes — exact I/O contracts

Every node takes and returns a plain dict/pydantic model so LangGraph state is inspectable and you can log intermediate state per example for failure analysis (critical — don't skip this, you'll need it for §"failure analysis" in the report).

### Node 1 — `classify.py`

**Input:** `{ "customer_text": str }`
**Output:**

```json
{ "intent": "flight_delay_cancellation", "confidence": 0.83, "raw_model_output": "..." }
```

Implementation: LLM call (cheap/fast model — Groq) with taxonomy definitions + 1–2 few-shot examples per intent (pulled from `intent_taxonomy.json` examples, never from golden set) in the prompt. Ask model to also emit a confidence 0-1 self-estimate; **don't fully trust this** — calibrate it against your dev slice (bucket confidence into 3 bins, check actual accuracy per bin, report the calibration, adjust threshold accordingly). This calibration check is a good decision-log entry.

### Node 2 — `retrieve.py`

**Input:** `{ "customer_text": str, "intent": str, "confidence": float }`
**Output:**

```json
{
  "retrieved": [
    {"thread_id": "...", "brand_text": "...", "customer_text": "...", "similarity": 0.71}
  ]
}
```

Logic: query ChromaDB top-k=5 filtered to `intent` (metadata filter). If confidence < threshold (set from calibration above, e.g. 0.5), widen filter to top-2 intents or drop the filter entirely and rely on pure similarity — document which you chose. If top similarity < a floor (e.g. 0.3 cosine — pick empirically from a handful of manual checks), return empty list — this becomes a routing signal ("no precedent found").

### Node 3 — `draft.py`

**Input:** `{ "customer_text": str, "intent": str, "retrieved": [...] }`
**Output:**

```json
{ "draft_reply": "...", "cited_thread_ids": ["..."] }
```

Prompt (`prompts/draft.txt`) structure:

```
You are a support agent for {BRAND}. Match this tone: {2-3 sentence tone description you wrote by hand from skimming real replies}.
Customer intent: {intent label + description}
Here is how similar issues were resolved before:
{for each retrieved example: customer text + brand resolution}
Customer's message: {customer_text}
Write a short (<280 char), specific reply. Reference a concrete next step or resolution drawn from the examples above. If none of the examples actually apply, say so plainly instead of inventing a policy.
```

Use the stronger model here (Gemini or similar) — quality matters more than latency for drafting.

### Node 4 — `route.py`

**Input:** everything above.
**Output:**

```json
{ "decision": "auto_handle" | "escalate", "reason": "..." }
```

Rule order (first match wins — implement as an explicit if/elif chain, not a black box, so it's easy to explain live):

1. `intent in MUST_ESCALATE_INTENTS` (define this list explicitly in `config.py` — e.g. safety, legal threat, payment dispute, anything your data shows brand agents themselves always handed off) → escalate, reason = "high-risk intent category".
2. `confidence < CONFIDENCE_THRESHOLD` → escalate, reason = "low classification confidence".
3. `len(retrieved) == 0` or `top similarity < SIMILARITY_FLOOR` → escalate, reason = "no comparable historical resolution found".
4. Optional: LLM self-check on the draft — "does this reply state anything not supported by the retrieved examples?" → if yes, escalate, reason = "draft contains unsupported claim".
5. Else → auto_handle, reason = "matched precedent with high confidence".

All thresholds live in `config.py` as named constants with a one-line comment on how you picked the value (from calibration/dev-slice sweep, not vibes).

---

## 3.5 Frontend architecture

Not required by the assignment brief, but worth the ~half-day it costs: reviewers will "run your code" and a UI where they can paste a tweet and watch the pipeline reason through it is far more convincing live than reading JSON off a terminal. Keep it small and honest — this is a demo instrument for your eval work, not a product.

**Stack:** React + Vite, plain JavaScript (no TypeScript) — no state library needed, this is small enough for `useState`/`useReducer`. Plain CSS or Tailwind, whichever you reach for faster; don't spend design time here, spend it on making the pipeline trace legible. Since there's no compile-time type checking here, treat `app/schemas.py` as the single source of truth for the response shape and keep `api.js` as a thin, un-typed pass-through — don't hand-roll a parallel type system in JS, just destructure fields where you use them (`const { intent, confidence, retrieved, draft_reply, decision, reason } = result`).

**Two pages only:**

1. **`TryAgent`** — a textbox for a customer message, a "Run" button, and a *step-by-step trace* of the pipeline response, not just the final answer:

   - Step 1 card: predicted intent + confidence (color-coded against `CONFIDENCE_THRESHOLD` so a reviewer can see at a glance why a decision went the way it did)
   - Step 2 card: retrieved examples, each showing the historical customer text + brand resolution + similarity score
   - Step 3 card: the drafted reply
   - Step 4 card: decision badge (auto-handle / escalate) with the stated reason, and which rule in `route.py` fired
   - A toggle to run the **trivial** and **simple** baselines on the same input side-by-side — this single feature does a lot of work for you in a live review, since "here's why my system beats the baselines" becomes a live demo instead of a table they have to trust.
2. **`EvalResults`** — reads the static JSON your harness already writes to `eval/results/`, no backend logic needed beyond serving the files (or just `fetch`-ing them if you serve `eval/results/` as static files from FastAPI). Renders: headline metrics table (3 systems side by side), confusion matrix for intent classification, routing precision/recall, judge score distribution, and the judge-human agreement number front and center — don't bury your honesty metric.

**API contract:** the frontend talks to exactly two endpoints, both already implied by the backend spec:

- `POST /handle-message` → `HandleMessageResponse` (§4), used by `TryAgent`, called once per selected system (full pipeline, and optionally trivial/simple baselines behind the same interface — see §"baselines" note below).
- `GET /eval-results` → serves the contents of `eval/results/*.json` — add this one endpoint to `app/main.py`, it's the only backend addition needed for `EvalResults`.

**Baseline parity requirement:** for the side-by-side toggle in `TryAgent` to work, `baselines/trivial.py` and `baselines/simple.py` need to be callable through the same FastAPI route (e.g. `POST /handle-message?system=trivial|simple|full`), returning the same `HandleMessageResponse` shape even though some fields will be trivial (e.g. baseline `retrieved` can be empty or a single nearest-neighbor match, `reason` can be a fixed string for the rule-based router). This is a small addition to `app/main.py` — worth doing now while you're building the endpoint rather than retrofitting later.

**What to skip:** auth, routing/multi-page nav libraries, loading-state polish beyond a basic spinner, mobile responsiveness, anything resembling a real agent-facing tool (queue view, bulk actions, etc.) — that's out of scope per §1's "what I chose not to build," and building it would eat time better spent on the eval harness.

---

## 4. Schemas (`app/schemas.py`)

```python
class HandleMessageRequest(BaseModel):
    customer_text: str

class RetrievedExample(BaseModel):
    thread_id: str
    customer_text: str
    brand_text: str
    similarity: float

class HandleMessageResponse(BaseModel):
    intent: str
    confidence: float
    retrieved: list[RetrievedExample]
    draft_reply: str
    decision: Literal["auto_handle", "escalate"]
    reason: str
```

This is also your eval harness's per-example log format — extend with `system_name` ("trivial"/"simple"/"full") and `latency_ms`, `cost_estimate` when logging eval runs, since cost/latency comparisons across baselines are easy bonus content for the report.

---

## 5. Golden set schema (`data/golden/golden_set.jsonl`)

```json
{
  "id": "g001",
  "customer_text": "...",
  "gold_intent": "flight_delay_cancellation",
  "gold_decision": "escalate",
  "gold_reason_category": "high-risk intent category",
  "reply_criteria": [
    "acknowledges the delay",
    "gives a concrete next step (rebooking link, status check, or compensation process)",
    "does not promise a refund amount"
  ],
  "difficulty_tag": "sarcasm | multi_issue | ambiguous | clean | code_mixed",
  "source_thread_id": "..."
}
```

`reply_criteria` (checklist form) is more defensible in review than a single "gold reply" string, and it's what your LLM judge should score against per-item, not a generic rubric.

Labeling process to document in README:

1. Stratified sample across intents (roughly proportional to taxonomy cluster sizes, with rare intents oversampled to ≥10 examples each).
2. Deliberately inject ~15–20% "hard" tagged examples (sarcasm, multiple issues in one tweet, emoji-only, non-English fragments) by searching for them, not just random sampling — random sampling alone will under-represent them.
3. Label in a spreadsheet or via `05_label_golden_set.py` CLI (show text, prompt for intent/decision/criteria).
4. Relabel a blind 15–20 sample after a break; compute your own self-agreement; report it.

---

## 6. Eval harness (`eval/harness.py`)

Pseudocode:

```
for system in [trivial, simple, full]:
    for example in golden_set:
        result = system.run(example.customer_text)
        log(system, example.id, result)

compute_intent_metrics(logs)      # accuracy, macro-F1, confusion matrix, per system
compute_routing_metrics(logs)     # precision/recall/F1 for "should escalate" as positive class
compute_judge_scores(logs)        # LLM judge on draft_reply vs reply_criteria, per system
compute_cost_latency(logs)        # avg cost + latency per system

save_all_to(eval/results/)
print_headline_table()
```

**Judge (`eval/judge.py`)**: for each (example, draft_reply) pair, prompt the judge model with the `reply_criteria` checklist and ask for per-criterion pass/fail + a 1-5 overall score + a one-line justification citing which retrieved example (if any) supports the claim. Store raw judge output for the agreement study.

**Judge agreement (`eval/judge_agreement.py`)**: sample ~40-60 judge-scored examples, you re-score blind (hide the judge's score), compute exact-match % and weighted Cohen's kappa on the 1-5 scale. Report both — don't cherry-pick the flattering one.

---

## 7. Config (`app/config.py`) — everything tunable in one file

```python
CLASSIFY_MODEL = "groq/llama-3.x-..."     # cheap/fast
DRAFT_MODEL = "gemini-..."                 # stronger
JUDGE_MODEL = "..."                        # ideally different from DRAFT_MODEL to reduce self-preference bias — note this explicitly

CONFIDENCE_THRESHOLD = 0.55   # set from calibration sweep on dev slice, see DECISIONS.md
SIMILARITY_FLOOR = 0.30       # set from manual spot-check, see DECISIONS.md
TOP_K_RETRIEVAL = 5
MUST_ESCALATE_INTENTS = ["legal_safety", "payment_dispute"]  # from taxonomy + brand judgment
```

---

## 8. Build order checklist (tick off in order — each step is independently testable)

- [ ] `01_sample_data.py` runs, prints thread counts, saves parquet
- [ ] Manual brand-selection notebook comparison across 3 candidates, decision written to DECISIONS.md
- [ ] `02_build_taxonomy.py` produces `intent_taxonomy.json`, manually reviewed for coherence
- [ ] `03_build_grounding_corpus.py` produces `resolved_threads.jsonl`, filter-rate logged
- [ ] `04_build_index.py` — spot-check 5 manual queries against the index, confirm retrieval looks sane before wiring into the pipeline
- [ ] `classify.py` node working standalone (test with 10 hand-picked examples covering all intents)
- [ ] `retrieve.py` node working standalone
- [ ] `draft.py` node working standalone (read 10 outputs manually — does it sound like the brand?)
- [ ] `route.py` node working standalone (test each rule branch with a constructed example)
- [ ] `graph.py` wires all 4 nodes, `POST /handle-message` returns full `HandleMessageResponse`
- [ ] `baselines/trivial.py` and `baselines/simple.py` implemented and callable with the same interface (`?system=` param)
- [ ] `GET /eval-results` endpoint serving `eval/results/*.json`
- [ ] Frontend: `TryAgent` page wired to `/handle-message`, trace renders all 4 steps + baseline toggle
- [ ] Frontend: `EvalResults` page wired to `/eval-results`, headline table + confusion matrix + judge agreement visible
- [ ] Golden set labeled (150-250), `reply_criteria` written per item
- [ ] `eval/harness.py` runs all 3 systems end-to-end, saves results
- [ ] `eval/judge.py` + `eval/judge_agreement.py` run, agreement number obtained (good or bad — report it)
- [ ] Threshold calibration pass (confidence bins, similarity floor) — update `config.py`, note in DECISIONS.md
- [ ] Failure analysis: filter eval logs for wrong/low-scoring examples, pick top 5 patterns
- [ ] README written and tested on a clean checkout, timed (<15 min)
- [ ] REPORT.md written (5 sections per assignment spec)
- [ ] DECISIONS.md finalized (10-15 bullets)
- [ ] Submit via Notion form with repo link

---

## 9. Things to decide the moment you touch real data (don't pre-decide, but don't forget either)

- Exact brand — only after the 3-candidate comparison in step 1.
- Exact intent count and names — only after reading real clusters.
- `MUST_ESCALATE_INTENTS` — only after seeing what categories actually show up.
- Thresholds — only after calibration sweeps, not before.

Everything else in this doc is fixed; these four are intentionally left for contact with the data.
