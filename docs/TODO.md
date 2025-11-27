# gitsummary – Sequential Work Plan

A step‑by‑step workload breakdown for designing and implementing **gitsummary**.  
Each step builds on the previous one and has clear outputs that feed the next phase.

---

## 1. Ground the Problem & Constraints

**Goal:** Ensure the project vision, constraints, and target users are explicit and stable before designing anything.

**Tasks:**
- [ ] Re‑read `docs/project_summary.md` and existing goals/motivation docs.
- [ ] Capture non‑negotiable constraints (pure Git source, offline, Git‑Notes‑based storage, etc.).
- [ ] List primary target users and their top 3 jobs‑to‑be‑done.
- [ ] Write a short, 1–2 paragraph **Problem Statement** and add it to the docs.

**Output / Exit criteria:**
- A single, concise problem statement and constraint list that the rest of the work will assume.

---

## 2. Define the Artifact Schema v0

**Goal:** Design the core “artifact” data model that represents semantic information about a change range.

**Tasks:**
- [ ] Enumerate all facets from the docs (context, intention, implementation, impact, maintainability, deployment, meta).
- [ ] For each facet, define:
  - Required vs optional fields
  - Data types (string, list, enum, numeric, references, etc.)
  - Expected value ranges / formats
- [ ] Decide how to represent evidence links back to commits, files, hunks.
- [ ] Version the schema (e.g. `schema_version` field) and note migration expectations.
- [ ] Document the schema in `docs/artifact_schema.md`.

**Output / Exit criteria:**
- A versioned JSON‑serializable schema specification for a single artifact, with examples.

---

## 3. Design Git Notes Storage Layout

**Goal:** Decide exactly how artifacts are stored in Git Notes so they are durable, portable, and easy to query.

**Tasks:**
- [x] Choose one or more notes namespaces (e.g. `refs/notes/artifacts`).
- [x] Decide what object(s) notes attach to:
  - Individual commits
  - Tags
  - Synthetic “range” objects (e.g. pseudo‑IDs for commit ranges)
- [x] Define how to reference a **change range** artifact (e.g. store range metadata in the note attached to the tip commit, or via a separate index structure).
- [x] Decide on serialization format (likely JSON, UTF‑8, untouched by Git filters).
- [x] Design a minimal index/lookup strategy where needed (e.g. map artifact IDs to commit hashes).
- [x] Document layout & conventions in `docs/storage_layout.md`.

**Output / Exit criteria:**
- A clear mapping between `ArtifactID` ⇄ Git objects ⇄ Git Notes namespace, with examples.

---

## 4. CLI Surface Design

**Goal:** Define the initial CLI that developers and tools will actually use.

**Tasks:**
- [x] Specify core commands and flags (no implementation yet):
  - `gitsummary analyze` (extract semantic understanding, store artifacts)
  - `gitsummary generate` (produce reports from stored artifacts)
  - `gitsummary show` (human‑friendly view of an artifact)
  - `gitsummary list` (list artifacts for a range / branch / tag)
- [x] For each command, define:
  - Inputs (commit range, tags, branches, artifact ID)
  - Outputs (JSON to stdout, pretty text, exit codes)
  - Non‑goals for v0 (what this command will *not* do yet).
- [x] Write a short CLI spec in `docs/cli_design.md` with usage examples.
- [x] Document naming rationale (`analyze` → `generate` two-phase model)

**Output / Exit criteria:**
- A stable v0 CLI spec that can be implemented without further structural changes.

**Key Design Decision:** Adopted `analyze` → `generate` naming scheme based on industry patterns (semantic-release, git-cliff). See `workdir/step-4-cli-design.md` for full rationale.

---

## 5. Implement Core Git Range & Diff Collector (Pure Git)

**Goal:** Build a minimal, well‑tested layer that turns Git commit ranges into structured raw data, without any AI/semantics.

**Tasks:**
- [ ] Implement a Python module that:
  - Resolves commit ranges (commits, tags, branches).
  - Extracts commit metadata (author, date, message, parents).
  - Extracts diffs, file paths, file types, and hunks.
- [ ] Ensure implementation uses only Git executables / object model (no GitHub/GitLab APIs).
- [ ] Define a typed internal representation (Python dataclasses or similar) for “raw change data”.
- [ ] Add tests using a small fixture repo to validate range resolution and diffs.

**Output / Exit criteria:**
- Given `A..B`, the system produces a deterministic “raw change description” structure suitable as input to artifact generation.

---

## 6. Implement Artifacts Construction (Raw → Artifact Schema)

**Goal:** Convert raw Git data into a v0 artifacts instance according to the schema defined in the previous step.

**Tasks:**
- [ ] Implement a builder that:
  - Fills the **Context** facet directly from commit metadata.
  - Constructs artifacts instances (using LLM to map raw collected data to the artifacts schemas).
  - Populates **Implementation** facet with files changed, counts, and simple signals (e.g. added/removed lines per file).
- [ ] Generate a unique `artifact_id` and attach `schema_version`.
- [ ] Write / update unit tests to assert artifact structure correctness.
- [ ] Add a `--dry-run` mode to dump artifacts to stdout for inspection.

**Output / Exit criteria:**
- A reproducible, schema‑conformant artifact JSON generated purely from Git for a commit range.

