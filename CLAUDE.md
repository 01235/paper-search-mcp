# paper_search_mcp

A MCP server for searching and downloading academic papers from multiple sources.

**Stack:** python · cli

## Environment

- Windows 10, PowerShell is the primary shell. Bash (Git Bash) is available but
  the two take different syntax — no `&&` chaining, no `2>/dev/null`, no
  here-strings in PowerShell 5.1.
- Paths contain spaces. Quote them.
- Python managed by `uv` - never bare `pip` or `venv`. CLI tools install with `uv tool install --editable .`
- **UTF-8 everywhere — set it up front, don't wait to hit the bug.** Windows
  defaults to the system codepage, not UTF-8, for console output and file
  I/O — the moment non-ASCII text (an em-dash, a curly quote, any real
  multilingual content) hits an unconfigured `print()` or `open()`, that's a
  `UnicodeEncodeError`/`UnicodeDecodeError`. Rust and Node default to UTF-8
  already; this is a Python-specific gotcha.
  - Reconfigure stdout/stderr once, at the top of `main()`, before anything
    prints: `sys.stdout.reconfigure(encoding="utf-8")` /
    `sys.stderr.reconfigure(encoding="utf-8")` — a no-op if already UTF-8.
  - Pass `encoding="utf-8"` to every `open()` / `read_text()` /
    `write_text()` call. Never rely on the platform default.

## Commands

```bash
uv sync
```

```bash
uv run pytest
```

```bash
uv run ruff check .
```

```bash
uv run ruff format .
```

```bash
uv run ty check paper_search_mcp/
```

```bash
uv run paper-search-mcp
```

```bash
uv run paper-search
```

The server has zero required configuration - every academic-source connector
works against free/public endpoints out of the box. Optional API keys (CORE,
Semantic Scholar, DOAJ, Unpaywall, Zenodo, etc.) improve rate limits or unblock
specific sources; see `docs/EXT-DEPS.md` and `.env.example`. IEEE Xplore and
ACM DL are opt-in skeletons that stay dormant (`NotImplementedError` on
download/read) until their API key env var is set.

## Directory structure

```
paper-search-mcp/
├── pyproject.toml, uv.lock          — package definition + lockfile (no src/ layout — package is at repo root)
├── CLAUDE.md                        — this file
├── paper_search_mcp/                — the installable package
│   ├── server.py                    — MCP server entry point (paper-search-mcp)
│   ├── cli.py                       — CLI entry point (paper-search)
│   ├── config.py                    — env var / .env loading (PAPER_SEARCH_MCP_* prefix)
│   ├── paper.py                     — shared Paper data model
│   ├── utils.py                     — shared helpers
│   └── academic_platforms/          — one module per source (arxiv, pubmed, crossref, ...)
├── tests/                           — pytest suite, one file per platform + server/fallback/entrypoint tests
└── docs/                            — ROADMAP.md, EXT-DEPS.md, superpowers/{plans,specs}
```

## Adding a new module

1. Create the file in the right place under the layout in Directory
   structure above.
2. Wire it into the package's public surface, if it has one — `__init__.py`
   exports, `mod.rs`, `index.ts`, whatever this language uses.
3. Add a one-line entry for it in the Directory structure block above.

## Working style

- **OOP by default.** Functional where the problem is genuinely a transformation
  pipeline — if you go functional in a module, note why here.
  <!-- TODO: record any deliberate paradigm departures -->
- **Never mutate inputs.** Return new objects.
- **Type annotations on every function signature.** The default ruff selection
  (`E`, `F`, `I`) only checks that annotations are *present*, not that they're
  *correct* — `uv run ty check paper_search_mcp/` (ty) is what actually checks the types.
- **Small, targeted edits and targeted test runs** while iterating; full suite
  before committing. Keeping the loop fast is what keeps the checks in use.
- **Files:** 200–400 lines comfortable, 800 the ceiling. Many small focused
  modules over few large ones, but don't split below the point where navigation
  costs more than it saves.
- **Handle errors explicitly.** No silently swallowed exceptions. Validate at
  system boundaries — anything from a user, a file, an API, or the network.
- **No hardcoded secrets.** Environment variables, and record them in
  `docs/EXT-DEPS.md`.
- No palette/design-token guidance applies here — this is an MCP server and
  CLI with no UI surface.

## Comment and docstring density

Comments and docstrings are good, **in moderation**. The calibration:

- a **module docstring** stating what the module is and the *why* a reader
  cannot recover from the code — a cost model, a non-obvious constraint
  between two subsystems, what gets written where;
- **function docstrings of one to three lines**, carrying the contract and
  any non-obvious constraint a caller couldn't derive from the signature;
