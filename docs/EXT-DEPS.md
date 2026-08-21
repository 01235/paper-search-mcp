# External dependencies — paper_search_mcp

Everything that has to exist outside this repository for it to run. Packages
resolved by `uv`/`cargo`/`npm` do **not** belong here — the lockfile covers
those. This file is for the things a lockfile can't install.

The test for whether this file is complete: could someone on a clean machine get
the project running from this file alone? If they'd hit a wall you already know
about, it's missing an entry.

## Toolchain

| Thing | Version | How to get it |
|---|---|---|
| uv | latest | https://docs.astral.sh/uv/ - `winget install astral-sh.uv` |
| Python | see `requires-python` in pyproject.toml | `uv python install` |

## Services

None. No database, no queue, nothing that has to be kept running - this is a
stateless MCP server that calls out to public paper APIs on demand.

## Extensions and system packages

_None yet._

## Environment variables and secrets

All optional - the server works with zero configuration, using only free/public
endpoints. Setting these improves rate limits, coverage, or unblocks a specific
source. Configure in `~/.config/paper-search-mcp/.env` (copy `.env.example`) or
as shell exports; all follow the `PAPER_SEARCH_MCP_<NAME>` prefix (legacy
unprefixed names like `CORE_API_KEY` still work for backward compatibility).

| Variable | Purpose | Source |
|---|---|---|
| `PAPER_SEARCH_MCP_CORE_API_KEY` | CORE search/download, raises rate limits | Free at core.ac.uk/services/api |
| `PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar, raises rate limits | Free at semanticscholar.org/product/api |
| `PAPER_SEARCH_MCP_GOOGLE_SCHOLAR_PROXY_URL` | Google Scholar, bypasses bot-detection | Your own HTTP/HTTPS proxy |
| `PAPER_SEARCH_MCP_DOAJ_API_KEY` | DOAJ, raises hourly rate limit | Free at doaj.org/apply-for-api-key |
| `PAPER_SEARCH_MCP_UNPAYWALL_EMAIL` | Unpaywall (required by their API terms) | Any email address you control |
| `PAPER_SEARCH_MCP_ZENODO_ACCESS_TOKEN` | Zenodo, raises rate limits | Free at zenodo.org |
| `PAPER_SEARCH_MCP_OPENAIRE_API_KEY` | OpenAIRE, raises rate limits | Free at openaire.eu |
| `PAPER_SEARCH_MCP_CITESEERX_API_KEY` | CiteSeerX, raises rate limits | See CiteSeerX docs |
| `PAPER_SEARCH_MCP_IEEE_API_KEY` | IEEE Xplore - **required to activate**, otherwise skeleton/`NotImplementedError` | Free at developer.ieee.org |
| `PAPER_SEARCH_MCP_ACM_API_KEY` | ACM DL - **required to activate**, otherwise skeleton/`NotImplementedError` | See libraries.acm.org/digital-library/acm-open |

See `README.md`'s "Credential & API Key Requirements" section for the full,
current list and troubleshooting notes - this table summarizes it but the
README is canonical.

## Dev-only tools

<!-- Things needed to develop but not to run.

| Tool | Install | Purpose |
|---|---|---|
| pre-commit | uv tool install pre-commit; pre-commit install | Git hooks. The second command is what writes the hook — the config alone does nothing |
| mutmut | uv tool install mutmut | Mutation testing during periodic review |
| crosshair-tool | uv add --dev crosshair-tool | Symbolic-execution contract verification for risk-bearing pure functions |
| hypothesis | uv add --dev hypothesis | Property-based and stateful testing |
-->

| Tool | Install | Purpose |
|---|---|---|
| pre-commit | `uv tool install pre-commit` then `pre-commit install` | Git hooks. The second command writes the hook - the config alone does nothing |
| ruff | already a dev dependency | Lint and format - `uv run ruff check .` / `uv run ruff format .` |
| pytest | already a dev dependency | Test runner - `uv run pytest` |
| ty | already a dev dependency | Astral's type checker - `uv run ty check paper_search_mcp/`; run it yourself, not pre-commit (beta tool, no auto-fix - see references/dev-workflow.md) |
