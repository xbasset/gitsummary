# Install & Update

Short steps for repo users (new or upgrading).

## Fresh Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m gitsummary --help
```

## Update Existing Install

```bash
git pull
source .venv/bin/activate
pip install -r requirements.txt --upgrade
python -m gitsummary --help
```

## OpenAI LLM Provider

- Require `openai>=1.0.0` (in `requirements.txt`).
- Set API key: `export OPENAI_API_KEY=...`.
- If a separate tool pins `openai<2`, use a dedicated venv for gitsummary.

## Postgres Backend (Optional)

Select backend:

```bash
export GITSUMMARY_STORAGE_BACKEND=postgres
export GITSUMMARY_POSTGRES_DSN="user=... password=... dbname=... host=... port=5432"
```

Project identity (optional overrides):

- `GITSUMMARY_PROJECT_ID` (default: inferred as `owner/repo` when repo path includes `.../repos/<owner>/<repo>`)
- `GITSUMMARY_PROJECT_SLUG`
- `GITSUMMARY_PROJECT_NAME`
- `GITSUMMARY_PROJECT_PROVIDER` (default: `github` if inferred, else `local`)
- `GITSUMMARY_PROJECT_URL` (default: `https://github.com/<owner>/<repo>` or `local://<repo>`)

Artifacts are stored in `public.artifacts` with:
- `content_type = gitsummary.commit_artifact`
- `source_ref = <commit sha>`
- structured columns (`category`, `impact_scope`, `is_breaking`, `behavior_before`, `behavior_after`, `technical_highlights`, `analysis_mode`, `analysis_provider`, `analysis_model`, `analysis_prompt_version`, `analysis_timestamp`, `analysis_duration_ms`, `analysis_fallback_reason`, `analysis_token_usage_*`, `analysis_input_metrics_*`, `analysis_qualitative_*`, `tool_version`)
