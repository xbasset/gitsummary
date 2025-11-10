# **gitsummary — Open Questions (v0.1)**

This document captures **all unresolved questions and options** needed to complete the design.
Each question includes:

* **Context** — why it matters
* **Decision Needed** — what must be chosen

No assumptions or answers are included.

---

# **1. Git Range Semantics**

### **1.1 Range semantics (critical)**

**Context:**
`collect --tag A B` currently implies “analyze commits between A and B”.
Git supports multiple interpretations:

* `A..B` = commits reachable from B not reachable from A
* `A...B` = symmetric difference
* merge-base-based ranges
* supporting non-tag refs (`commitA commitB`, branches, etc.)

**Decision Needed:**
What exact semantic should `gitsummary collect A B` use for commit selection?

---

### **1.2 Non-tag references**

**Context:**
We currently only support tags in examples. Users may need ranges like:

* `gitsummary collect A..B`
* `--rev A B`
* `--branch main --merged feature/...`

**Decision Needed:**
Should we support non-tag refs at launch? If yes, which syntaxes?

---

### **1.3 Path filtering**

**Context:**
Monorepos often need per-component artifacts.

**Decision Needed:**
Should `collect` support a `--path` or `--filter-path` option?

---

# **2. Artifact Identity & Determinism**

### **2.1 Human-friendly alias**

**Context:**
Canonical ID = blob OID, but a human alias (e.g., `chg_0_<timestamp>_<B8>_<range8>`) could help.

**Decision Needed:**
What exact alias format should be stored inside the artifact?

---

### **2.2 Deterministic artifacts**

**Context:**
Reproducibility depends on deterministic ordering and timestamps.

**Decision Needed:**
Should artifacts be **bit-for-bit identical** when generated twice under same repo state + tool version?

---

### **2.3 Schema versioning policy**

**Context:**
We have a schema version field but no versioning rules.

**Decision Needed:**
How do we increment schema versions (major/minor/patch) and track backward compatibility?

---

### **2.4 Storage backend beyond Git**

**Context:**
We will use Git-native storage, but some users may want alternative stores (local folder / S3 / GCS).

**Decision Needed:**
Should a pluggable storage backend be supported (even later), or is Git the only backend?

---

# **3. Git-Native Storage Details**

### **3.1 Ref namespace names**

**Context:**
We proposed:

* `refs/gitsummary/main`
* `refs/notes/gitsummary`

**Decision Needed:**
Are these the final names, or should they be configurable/shorter?

---

### **3.2 Analysis persistence**

**Context:**
Should analysis outputs be stored in Git by default?

Options:

1. Always store analyses in:

   ```
   /analyses/<artifact-oid>/<facet>.json
   ```
2. Only store if `--save` is specified.
3. Never store; output only to stdout.

**Decision Needed:**
What should be the default behavior?

---

### **3.3 Push behavior**

**Context:**
Artifacts stored in refs are not automatically pushed.

**Decision Needed:**
Should `collect` or `analyze` attempt to push `refs/gitsummary/*` and `refs/notes/gitsummary` by default, offer a flag, or stay entirely manual?

---

### **3.4 Notes attachment**

**Context:**
We plan to attach a git note containing artifact OID to the closing commit or tag.

**Decision Needed:**
Should attaching notes be default behavior, optional, or opt-in?

---

# **4. Collector Behavior**

### **4.1 Diff size limits**

**Context:**
Large diffs (vendor files, lockfiles, generated code) can explode artifact size + LLM cost.

**Decision Needed:**
Should we impose a default `max diff bytes` threshold? Should behavior be “truncate + summarize”?

---

### **4.2 AST parsing (tree-sitter)**

**Context:**
AST parsing enables better semantic analysis, but tree-sitter installation can be heavy.

**Decision Needed:**
Should AST parsing be:

* on by default,
* optional if available,
* or completely avoided in v0.1?

---

### **4.3 Ignoring specific directories**

**Context:**
Changes in `vendor/`, `dist/`, `target/`, generated files may not be relevant.

**Decision Needed:**
Which default ignore patterns should be baked into the collector?

---

### **4.4 Blame data**

**Context:**
Blame per-hunk can help determine responsible modules & historical ownership.

**Decision Needed:**
Should the collector capture blame information (optional because expensive)?

---

### **4.5 Conventional commits**

**Context:**
Commit message convention can seed intention extraction.

**Decision Needed:**
Should collector parse conventional commits if present?

---

# **5. Analyzer Architecture**

