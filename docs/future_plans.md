# Future Plans & Extended Scope

This document captures user groups, use cases, and features that are part of the long-term vision for `gitsummary` but are **out of scope for the initial v0.1 Release Manager focus**.

## Future User Personas

### 1. The Developer (Onboarding & Context)
**Problem:** "I just joined this team/project. How did the auth system evolve over the last 3 months? Why was this architectural decision made?"
**Future Solution:**
- Interactive queries against the artifact history (e.g., `gitsummary ask "explain the refactor in auth module"`).
- IDE integration to show "Intent" and "Impact" alongside `git blame`.

### 2. The SRE / Ops Engineer
**Problem:** "We are deploying to production. What config, env vars, or logging patterns changed in this release that I need to know about?"
**Future Solution:**
- Dedicated "Deployment" facet in analysis.
- Automatic generation of deployment runbooks or "watch lists" for monitoring based on diffs.

### 3. The AI Agent
**Problem:** Autonomous agents need to understand the codebase's history to make safe changes, but raw git logs are too noisy and unstructured.
**Future Solution:**
- `gitsummary` acts as the "Memory" or "Hippocampus" for other agents.
- A standardized API for agents to query historical context before proposing changes.

## Advanced Features

### Interactive Disambiguation (Human-in-the-Loop)
- **Concept:** When the LLM cannot confidently infer intent (e.g., ambiguous refactor vs feature), it asks the user for clarification.
- **Mechanism:** A `gitsummary review` command that cycles through low-confidence artifacts and prompts the human author.

### Cross-Repo Summaries
- Aggregating artifacts across microservices to generate a "System-Wide" changelog.

### Deep Semantic Search
- Vector embeddings of the artifacts to allow semantic search over the history of the project (e.g., "When did we stop supporting Python 3.8?").

