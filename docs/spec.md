# **gitsummary — Project Specification (v0.1)**


## **1. Project Overview**

`gitsummary` is a Python-based CLI tool that:

1. **Collects** pure-git-derived information between two Git tags (future: support for broader Git references).
2. **Generates an artifact** representing the semantic meaning of the change set.
3. **Stores this artifact in a `.gitsummary/` directory** for durability, versioning, and integration (future: Git-native mechanisms).
4. **Analyzes stored artifacts** to produce domain-specific facets (e.g., deployment impact).
5. Supports **interactive analysis** to let users clarify assumptions (optional future capability).

The system is designed to be **host-agnostic**, relying solely on the Git repository itself and not on platform metadata (GitHub/GitLab/etc.).

---

## **2. CLI Commands (Initial Set)**

### **2.1 `collect`**

```
gitsummary collect --tag <A> <B>
```

* Computes changes between two git tags (or, later, generic refs).
* Extracts pure-git facts (commit messages, diffs, file changes, metadata).
* Produces an **artifact**, a structured JSON document describing:

  * context (commit range, authors, dates)
  * intention (inferred)
  * implementation
  * impact
  * maintainability
  * deployment-related findings
  * meta information (schema version, confidence, evidence references)
* Writes the artifact into the `.gitsummary/` storage directory (see Section 4).
* Outputs:
  `Artifact created: <ART_OID>`

### **2.2 `analyze`**

```
gitsummary analyze <ART_OID> --target <facet>
```

* Loads the artifact identified by `<ART_OID>`.
* Runs analyzers to produce a facet-specific interpretation (e.g., `deployment`).
* Future: may support `--interactive` mode for clarification questions.

---

## **3. Artifact Structure (High-Level Schema)**

Each artifact produced during `collect` includes the following **agreed-upon sections**:

### **3.1 `context`**

* commit range (e.g., `A..B`)
* merge commit or end reference
* authors involved
* date range
* branches involved (if derivable)
* summary of commit messages

### **3.2 `intention` (inferred)**

* inferred goal of the change set
* inferred rationale
* inferred domain or subsystem affected
* inferred via LLM reasoning; no AST parsing involved

### **3.3 `implementation`**

* list of files changed
* added/removed LOC
* functions/classes added/modified/removed
* code patterns detected
* dependencies added/removed
* approximate complexity delta
* derived from diff metadata and heuristics (no AST traversal)

### **3.4 `impact`**

* inferred user-visible changes
* before/after behavioral description
* compatibility risks

### **3.5 `maintainability`**

* inferred tech debt created or reduced
* testing changes
* architectural implications
* refactor signals

### **3.6 `deployment`**

* new logs detected (patterns like `logger`, `console`, `print`)
* error-handling changes
* configuration changes (env, yaml, ini, Dockerfile, deploy scripts)
* infrastructure changes (k8s, helm, terraform, CI/CD)
* monitoring-related insights (recommended integration notes)

### **3.7 `meta`**

* confidence score per artifact or facet
* raw evidence references (commit hashes, diff excerpts)
* schema version

---

## **4. Storage Design**

Artifacts and supporting metadata are persisted **inside the repository working tree** under a dedicated directory rather than native Git refs.

### **4.1 `.gitsummary/` layout (POC canonical)**

```
.gitsummary/
  artifacts/
    <ART_OID>.json
  manifests/
    by-range/
      <A>..<B>.json            # pointer to <ART_OID>
  index/
    latest.json                # pointer to most recent <ART_OID>
  schema/
    version                    # "0.1.0"
  notes/                       # reserved for future use
    summary/
```

* **Artifact identity (`<ART_OID>`):** SHA-256 of the artifact JSON content.
* **Serialization:** natural `json.dumps` in the POC (future: canonical JSON for determinism).
* **Determinism:** not required in the POC; timestamps and ordering may vary run-to-run.
* **Analyzer outputs:** printed to stdout by default; persistence is deferred.

### **4.2 Git-native roadmap (future)**

The `.gitsummary/` directory mirrors a future Git-native implementation (refs, notes, GC safety). Those details remain in the roadmap but are **not part of the initial POC scope**.

---

## **5. Implementation Principles**

### **5.1 Pure Git, No Platform Dependencies**

* All collected data originates from Git itself:

  * diff
  * log
  * file changes
  * blame (collected by default)
  * tree structure
* No reliance on GitHub/GitLab APIs.

### **5.2 Python-Based CLI**

* Written in Python.
* Uses widely accepted, modern patterns.
* Will be packaged as a CLI tool.
* Typer framework.

### **5.3 Extensible Analyzer Architecture**

