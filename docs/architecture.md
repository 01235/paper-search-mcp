# paper-search-mcp architecture

<!--
This document describes the current system. Write it in the present tense, following writing-rules.md.
State each constraint as a fact with its reason. Name the test that checks it, if there is one.
Do not record plans or history. Plans are in the specs in docs/specs/. History is in git.
Define project terms only in section 12.
The section structure follows arc42 (https://arc42.org). Leave out a section that has nothing to describe. Keep the numbers of the other sections.
-->

## 1. Introduction and goals

### 1.1 What the system does

`paper-search-mcp` is an MCP server that searches for academic papers in multiple sources, such as arXiv, PubMed, and Crossref, and downloads their PDFs. Its tools do the following:

- A search tool for each source returns the papers that match a query. `search_papers` searches several sources at once and removes duplicate records.
- Download tools save a paper's PDF in a directory.
- Read tools download a paper's PDF and return its text.
- `download_with_fallback` looks for a paper's PDF in open-access repositories, in Unpaywall, and in Sci-Hub when the paper's own source returns no PDF.

The `paper-search` command searches, downloads, and reads papers from the same sources in a terminal.

### 1.2 Design priorities

- Running without configuration: the server starts without environment variables or a configuration file. `config.get_env` returns an empty string for a variable that is not set, and each searcher instance then sends its requests without a key, at the rate limit that its source sets for such requests. Unpaywall is the exception: it needs a contact email address, and without one the Unpaywall source returns no results. Section 7 lists the variables.
- No services to run: the server uses no database, no queue, and no other service that must be kept running. A tool sends requests to the API of its source when the client calls the tool.

### 1.3 Users

An MCP client starts the server and calls its tools. A person, or an agent with a shell, runs the `paper-search` command. `claude-code/SKILL.md` describes the command to Claude Code. One developer maintains the repository.

## 2. Constraints

- The stdio transport of MCP (MCP specification, section "Transports"): the client starts the server as a subprocess, writes MCP messages to the server's stdin, and reads MCP messages from its stdout. The specification requires that the server write nothing to stdout that is not an MCP message.
- Unpaywall's API requires a contact email address in each request (Unpaywall API documentation).
- The API of each source sets its own rate limits. Several sources give a higher limit to requests that include a key (the API documentation of each source; section 7 lists the keys).

## 3. Context and scope

The server exchanges data with an MCP client, with the web APIs of the sources, and with the local file system.

- MCP client: the client sends tool calls to the server's stdin and receives the results from its stdout, as MCP messages. A search tool returns a list of paper records, each the dictionary that `Paper.to_dict` returns. `search_papers` returns a dictionary with the records, the number of records from each source, and the error message of each source that failed. The download and read tools return a string: a file path, a paper's text, or a message.
- Source APIs: when a tool is called, the searcher instance of the source sends HTTP requests to the source's API and parses the response. The response is JSON, XML, an Atom feed, or an HTML page, depending on the source. PDF files are downloaded over HTTP.
- File system: the download and read tools write PDF files into the directory that their `save_path` argument names. `config.py` reads an environment file (section 8).

## 5. Building block view

### 5.1 Level 1: packages

- `paper_search_mcp` is the installable package. It is at the repository root, without a `src/` directory. It contains the entry point of the server (`server.py`), the entry point of the command-line interface (`cli.py`), and the modules that both use. `paper_search_mcp/__init__.py` calls `config.load_env_file()` and exports nothing.
- `paper_search_mcp.academic_platforms` contains one module per source. Each source module defines a searcher class derived from `PaperSource`.

### 5.2 Level 2: modules

`server.py` creates the MCP server with `FastMCP` from the MCP Python SDK, creates one searcher instance per source when it is imported, and defines the MCP tools, which call methods of these instances. It is written as functions that use the module-level instances. Its interface is the set of tools and `main()`, the entry point of the `paper-search-mcp` command, which runs the server on stdio. The search tools run the blocking searcher methods in worker threads with `asyncio.to_thread`. Most download and read tools call the searcher methods directly, in the event loop. `search_papers` runs the searches of the selected sources concurrently and removes duplicate records: it compares the DOIs of two records, or their titles and authors when a record has no DOI. `server.py` depends on `config` and on the source modules.

`cli.py` defines the `paper-search` command with the subcommands `search`, `download`, `read`, and `sources`. It creates the searcher instances when a command runs (`_init_searchers`) and writes the result to stdout: JSON for `search`, `download`, and `sources`, and the extracted text for `read`. It contains its own versions of the source list (`ALL_SOURCES`), of the parsing of the `sources` argument, and of the removal of duplicate records in `server.py`. It is written as functions.

`config.py` reads the settings from environment variables and from an environment file (section 8). Its interface is `load_env_file()` and `get_env(name)`. It is written as functions.

`paper.py` defines `Paper`, the dataclass of a paper record. The `search` method of every searcher class returns a list of `Paper` objects. `Paper.to_dict()` converts a record into the dictionary that the tools return: it joins list fields with "; " and writes dates in ISO 8601 format.

`utils.py` defines `extract_doi(text)`, which returns the first DOI in a text or a URL, or an empty string. The source modules call it. It is written as functions.

`academic_platforms/` contains these modules:

- `base.py` defines `PaperSource`, the abstract base class of the searcher classes. `search` is abstract. `download_pdf` and `read_paper` raise `NotImplementedError` unless a subclass overrides them. For a source that offers no PDFs, these methods raise `NotImplementedError` or return a message.
- Each source module defines the searcher class of its source, such as `ArxivSearcher` in `arxiv.py`. `oaipmh.py` defines `OAIPMHSearcher`, a base class for repositories that offer OAI-PMH, which `BASESearcher` in `base_search.py` extends. `chemrxiv.py` defines `ChemRxivSearcher`, which neither `server.py` nor `cli.py` imports.
- `unpaywall.py` defines `UnpaywallResolver`, which finds the URL of an open-access PDF for a DOI, and `UnpaywallSearcher`, which returns the Unpaywall record of the DOI in a query.
- `sci_hub.py` defines `SciHubFetcher`, which downloads a PDF from a Sci-Hub mirror. `download_scihub` and `download_with_fallback` in `server.py` use it.
- `ieee.py` and `acm.py` define `IEEESearcher` and `ACMSearcher`. `server.py` and `cli.py` import them only when the API key of the source is set (section 7). Their methods have no implementation (section 11).

## 7. Deployment view

An MCP client starts the server as a Python process, on the client's machine or in the container image that `Dockerfile` builds. This section lists what must be installed besides the Python packages, which `uv.lock` pins and `uv sync` installs.

### Toolchain

| Tool | Version | How to install |
|---|---|---|
| uv | latest | Astral's standalone installer, in PowerShell: `irm https://astral.sh/uv/install.ps1 \| iex`. Update it with `uv self update`. Documentation: https://docs.astral.sh/uv/ |
| Python | see `requires-python` in pyproject.toml | `uv python install` |

### Services and system packages

The project needs no services and no system packages. The server sends its requests to the public APIs of the sources (section 3).

### Environment variables

Every variable is optional. Most of them raise the rate limit of a source; the table states the effect of each. `config.py` reads the variables from the environment and from the file `~/.config/paper-search-mcp/.env`, which is made by copying `.env.example`. A variable that is set in the environment, for example with a shell export, takes precedence over the same variable in the file. Section 8 describes the order in which `config.py` looks up a name.

| Variable | Source | Effect | Where to get a value |
|---|---|---|---|
| `PAPER_SEARCH_MCP_CORE_API_KEY` | CORE | `CORESearcher` sends the key as a bearer token, and CORE raises the rate limit. | A free key from core.ac.uk/services/api |
| `PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar | `SemanticSearcher` sends the key in the `x-api-key` header, and Semantic Scholar raises the rate limit. | A free key from semanticscholar.org/product/api |
| `PAPER_SEARCH_MCP_GOOGLE_SCHOLAR_PROXY_URL` | Google Scholar | `GoogleScholarSearcher` sends its requests through this proxy, to avoid Google Scholar's bot detection. | The URL of your own HTTP or HTTPS proxy |
| `PAPER_SEARCH_MCP_DOAJ_API_KEY` | DOAJ | `DOAJSearcher` sends the key in the `X-API-Key` header, and DOAJ raises the hourly rate limit. | A free key from doaj.org/apply-for-api-key |
| `PAPER_SEARCH_MCP_UNPAYWALL_EMAIL` | Unpaywall | Unpaywall's API terms require a contact email address. Without it, `search_unpaywall` returns an empty list and `download_with_fallback` skips Unpaywall. | Any email address that you control |
| `PAPER_SEARCH_MCP_ZENODO_ACCESS_TOKEN` | Zenodo | `ZenodoSearcher` sends the token as a bearer token, and Zenodo raises the rate limit. | A free token from zenodo.org |
| `PAPER_SEARCH_MCP_OPENAIRE_API_KEY` | OpenAIRE | `OpenAiresearcher` sends the key as a bearer token, and OpenAIRE raises the rate limit. | A free key from openaire.eu |
| `PAPER_SEARCH_MCP_CITESEERX_API_KEY` | CiteSeerX | `CiteSeerXSearcher` sends the key as a bearer token, and CiteSeerX raises the rate limit. | The CiteSeerX documentation |
| `PAPER_SEARCH_MCP_IEEE_API_KEY` | IEEE Xplore | `server.py` registers `search_ieee`, `download_ieee`, and `read_ieee_paper` and adds `ieee` to `ALL_SOURCES`, and `cli.py` adds the `ieee` source. Each of these tools raises `NotImplementedError` (section 11). | A free key from developer.ieee.org |
| `PAPER_SEARCH_MCP_ACM_API_KEY` | ACM Digital Library | `server.py` registers `search_acm`, `download_acm`, and `read_acm_paper` and adds `acm` to `ALL_SOURCES`, and `cli.py` adds the `acm` source. Each of these tools raises `NotImplementedError` (section 11). | libraries.acm.org/digital-library/acm-open |
| `PAPER_SEARCH_MCP_ENV_FILE` | none | `config.py` reads the environment file at this path in place of `~/.config/paper-search-mcp/.env`. | The path of a file in the format of `.env.example` |

### Development tools

Development tools are needed to develop the project and not to run it.

| Tool | Install | Purpose |
|---|---|---|
| pre-commit | `uv tool install pre-commit`, then `pre-commit install` | Runs the hooks in `.pre-commit-config.yaml` before each commit: ruff with `--fix`, the ruff formatter, fixers for trailing whitespace and a missing final newline, and checks for YAML and TOML syntax, large files, merge conflict markers, and private keys. The hooks use the ruff version that `.pre-commit-config.yaml` pins, which can differ from the version in `uv.lock`. The second command installs the git hook; the configuration file alone has no effect. |
| pytest, ruff, ty | `uv sync` installs them from the `dev` dependency group | Tests, linting and formatting, and type checking. ty is run by hand, with `uv run ty check paper_search_mcp/`, and no pre-commit hook runs it: ty is in beta and has no automatic fixes, so a hook would block a commit on errors that the commit did not cause. |

### Setup

```bash
uv sync
```

`uv tool install --editable .` installs the `paper-search-mcp` and `paper-search` commands for use outside the project environment. To set the optional variables, copy `.env.example` to `~/.config/paper-search-mcp/.env` and fill in the values.

### Distribution

`.github/workflows/publish.yml` runs when a tag that matches `v*.*.*` is pushed. It runs the four test files that need no network access, builds the wheel, checks the wheel's two entry points, and publishes the package to PyPI. `Dockerfile` builds an image that installs the wheel and runs `paper-search-mcp`. `smithery.yaml` configures how Smithery starts the server over stdio and which environment variables Smithery passes to it.

## 8. Cross-cutting concepts

### Configuration

Every setting is an environment variable whose name is `PAPER_SEARCH_MCP_` followed by a setting name, such as `CORE_API_KEY`. `paper_search_mcp/__init__.py` calls `config.load_env_file()`, so the environment file is read when the package is imported. `load_env_file()` reads the file that `PAPER_SEARCH_MCP_ENV_FILE` names, or else `~/.config/paper-search-mcp/.env`, and sets each variable in the file that the environment does not already define. `get_env(name)` returns the value of `PAPER_SEARCH_MCP_<name>` if that variable is set, and otherwise the value of the unprefixed `<name>`, such as `CORE_API_KEY`, so that a configuration that uses the unprefixed names also works. When the prefixed variable is set to an empty string, `get_env` returns the empty string and does not read the unprefixed variable. `tests/test_config_env.py` checks this order.

### Logging and standard output

Modules that log create a module logger with `logging.getLogger(__name__)` and attach no handler. A logger passes each record to its own handlers and to the handlers of its parent loggers, so a handler attached in a module, in addition to a handler higher in the logger hierarchy, would write each record twice.

The package's code configures no logging. In the MCP server, `FastMCP(...)` in `server.py` calls `logging.basicConfig` when `server.py` is imported. The root logger then has level INFO and a handler that writes to stderr. In the CLI, nothing configures logging: Python's last-resort handler writes each record of level WARNING or above to stderr as its message text alone, and records below WARNING are not written.

`base_search.py`, `chemrxiv.py`, `doaj.py`, and `oaipmh.py` call `logging.basicConfig(level=logging.INFO)` in their `if __name__ == "__main__":` blocks. These blocks run only when the module is run as a script, so they do not configure logging for the server or the CLI.

Each process writes its results to stdout: the server writes MCP messages, and each CLI command prints JSON or the extracted text. Diagnostics go to stderr through logging. Section 11 lists the code that prints diagnostics to stdout instead.

## 10. Quality requirements

- Installation from section 7: a person on a clean machine can install and run the project by following section 7 alone. Check: set the project up on a machine that does not have it. A known setup obstacle that section 7 does not mention is a missing entry in section 7.

## 11. Risks and technical debt

- `IEEESearcher` and `ACMSearcher` have no implementation: `search`, `download_pdf`, and `read_paper` raise `NotImplementedError`, also when the API key is set. With a key set, the server registers the tools of the source, each call of these tools returns an error, and `search_papers` reports an error for the source. `test_search_raises_not_implemented_even_with_key` in `tests/test_ieee.py` and in `tests/test_acm.py` checks this for `search`.
- The read tools for arXiv, bioRxiv, medRxiv, IACR, and Semantic Scholar in `server.py`, and methods of `ArxivSearcher`, `BioRxivSearcher`, and `MedRxivSearcher`, print error and retry messages with `print()`. In the MCP server, these lines go to stdout, the stream from which the client reads MCP messages (section 2). In the CLI, they go to stdout before the JSON result.
- `cli.py` prints the text that `read` extracts with `print()`, and its `main()` does not set the encoding of stdout. On Windows, when stdout is a pipe or a file, Python encodes this text in the system code page, so a character outside the code page raises `UnicodeEncodeError`. The JSON that the other commands print contains only ASCII characters, because `json.dumps` escapes the others.

## 12. Glossary

| Term | Definition | Source |
|---|---|---|
| source | A service that the package searches for papers or downloads PDFs from, such as arXiv, PubMed, or Crossref. `ALL_SOURCES` in `server.py` lists the names that the tools accept. | project term, from the previous documentation, not yet approved |
