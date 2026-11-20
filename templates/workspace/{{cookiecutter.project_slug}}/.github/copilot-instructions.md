# Copilot instructions — {{ cookiecutter.project_name }}

This workspace also uses **PAIEP** (local, offline AI: Continue + {{ "Cline" if cookiecutter.agent_client == "cline" else "Roo Code" }} on a local model).

- Inline completions come from **{{ cookiecutter.inline_provider }}** only — one provider per workspace.
- Prefer PAIEP (local) for private code/data, offline work and knowledge-base/memory-grounded questions;
  Copilot for public-code problems that benefit from frontier models.
{%- if cookiecutter.copilot_mcp == "yes" %}
- PAIEP MCP tools are available to you (`rag_search`, `memory_recall`, `fs_*`, `git_*`, `agent_*`). Their
  results are sent to the cloud model: do not fetch sensitive files or memories through them.
{%- endif %}
- Never read or print secrets (`.env`, keys, tokens).