* `analyze` operates on top of stored artifacts.
* Each facet is a separate analyzer module.
* Facet example agreed upon: **deployment**.

### **5.4 Interactive Analysis Mode (Future)**

* Users may optionally enter an interactive loop to clarify intentions or assumptions.
* These clarifications may be stored alongside the artifact (future).

---

## **6. POC Direction and Future Roadmap**

### **6.1 POC Focus**

* Implement `collect` between two tags.
* Generate first-version artifacts.
* Store artifacts in the `.gitsummary/` directory structure described above.
* Implement a basic `deployment` analyzer.

### **6.2 Long-Term Vision**

* Treat artifacts as “semantic twins” of each change.
* Enable analytics across project history.
* Provide powerful release summaries, maintainability signals, and operational insights.
* Potential integration as a native Git extension.


# gitsummary — Decisions & Direction (v0.1)


## 1) Scope & Goals (POC)

* **Goal:** Provide a Python CLI to (1) **collect** pure-git facts for a range of commits between two tags and produce a rich **artifact**; (2) **analyze** that artifact for specific **facets** (starting with `deployment`) and print results to stdout.
* **Host-agnostic:** No use of GitHub/GitLab/Bitbucket APIs; rely only on the local Git repo.
* **Focus:** Shipping a working POC with simple, predictable behavior and a clean path to a future Git-native backend.

---

## 2) CLI Commands (POC)

### 2.1 `collect`

```bash
gitsummary collect --tag <A> <B>
```

* **Range semantics:** `A..B` (commits reachable from `B` and not from `A`).
* **Tags only in POC:** Accepts two **tags** as input. (Future: full Git ref syntax like `A..B`, branches, SHAs.)
* **Path filtering:** **None** in POC (no `--path`); analyze the entire repo per range.
* **Output:** Writes an artifact file to the local `.gitsummary` store and prints:

  ```
  Artifact created: <ART_OID>
  ```

### 2.2 `analyze`

```bash
gitsummary analyze <ART_OID> --target <facet>
```

* **Single facet per run** in POC (e.g., `--target deployment`).
* **Output:** Prints analysis to **stdout** (no persistence by default).
* **Interactive mode:** Planned for later; not required in POC.

---

## 3) Artifact Model (POC)

* **Content:**

  * `context`: commit range `A..B`, authors, date range, summary of commit messages.
  * `intention` *(inferred)*: goal, rationale, domain/subsystem (LLM-inferred; no AST parsing).
  * `implementation`: files changed, LOC added/removed, patterns detected, dependencies changed, rough complexity delta (diff- and heuristic-based).
  * `impact`: user-visible changes, before/after behavior, compatibility risks.
  * `maintainability`: tech debt delta, tests delta, architectural implications, refactor signals.
  * `deployment`: new logs, error handling changes, config/infra diffs (Dockerfile, CI, k8s/helm/terraform), monitoring notes.
  * `meta`: per-section confidence, evidence refs (commit+file+hunk), schema version, tool version, timestamps.
  * `alias`: **present but empty/null** in POC (reserved for future human-friendly aliasing).

* **Evidence references (analyzer outputs):**
  **Commit + file + hunk range** (e.g., `commit: "abc1234"`, `file: "src/x.py"`, `hunk: "@@ -21,7 +22,11 @@"`).

* **Blame data:**
  **Collected in POC** for changed files to enrich intention/ownership/maintainability signals.

* **Conventional Commits:**
  **Not parsed** in POC (LLM/code-first approach; assume messy commit messages).

---

## 4) Storage Backend (POC)

* **Filesystem-based (no Git integration yet):**
  Store in repo-local directory **`.gitsummary/`** with a structure that **mimics a future Git-native layout**.

* **Proposed POC layout:**

  ```
  .gitsummary/
    artifacts/
      <ART_OID>.json
    manifests/
      by-range/
        <A>..<B>.json            # pointer to <ART_OID>
    index/
      latest.json                # pointer to most recent <ART_OID>
    schema/
      version                    # "0.1.0"
    notes/                       # (reserved; empty in POC)
      summary/
  ```

* **Artifact identity (XXX):**
  **SHA-256 of the artifact JSON content**.

  * CLI accepts **prefixes** like Git (e.g., first 7–12 chars) when unambiguous.

* **Serialization:**
  POC uses **natural `json.dumps`** (no canonicalization).
  Future: switch to **canonical JSON** (sorted keys, stable whitespace) when determinism matters.

* **Determinism:**
  **Not required** in POC (timestamps/order may vary; IDs may differ across runs).

