# ADR 0012: Local Chat UI and Tool Bridge
- Status: Accepted
- Date: 2026-11-20
- Context: M8 needs a local web client for chat, RAG, memory and agent workflows. Open WebUI was
  selected in Phase 06, but its OpenAPI tool calls do not provide the MCP clients' per-call
  destructive approval behavior. A browser-facing API bridge must not expose write/approve actions
  that a model could invoke automatically.
- Decision:
  - Deploy the pinned Open WebUI image as an optional Compose `ui` profile, with local authentication,
    a persistent data volume, and a loopback-only host binding.
  - Connect it to the existing OpenAI-compatible gateway using the internal Compose hostname.
  - Use the pinned MCPO adapter to expose the existing MCP tools as an authenticated OpenAPI server
    on the internal backend network; do not publish the bridge to the host.
  - Use a separate [`config/mcp-ui.yaml`](../../config/mcp-ui.yaml) allow-list: RAG, memory reads and
    agent status/routing/run are available; file writes, memory writes/deletes, and agent
    approve/reject are not registered. Agent work remains proposal-only from the UI; a human reviews
    and approves/rejects through the M6 CLI.
  - Keep Open WebUI accounts, chat and settings in a named volume; require a stable
    `WEBUI_SECRET_KEY` and a separate MCPO API key.
- Alternatives:
  - **AnythingLLM:** turnkey workspaces and RAG, but duplicates PAIEP's RAG/memory path and is more
    opinionated. Retain as an alternative if Open WebUI integration becomes unmaintainable.
  - **Custom UI/API:** complete UX and approval control, but increases implementation and maintenance
    cost and conflicts with ADR 0003's integrate-first decision.
  - **Expose full MCP via MCPO:** fewer adapters, but OpenAPI tools do not preserve MCP destructive
    annotations as an approval gate; rejected for file writes and agent approvals.
  - **Direct container network for tools:** rejected in favor of MCPO authentication plus backend-only
    networking and a restricted MCP configuration.
- Consequences:
  - **Benefits:** reuses the established gateway/MCP backends; UI can be disabled without affecting
    M1–M7; model calls cannot directly apply files or mutate memory through the UI tool set.
  - **Drawbacks:** Open WebUI's first model/tool connections require one-time admin setup; code-change
    tasks require a separate CLI approval; Open WebUI and MCPO image versions and license terms must
    be reviewed when upgrading.
  - **Complexity:** low-to-moderate; one optional UI container and one MCPO bridge.
  - **Cost:** $0; local CPU/RAM use is workload-dependent. On Profile A, enable only when needed.
  - **Hardware impact:** Open WebUI adds a lightweight web service; inference remains on the existing
    Ollama CPU/GPU profile.
  - **Future scalability:** the loopback binding is intentionally not a remote-access design. LAN or
    multi-user access requires M10 authentication, TLS, authorization and network hardening.
  - **Trust assumption:** `PAIEP_SCOPE` is client-selected, not authenticated; acceptable for a
    single-user laptop, not a shared Profile-D host.
