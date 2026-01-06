# Commit Artifact Brainstorm (Extensions)

Goal: extend commit artifacts with provenance, cost, and qualitative signals to  
improve planning, review, and reporting.

## Current Artifact Fields

*   `commit_hash`
*   `schema_version`
*   `intent_summary`
*   `category`
*   `behavior_before`
*   `behavior_after`
*   `impact_scope`
*   `is_breaking`
*   `technical_highlights`
*   Storage metadata (not in schema today): `tool_version`

## Why add more fields (benefits)

*   **Cost visibility**: understand LLM spend per commit analysis, per repo analysis, per release analysis.
*   **Quality controls**: detect when LLM results were weak (low confidence).
*   **Review prioritization**: surface high‑risk or high‑difficulty commits.
*   **Process insights**: measure where time/effort goes; identify noisy commits.
*   **Product metrics**: quantify impact/complexity over time for releases.

## Proposed Additions

### 1) Provenance / process

**Fields**

*   `analysis_mode`: `llm | heuristic | hybrid`
*   `provider`, `model`, `prompt_version`
*   `analysis_timestamp`, `analysis_duration_ms`
*   `fallback_reason` (if LLM failed or timed out)

**Benefits**

*   Traceability: reproduce artifacts with same model/prompt.
*   Debugging: spot provider failures, rate limits, or fallback paths.
*   Audit trail: explain why output differs across runs.

**How to collect**

*   `analysis_mode`: set in AnalyzerService depending on LLM success.
*   `provider`/`model`: from provider config (`LLMResponse.model`).
*   `prompt_version`: manual constant in prompt module.
*   `analysis_timestamp`: UTC now at analyze time.
*   `analysis_duration_ms`: measure per commit analysis call.
*   `fallback_reason`: exception name/message or standard enum.

### 2) Token usage + cost

**Fields**

*   `token_usage`: `{input, output, cached(optional)}`

**Benefits**

*   Budgeting: estimate per‑repo or per‑release token.
*   ROI: identify commits that are expensive but low‑value.
*   Ops: detect outlier prompts that produce token spikes.

**How to collect**

*   Tokens: use provider response (`LLMResponse.prompt_tokens`, `completion_tokens`).

### 3) Input size / scope

**Fields**

*   `commit_message_chars`, `commit_message_lines, commit_message_tokens (estimation based on 3 tokens per word)`
*   `diff_files`, `diff_insertions`, `diff_deletions`, `diff_total`
*   `diff_hunks`

**Benefits**

*   Scale signals: correlate size with difficulty, review effort, risk.
*   Release summaries: quantify change size without scanning diffs.
*   Prompt tuning: decide when to trim diffs for LLM.

**How to collect**

*   Message size: from `CommitInfo.full_message`.
*   Diff stats: `CommitDiff.stat` and `FileDiff` list; `git diff --numstat`.
*   Hunks: count `FileDiff.hunks`.

### 4) Qualitative signals (requested)

**Fields**

*   `technical_difficulty` (0–10) + explanation
*   `creativity` (0–10) + explanation
*   `mental_load` (0–10) + explanation
*   `review_effort` (0–10) + explanation
*   `ambiguity` (0–10) + explanation

**Benefits**

*   Reviewer assignment: pair complex commits with stronger reviewers.
*   Process insights: detect areas of high mental load or ambiguity.
*   Retrospective analysis: spot chronic complexity hotspots.

**How to collect**

*   LLM‑generated scores with a short rubric prompt.
*   no Heuristic approximation when no LLM.

## Light Rubrics (for consistency)

*   `technical_difficulty`: 0 trivial rename → 10 architecture/complex algorithm
*   `creativity`: 0 boilerplate → 10 novel pattern/solution
*   `mental_load`: 0 routine → 10 high context/multi-system
*   `review_effort`: 0 quick → 10 multi-file, subtle, high risk
*   `ambiguity`: 0 clear intent → 10 unclear intent

## Data Sources (existing plumbing)

*   Token usage: LLM provider response (`input/output/cached`).
*   Diff stats in char + lines + tokens (estimated by 3 tokens per word): `CommitDiff.stat`, `FileDiff`, `git diff --numstat`.
*   Message size in tokens: `CommitInfo.full_message`.
*   Languages: file extensions from `CommitDiff.files`.

## Storage Design Notes

*   Keep additions optional (backwards compatible).
*   Group new fields under `analysis_meta` to reduce top‑level clutter.
*   Consider `analysis_meta.llm` and `analysis_meta.heuristics` subobjects.
*   Persist tokens even when artifact is stored in Postgres.
*   Avoid storing full prompt text unless needed (privacy, size).