### **5.1 Analyzer plugin system**

**Context:**
Facets (deployment, maintainability, etc.) may become plugins.

**Decision Needed:**
Should analyzers be:

* built-ins,
* plugins via Python entry points,
* or both?

---

### **5.2 Multiple facet output**

**Context:**
Users may want:

```
gitsummary analyze ART --target deployment,impact
```

**Decision Needed:**
Should multi-facet analysis be supported in one command?

---

### **5.3 Evidence linking**

**Context:**
Analyses should reference evidence from the artifact.

**Decision Needed:**
What format should evidence links use (path, line range, commit hash, excerpt)?

---

### **5.4 Analyzer output format**

**Context:**
We will support structured JSON output, but users may want pretty Markdown summaries.

**Decision Needed:**
What should be the default output for analyzers: JSON or Markdown?

---

# **6. Deployment Facet Questions**

### **6.1 Monitoring stack targeting**

**Context:**
Different systems recognize logs differently (ELK, Loki, Datadog, OpenTelemetry).

**Decision Needed:**
Which monitoring systems should the deployment facet tailor recommendations for first?

---

### **6.2 Detection of runtime behavior changes**

**Context:**
Logs & errors are first-level signals; deeper detection (like metrics emission) could be added.

**Decision Needed:**
Should the deployment facet detect metric patterns (e.g., Prometheus counters, StatsD calls)?

---

### **6.3 CI/CD changes**

**Context:**
Deployment workflows often change via GitHub Actions, GitLab CI, etc.

**Decision Needed:**
Should changes to `.github/workflows`, `.gitlab-ci.yml`, etc., be interpreted as deployment-related?

---

### **6.4 Severity classification**

**Context:**
Deployment-impacting changes could be tagged by severity.

**Decision Needed:**
Should we implement:

* none,
* low/medium/high,
* or detailed categories (e.g., observability, infra, config, logs, errors)?

---

# **7. Interactive Analysis**

### **7.1 Annotation storage**

**Context:**
Interactive Q&A could produce clarifications stored for future runs.

**Decision Needed:**
Where should annotations be stored:

* inside Git under `refs/gitsummary/main`?
* in a separate local store?
* not stored by default?

---

### **7.2 Session management**

**Context:**
Interactive sessions may need IDs linked to artifacts.

**Decision Needed:**
Should sessions have unique IDs persisted for auditability?

---

# **8. CLI Design**

### **8.1 CLI framework**

**Context:**
Python options include Typer, Click, Argparse.

**Decision Needed:**
Which framework should be used?

---

### **8.2 Output modes**

**Context:**
Users may want:

* human-readable
* machine-readable (`--json`)
* quiet / verbose modes

**Decision Needed:**
What should `collect` and `analyze` default to?

---

### **8.3 Config management**

**Context:**
Parameters such as model, ignore paths, and diff limits need configuration.

**Decision Needed:**
Should config be handled via:

* `pyproject.toml`,
* `~/.config/gitsummary/config.toml`,
* CLI flags only,
* or a combination?

---

# **9. LLM Usage**

### **9.1 Default model selection**

**Context:**
We will use OpenAI Agent SDK but need a model baseline.

**Decision Needed:**
Which model should be the default (GPT-5? GPT-4o?) and should users be able to override it via config?

---

### **9.2 Token budget**

**Context:**
Artifacts might be large; LLM cost must be controllable.

**Decision Needed:**
Should there be default and max token budgets per analysis run?

---

### **9.3 Offline mode**

**Context:**
Some environments require no external calls.

**Decision Needed:**
Should `analyze` work in an offline heuristic-only mode?

---

### **9.4 Caching**

**Context:**
LLM results can be cached using a hash of evidence + prompt version.

**Decision Needed:**
Should caching be implemented, and if yes, where should the cache live (Git, local disk, etc.)?

---

# **10. Packaging & Distribution**

### **10.1 Installation**

**Context:**
We want an easy-to-install CLI.

**Decision Needed:**
Should we target:

* `pipx install gitsummary`
* `pip install gitsummary`
* downloadable binary via PyInstaller
* or multiple options?

---

### **10.2 License**

**Context:**
License type affects contributions and redistribution.

**Decision Needed:**
Which license (e.g., Apache-2.0, MIT, proprietary)?

---

### **10.3 Documentation depth**

**Context:**
Initial docs could be minimal or more structured.

**Decision Needed:**
Should we start with:

* single README,
* README + docs/ directory,
* or a small mkdocs site?
