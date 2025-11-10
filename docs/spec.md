# **gitsummary — Project Specification (v0.1)**


## **1. Project Overview**

`gitsummary` is a Python-based CLI tool that:

1. **Collects** pure-git-derived information between two Git references (`tags`, `commits`, or revision ranges).
2. **Generates an artifact** representing the semantic meaning of the change set.
3. **Stores this artifact using Git-native mechanisms** for durability, versioning, and integration.
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
* Writes the artifact into a **Git-native storage layer** (see Section 4).
* Outputs:
  `artifact <ART_OID> created`

### **2.2 `analyze`**

```
gitsummary analyze <ARTIFACT_ID> --target <facet>
```

* Loads the artifact identified by `<ARTIFACT_ID>`.
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

### **3.3 `implementation`**

* list of files changed
* added/removed LOC
* functions/classes added/modified/removed
* code patterns detected
* dependencies added/removed
* approximate complexity delta

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

## **4. Git-Native Storage Design**

Artifacts and analyses are stored **inside the Git repository** using Git’s native data model.

### **4.1 Canonical Artifact ID**

* The artifact ID (`XXX`) is the **Git blob object ID** (SHA-1 or SHA-256 depending on repo format) produced using:

```
git hash-object -w artifact.json
```

This makes artifacts:

* content-addressed
* deduplicated
* reproducible
* compatible with Git plumbing and GC rules

A human-friendly alias may be stored *inside* the artifact, but the **canonical public ID is the blob OID**.

### **4.2 Dedicated Ref Namespace**

Artifacts are stored under:

```
refs/gitsummary/main
```

This ref points to a commit whose tree contains:

```
/artifacts/<ART_OID>.json
/manifests/by-range/<A>..<B>
/index/latest
/schema/version
```

All updates are appended as new commits under `refs/gitsummary/main`.

### **4.3 Git Notes (Optional but Agreed Future Feature)**

Artifacts may also be referenced from the relevant closing commit or tag using notes:

```
refs/notes/gitsummary
```

The note contains the artifact’s blob OID.

### **4.4 GC Safety**

Artifacts and notes are protected from garbage collection because they are referenced via:

* a persistent ref (`refs/gitsummary/main`)
* optional notes (`refs/notes/gitsummary`)

---

## **5. Implementation Principles**

### **5.1 Pure Git, No Platform Dependencies**

* All collected data originates from Git itself:

  * diff
  * log
  * file changes
  * blame (optional, future)
  * tree structure
* No reliance on GitHub/GitLab APIs.

### **5.2 Python-Based CLI**

* Written in Python.
* Uses widely accepted, modern patterns.
* Will be packaged as a CLI tool.
* (CLI framework not set yet, but Python is confirmed.)

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
* Store artifacts using Git-native storage described above.
* Implement a basic `deployment` analyzer.

### **6.2 Long-Term Vision**

* Treat artifacts as “semantic twins” of each change.
* Enable analytics across project history.
* Provide powerful release summaries, maintainability signals, and operational insights.
* Potential integration as a native Git extension.
