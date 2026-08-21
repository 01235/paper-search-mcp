# Roadmap — paper_search_mcp

## Ideas

Things mentioned in passing that aren't being built yet. No commitment implied;
this is a parking place so good ideas don't evaporate between sessions.

<!-- - Idea, one line, with enough context to reconstruct the thought later -->

## In flight

Plans that grew beyond a single work cycle. Each should link to its spec or plan
under `docs/superpowers/`.

- [ ] Citation graph & paper relation context feature — see README.md TODO
      ("Development Tasks")

## Delivered

Most of the platform integrations tracked in this project's README TODO section
are already implemented and marked `[√]` there — arXiv, PubMed, bioRxiv,
medRxiv, Google Scholar, IACR, Semantic Scholar, Crossref, PMC, CORE, Europe
PMC, OpenAlex, OpenAIRE, dblp, CiteSeerX, DOAJ, BASE, Zenodo, HAL, SSRN,
Unpaywall, and Sci-Hub (with warning/enablement docs). See README.md's TODO
section for the authoritative, checked-off list rather than duplicating it
here.

## Deferred

Work consciously **not** being done, and why. This section is the important one:
it's the difference between a decision and an oversight. Anything skipped during
a review or dropped from a branch belongs here with its reason, so that six
months later the answer to "why doesn't this handle X?" is written down.

- **IEEE Xplore and ACM Digital Library** — search is registered but
  download/read raise `NotImplementedError`. Deferred because both require a
  paid/institutional API key and the project is free-first by design; kept as
  opt-in skeletons activated only when `PAPER_SEARCH_MCP_IEEE_API_KEY` /
  `PAPER_SEARCH_MCP_ACM_API_KEY` are set. Revisit if a contributor with API
  access wants to finish the connectors.
- **ResearchGate, JSTOR, ScienceDirect, Springer Link, Web of Science, Scopus**
  — deferred, not started. These are paid/restricted sources outside the
  project's free-first roadmap (see README.md "Free-First" principle). Revisit
  only if a specific need arises, since none are open-access-first sources.
