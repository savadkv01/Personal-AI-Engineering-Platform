# AGENTS.md — {{ cookiecutter.project_name }}

Conventions for any AI coding agent in this repository (Continue, Cline, Roo Code, Copilot, PAIEP agents).

- **Backend:** PAIEP shared local backend (`{{ cookiecutter.gateway_url }}`), scope `{{ cookiecutter.memory_scope }}`.
- **Changes:** small, reviewable, reversible; show diffs before writing; the human approves.
- **Context:** search the PAIEP knowledge base / memory before guessing; cite sources.
- **Secrets:** never read, print or commit `.env`, keys or tokens.
- **Git:** agents may create local branches; committing and pushing are human actions.