- **no docstring at all** on a private helper whose name and signature
  already say what it does;
- **inline comments only where the code is genuinely surprising** — a line
  explaining why a count or a threshold works the way it does, not a line
  restating what the next line already says.

What to avoid: narrating decision history, arguing with alternatives that
weren't chosen, cross-referencing three other modules mid-paragraph,
restating the code in English, or explaining the same thing in both a
class docstring and its methods'.

**A long docstring is usually a design smell.** It's generally explaining
why something confusing is the way it is, and the right fix is to make it
not confusing. Design rationale belongs in `docs/` and the dated records
under `docs/superpowers/specs/`, not in the code — the code carries the
contract and the surprises, and nothing else.

This applies to new code and to code being edited for another reason. It is
not a licence to strip comments from files not otherwise being touched.

`paper_search_mcp/academic_platforms/arxiv.py` is the calibration — read it
before writing prose in this codebase, and match its density.

## Logging

- **The language's logging facility, not print/console output, for
  diagnostics.** A command's actual result — the thing piped to another tool
  or read as the answer — stays on stdout; progress, warnings, and what a
  routine is doing go through logging.
- **One central place configures logging**, called once per run at the
  entry point. Every other module just gets its own logger
  (`logging.getLogger(__name__)` in Python) and never attaches a handler —
  attaching handlers per-module means the same line gets logged twice the
  moment two modules touch the same logger hierarchy.
- **Log files are gitignored**, one directory per subsystem or run, so they
  stay searchable instead of one undifferentiated stream.
- **Before adding logging to code you're touching, check what it already
  logs.** New logging that duplicates or collides with an existing stream is
  worse than none — it looks like signal but is noise.

No central config exists yet — each `academic_platforms/*.py` module's
`logging.basicConfig(...)` call under its own `if __name__ == "__main__":`
self-test block is local to that script, not shared. If server-wide logging
configuration is added, it belongs once at the entry point (`server.py`'s
`main()` or `cli.py`'s `main()`), not per-module.

## Development modes

- **Features and bugfixes → TDD.** Test first, watch it fail, minimal
  implementation, watch it pass, refactor. 80% coverage floor.
- **Small fixes → just do it in a branch.** No plan document, no full-suite run,
  no whole-repo review. Judge by risk, not line count.
- Invoke `superpowers-extended-cc:systematic-debugging` the moment something
  behaves unexpectedly, before proposing a fix.

## Git

- **`main`, never `master`.**
- Commits are the user's own — **no `Co-Authored-By`, no "Generated with"
  footer, no Claude in the author field.**
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`,
  `chore:`, `perf:`.
- Push and open PRs only when asked, under the user's own `gh` login.

## Solo project workflow

An individual project, not a team repository — no separate human reviewer is
required before merging. Concretely:

- Feature work happens on a branch, merged back once tests pass and the
  change is verified. Merge it (or open then merge a PR) and delete the
  branch afterward — a PR is a convenience for history and diffing, not a
  required gate.
- Prefer merge commits when landing a branch over squashing — it keeps the
  per-task commit granularity.
- Still confirm before genuinely destructive or irreversible actions —
  discarding unmerged work, force-pushing, rewriting shared history.
  "Merge my finished, reviewed branch" is not one of those.

## Writing conventions

- **Documentation** (`docs/*.md`, `README.md`, other prose files): British/GB
  English spelling and grammar. Code fences and inline code (identifiers,
  flags, filenames) keep their literal spelling regardless.
- **Source code comments and docstrings:** American English — the software
  default.
- **Oxford comma** in comments, documentation, and markdown.
- **`README.md`** additionally avoids em-dashes — use `' - '`
  (space-hyphen-space) instead.

## Before calling work done

1. Full test suite passes — report real output, not a summary.
2. Lint, format, and type checks clean.
3. `docs/EXT-DEPS.md` updated if anything external was added.
4. `docs/ROADMAP.md` updated: delivered items crossed off, new ideas captured,
   deferred work recorded with its reason.
5. This file updated if any command or assumption above changed.

## Docs

`docs/` itself is living documentation — canonical for its subject, kept
current, and fixed in place when the code moves rather than re-explained
here. `docs/superpowers/` holds dated records instead: written during a
specific piece of work and left alone afterwards, so treat a claim in one as
true when it was written, and verify it against the code before relying on
it.

- `docs/ROADMAP.md` — future ideas, plans spanning multiple cycles, and a
  separate section for deliberately deferred work.
- `docs/EXT-DEPS.md` — everything external that must exist for this to run.
- `docs/superpowers/plans/` and `docs/superpowers/specs/` — dated planning
  and design records, one pair per piece of work.
