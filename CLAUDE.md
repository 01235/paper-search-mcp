# paper-search-mcp

An MCP server that searches for academic papers in multiple sources and downloads them, with a command-line interface to the same sources.

**Stack:** python · cli

## Workflow

The imported file below describes the modes of work, how specs and code are reviewed, and which documents this repository keeps.

@~/Code/repository-conventions/workflow.md

## Environment

- The operating system is Windows 10. PowerShell is the primary shell. Bash (Git Bash) is also available and uses a different syntax. PowerShell 5.1 has no `&&` chaining, no `2>/dev/null`, and no Bash heredocs (`<<EOF`). Its here-strings are written `@'...'@`.
- Paths contain spaces. Quote them.
- uv manages Python, the virtual environment, and the dependencies: `uv add` adds a dependency and `uv run` runs a command in the project environment. A CLI tool is installed with `uv tool install --editable .`, so that edits to the source take effect without reinstalling.
- On Windows, Python reads and writes text in the system code page unless a call sets the encoding. Non-ASCII text then raises `UnicodeEncodeError` or `UnicodeDecodeError`. Set UTF-8 before the first input or output:
  - call `sys.stdout.reconfigure(encoding="utf-8")` and `sys.stderr.reconfigure(encoding="utf-8")` at the top of `main()` in `server.py` and in `cli.py`, before anything prints;
  - pass `encoding="utf-8"` to every `open()`, `read_text()`, and `write_text()` call.

  Rust and Node use UTF-8 by default.

## Commands

```bash
uv sync
```

```bash
uv run pytest
```

```bash
uv run ruff check
uv run ruff format
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

- `uv sync` installs the package, its dependencies, and the `dev` dependency group (pytest, ruff, and ty) into the project environment.
- Many test files call the live APIs of the sources, so `uv run pytest` needs network access. Most of these files skip a test when the API does not answer. `tests/test_pubmed.py` and `tests/test_server.py` do not skip, so they fail without network access. The four test files that `.github/workflows/publish.yml` runs need no network access.
- `tests/e2e_test.py` and `tests/functional_test.py` are scripts that call the live API of every source. Pytest does not collect them, because `pyproject.toml` sets `python_files = ["test_*.py"]`. Each one runs with `uv run python tests/<name>.py`.
- `uv run ty check` without a path also checks `tests/`, where ty reports two errors: `tests/test_sci_hub.py` passes a `MockResponse` where `SciHubFetcher._generate_filename` expects a `requests.Response`.
- `uv run paper-search-mcp` starts the MCP server on stdio. The server reads MCP messages from stdin, so in a terminal it waits for input.
- `uv run paper-search` runs the command-line interface, with the subcommands `search`, `download`, `read`, and `sources`.

<!-- Correct these commands once the project runs. Add anything a new session would otherwise have to work out, such as a required environment variable, a database that must be running, or a fixture that must be generated first. -->

## Directory structure

```
paper-search-mcp/
├── pyproject.toml, uv.lock  — package definition and lockfile
├── CLAUDE.md                — this file
├── paper_search_mcp/        — the installable package, at the repository root (no src/ directory)
│   ├── server.py            — MCP server and its tools; entry point `paper-search-mcp`
│   ├── cli.py               — command-line interface; entry point `paper-search`
│   ├── config.py            — reads the `PAPER_SEARCH_MCP_*` variables and the environment file
│   ├── paper.py             — `Paper`, the dataclass of a paper record
│   ├── utils.py             — `extract_doi`, which finds a DOI in a text or a URL
│   └── academic_platforms/  — one module per source; base.py defines `PaperSource`
├── tests/                   — pytest suite: a test file for most sources, and tests of
│                              the server, `download_with_fallback`, config.py, and the entry points
├── docs/                    — architecture.md, specs/, images/
├── claude-code/             — SKILL.md, a Claude Code skill that describes the `paper-search` command
├── .github/workflows/       — publish.yml, which publishes the package to PyPI on a version tag
├── Dockerfile               — container image that runs `paper-search-mcp`
├── smithery.yaml            — Smithery configuration of the server
└── .env.example             — the optional environment variables, to copy to ~/.config/paper-search-mcp/.env
```

<!-- One line per top-level module or directory. Update the block when a module is added or moved. A new session uses it to find a module without searching the file tree. -->

## Adding a module

1. Create the file where the directory structure above places it.
2. `paper_search_mcp/__init__.py` exports nothing, so the package has no public API to add the module to. A new source module is registered in `server.py` (a searcher instance, its name in `ALL_SOURCES`, a branch in `search_papers`, its tools, and its entry in `primary_downloaders` in `download_with_fallback`) and in `cli.py` (`_init_searchers` and `ALL_SOURCES`).
3. Add a line for the module to the directory structure above.
4. Add the module to the building block view in `docs/architecture.md`.

## Code

- Object-oriented code is the default. A module that transforms input data into output data, with no state worth naming, is written as functions. Its entry in the building block view states this.
- Functions return new objects and leave their inputs unchanged.
- In Python, every function signature in `paper_search_mcp/` has type annotations. `pyproject.toml` selects Ruff's `E`, `F`, and `I` rules, which do not check that annotations exist, and ty checks the types.
- A caught exception is handled, or re-raised with context. Data is validated where it enters the system: from a user, a file, an API, or the network.
- Secrets are read from environment variables. The deployment view in `docs/architecture.md` lists those variables.
- Each module hides one design decision, in Parnas's sense of information hiding: a change to that decision requires edits to that module only. A design decision is a choice such as a file format, a database schema, an algorithm, or the interface of an external service. The module docstring names the decision. New code goes into the module that hides the decision the code depends on. When no module hides that decision, propose a new module to the user. The length of a module is not a reason to split it.

## Tests

- Test a module through the functions that other modules call. Before writing a test, look for an existing test of the same behaviour, and extend that test instead of adding another.
- For a feature or a bug fix, write the test first and see it fail on its assertion: against the code with the bug, or against a stub that returns a wrong value. Then write the implementation and see the test pass. A failure caused by a missing function or module does not show that the assertion can fail.
- While working, run the tests for the code being changed. Run the full suite once before merging a branch, and again only if a file has changed since that run.

## Logging

- Code reports progress, warnings, and errors through a module logger, `logging.getLogger(__name__)`, and not with `print()`. The MCP server writes its MCP messages to stdout, and the CLI writes each command's result to stdout, so text printed to stdout is mixed into them. Section 8 of `docs/architecture.md` describes the logging configuration of each process.
- Before adding a log call, read what the code already logs. A message that repeats an existing message, or reports the same event in other words, adds output that a reader takes for new information.
- If a logging configuration is added for the package, it is added at the top of `main()` in `server.py` and in `cli.py`, once in each, and other modules only create their logger. In the server, `FastMCP(...)` calls `logging.basicConfig` when `server.py` is imported, so a later `basicConfig` call has an effect only with `force=True`.

## Git

- The default branch is `main`.
- Commits use the user's git identity as the author. Do not add a `Co-Authored-By` trailer to commits or a "Generated with" line to PR descriptions.
- Commit messages use the conventional commit prefixes `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, and `perf:`.
- Pushes and PRs use the user's own `gh` login.

## Before calling work done

1. The tests pass, run as the Tests section describes. Report the output as printed.
2. Lint, format, and type checks report no issues.
3. `docs/architecture.md` describes the system as changed.
4. This file is updated if a command or an assumption in it has changed.

## Comment and docstring reference

`paper_search_mcp/academic_platforms/arxiv.py` is the reference for comment and docstring density.