---

## 7. Wire Artifacts into Git Notes

**Goal:** Persist artifacts using the Git Notes layout defined earlier.

**Tasks:**
- [ ] Implement a storage module to:
  - Write artifact JSON as a note for a chosen Git object (e.g. tip commit).
  - Read artifact JSON back from notes.
  - Handle idempotent writes (avoid duplicates when regenerating).
- [ ] Ensure operations behave well with `git fetch`, `git push --notes`, and GC.
- [ ] Add tests that:
  - Create a temp repo.
  - Write an artifact via notes.
  - Confirm the note can be fetched and parsed correctly.

**Output / Exit criteria:**
- Running `gitsummary collect A..B` yields an artifact stored in Git Notes, retrievable by CLI and Python APIs.

---

## 8. Add Semantic Analysis Facets (LLM / Heuristic Layer)

**Goal:** Enrich basic artifacts with higher‑level semantics (intention, impact, maintainability, deployment, etc.).

**Tasks:**
- [ ] Define a clear interface for analyzers, e.g. `analyze_<facet>(artifact, raw_data) -> facet_update`.
- [ ] Implement at least the following v0 analyzers LLM‑backed:
  - **Intention**: inferred purpose and rationale.
  - **Impact**: user‑visible or API behavior changes.
  - **Maintainability**: refactor vs debt, test deltas, complexity signals.
  - **Deployment**: config/log/monitoring changes and operational notes.
- [ ] Decide and document how analysis is triggered:
  - During `collect` (eager)
  - Or via separate `analyze` command (lazy / incremental).
- [ ] Ensure analyzers store their outputs back into the artifact while preserving previous facets.

**Output / Exit criteria:**
- `gitsummary analyze <ARTIFACT_ID>` updates an existing artifact with semantic facets and writes them back to notes.

---

## 9. Implement CLI Commands Against the Core API

**Goal:** Provide a usable developer‑facing CLI wired into the collector, analyzer, and storage layers.

**Tasks:**
- [ ] Implement `gitsummary analyze` using Git range collector + LLM extraction + notes storage.
- [ ] Implement `gitsummary generate <type>` using the report generator framework.
- [ ] Implement `gitsummary show` to pretty‑print an artifact (selectable facets).
- [ ] Implement `gitsummary list` to list artifacts for branches/tags/ranges.
- [ ] Support `--json` flag for machine‑readable outputs.
- [ ] Add robust error messages and exit codes.
- [ ] Migrate legacy `collect` command to `analyze`, `analyze --target` to `generate`.

**Output / Exit criteria:**
- End‑to‑end CLI flow: `analyze` → `generate` → `show` works on a test repo.

---

# Once satisfied, ship and show the remaining work:

## 10. Testing, Fixtures & Quality Gates

**Goal:** Establish confidence in behavior across different repositories and workflows.

**Tasks:**
- [ ] Create fixture repositories representing:
  - A simple toy project (hello world).
  - A mid‑size app with branches and tags.
  - A repo with poor commit messages and noisy diffs.
- [ ] Add integration tests that:
  - Run full CLI flows on fixture repos.
  - Validate artifacts against schema.
  - Assert Git Notes are written and read correctly.
- [ ] Add CI workflow to run tests and linters.
- [ ] Define minimal quality gates for accepting schema or CLI changes.

**Output / Exit criteria:**
- Green CI for all core flows; artifacts validated against schema in tests.

---

## 11. Documentation & Developer Experience

**Goal:** Make the tool understandable and pleasant to adopt for both humans and AI agents.

**Tasks:**
- [ ] Write a high‑level **Concepts** doc (artifact, facets, notes, analyzers).
- [ ] Add a **Quickstart** using a small sample repo, with copy‑pasteable commands.
- [ ] Document how to consume artifacts from:
  - CLI (`--json` output)
  - Python API
  - Git Notes directly.
- [ ] Add examples of downstream uses (release notes, architecture docs, semantic search).

**Output / Exit criteria:**
- Someone new to the repo can install, run `gitsummary` on a sample repo, and understand artifacts within 10–15 minutes.

---

## 12. Packaging, Versioning & Distribution

**Goal:** Ship a coherent v0 release that others can install and try.

**Tasks:**
- [ ] Package the project as a Python package (e.g. via `pyproject.toml`).
- [ ] Provide simple installation instructions (e.g. `pipx install gitsummary`).
- [ ] Define versioning strategy (e.g. semantic versioning, with schema changes called out).
- [ ] Tag a v0.1.0 release in Git.
- [ ] Optionally, publish release notes generated by gitsummary itself.

**Output / Exit criteria:**
- A tagged release that a user can install and run with documented expectations.

---

## 13. Dogfooding & Feedback Loop

**Goal:** Use gitsummary on real projects (including itself) to validate assumptions and refine.

**Tasks:**
- [ ] Enable gitsummary on one or two real repos (e.g. this project + a small app like `todoapp`).
- [ ] Collect feedback on:
  - Artifact usefulness for developers and release managers.
  - Accuracy / helpfulness of semantic facets.
  - Pain points in CLI UX and performance.
- [ ] Turn feedback into concrete TODO items for the next iteration (v0.2+).

**Output / Exit criteria:**
- A prioritized backlog of improvements informed by real‑world usage.