* **Analyzer outputs:**
  **Not persisted** by default (stdout only). Users can redirect output if they wish.
  (Future `--save` option possible, but analysis is not part of the core stored metadata.)

---

## 5) Ignore & Input Rules (POC)

* **Honor `.gitignore` exactly.**
* **Additional noise filtering:** support a repo-level **`.gitsummaryignore`** (POC convenience, may be revisited later).
  Default built-in patterns include (can be extended/overridden by `.gitsummaryignore`):

  * **Lockfiles:** `*.lock`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `poetry.lock`, `composer.lock`
  * **Build outputs:** `dist/`, `build/`, `target/`, `out/`, `__pycache__/`
  * **Vendored/bundled:** `vendor/`, `node_modules/`
  * **Minified/bundles:** `*.min.js`, `bundle.js`
  * **Binary blobs:** `*.zip`, `*.bin`, `*.tar`, `*.tar.gz`, `*.7z`
* **Diff size limits:** **None** in POC (process all non-ignored files fully).
* **AST parsing:** **None** in POC (no tree-sitter); rely on diffs, filenames, blame, and LLM reasoning.

---

## 6) Future Git-Native Direction (Not in POC)

> The POC’s directory structure and identifiers are intentionally chosen to map cleanly to a Git-native implementation later.

* **Future refs (short names):**

  * `refs/summary/main`
  * `refs/notes/summary`

* **Notes attachment:**
  Decision **deferred** for now; architecture will be **compatible** with attaching notes to the closing tag/commit by default later.

* **Push behavior:**
  **Deferred**; POC has **no push** logic and no remote interaction.

---

## 7) Analyzer Architecture (POC)

* **Built-in analyzers only**, designed to be **future-ready for plugins**.

  * Folder: `gitsummary/analyzers/` (e.g., `deployment.py`, `impact.py`, `maintainability.py`).
  * Simple `Analyzer` protocol/class: input = artifact dict; output = Python object (printed as JSON/Markdown to stdout).
* **Targets:** One facet per invocation (`--target <facet>`).
* **Output format:** To stdout; formatter may be JSON or human-readable text (facet decides or via a `--format` flag later).

---

## 8) Versioning & Metadata

* **Schema versioning:** **Semantic Versioning** `<major>.<minor>.<patch>`.

  * Initial: `"schema_version": "0.1.0"`.
  * Major = breaking, Minor = additive, Patch = non-structural fixes.
* **Tool version:** Embed the CLI’s own version in artifact `meta`.
* **Timestamps:** Allowed in POC; no determinism required.
* **Confidence:** Per facet/section confidence scores are allowed in `meta`.

---

## 9) UX & Ergonomics (POC)

* **CLI:** Python Typer.
* **Stdout by default:** Analyses are user-facing and ephemeral by design; artifacts are the durable, content-addressed metadata.
* **Errors:** Keep messages clear and Git-like. If no commits in range, return success with an empty/neutral artifact (implementation detail can evolve).
* **Config:** Read `.gitignore` + `.gitsummaryignore`; other config (models, limits, etc.) can be introduced later.

---

## 10) Summary of Key Decisions (Checklist)

* **Range semantics:** `A..B` ✅
* **Refs supported:** **Tags only** for POC; **full Git syntax later** ✅
* **Path filtering:** None in POC ✅
* **Artifact ID:** SHA-256 of JSON content (prefix accepted) ✅
* **Artifact alias field:** present but empty/null in POC ✅
* **Determinism:** Not required in POC ✅
* **Schema versioning:** SemVer; start at `0.1.0` ✅
* **Storage:** Filesystem `.gitsummary/` (Git-like layout) ✅
* **Analyzer outputs:** stdout only ✅
* **Push behavior:** Deferred (none in POC) ✅
* **Git notes:** Deferred; future-ready ✅
* **Ignore rules:** `.gitignore` + `.gitsummaryignore` defaults ✅
* **Diff size limits:** None in POC ✅
* **AST parsing:** None in POC ✅
* **Blame:** **Enabled** in POC ✅
* **Conventional commits:** Not parsed ✅
* **Analyzers:** Built-in only; future-ready for plugins ✅
* **Single facet per run:** Yes ✅
* **Evidence format:** commit + file + hunk range ✅
* **Serialization:** Natural `json.dumps` in POC; canonical later ✅

---

## 11) Example POC Workflow

```bash
# Collect an artifact for a release range
gitsummary collect --tag 0.1 0.2
# → Artifact created: 3fa4c021bc7e9f1f6c3d92da0d98cefd88b3fcd9

# Analyze deployment facet and print to stdout
gitsummary analyze 3fa4c021 --target deployment
# → (stdout) JSON or Markdown with deployment insights
```
