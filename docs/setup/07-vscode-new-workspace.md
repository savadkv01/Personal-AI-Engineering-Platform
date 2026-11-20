# PAIEP setup for a new VS Code workspace — step by step

> Companion to [07 — VS Code Integration (M7)](07-vscode-integration.md), which explains the design and all
> options. This walkthrough is written for the primary Windows machine (paths and ports below) and records
> the fixes found while setting up `local_agentic_test`; adjust paths/ports on other machines.

This guide connects a new (or existing) repository to the local, offline **PAIEP** backend and configures
**Continue** (chat, edit, autocomplete) and **Cline** (agentic tasks) against it.

> Replace `<repo-name>` with your repository **folder name, exactly** (letters, digits, `.`, `_`, `-`;
> e.g. `my-api` or `local_agentic_test`) and `<parent-folder>` with the folder that *contains* the repo
> (for `C:\Users\user\Downloads\my-api` the parent is `C:\Users\user\Downloads`).

---

## 0. Facts about this machine (read once)

| Item | Value | Where it comes from |
|------|-------|---------------------|
| PAIEP checkout | `C:\D Drive\Projects\DE\Personal-AI-Engineering-Platform` (called `<PAIEP>` below) | — |
| Gateway (OpenAI-compatible) | `http://127.0.0.1:8081/v1` | `GATEWAY_HOST_PORT` in `<PAIEP>\docker\.env` |
| Ollama (autocomplete) | `http://127.0.0.1:11435` (**not** the default 11434 — a native Ollama uses 11434) | `OLLAMA_HOST_PORT` in `<PAIEP>\docker\.env` |
| Gateway token | value of `GATEWAY_TOKEN` in `<PAIEP>\docker\.env` | never paste it into committed files or chats |
| Chat model | `qwen2.5-coder:7b` | template default |
| Autocomplete model | `qwen2.5-coder:1.5b-base` | template default |
| Compose CLI for MCP | `docker-compose` (Windows needs the standalone binary) | template default |
| Cline global MCP file | `C:\Users\user\.cline\data\settings\cline_mcp_settings.json` | open it from the Cline UI (step 7.3) |
| Continue user folder | `C:\Users\user\.continue\` | — |

Prerequisites (one-time per machine): Docker Desktop running, Python on `PATH`, VS Code with the
**Continue** (`continue.continue`) and **Cline** (`saoudrizwan.claude-dev`) extensions installed. Do **not**
install Roo Code alongside Cline.

---

## 1. Start the shared PAIEP backend (once per machine boot)

Open PowerShell and run:

```powershell
cd "C:\D Drive\Projects\DE\Personal-AI-Engineering-Platform\docker"

# First time only (or after PAIEP code changes): build the MCP image
docker compose --profile mcp build mcp

# Every time Docker was restarted: start gateway + vector DB + Postgres (Ollama starts with them)
docker compose --profile mcp up -d gateway qdrant postgres

# First time only: pull the autocomplete model into the PAIEP Ollama container
docker exec paiep_ollama ollama pull qwen2.5-coder:1.5b-base
```

Check that everything is up:

```powershell
docker ps --format "{{.Names}}  {{.Ports}}" | Select-String paiep_
```

You should see `paiep_gateway 127.0.0.1:8081`, `paiep_ollama 127.0.0.1:11435`, `paiep_qdrant`, `paiep_postgres`.

Also confirm both models exist:

```powershell
docker exec paiep_ollama ollama list
```

`qwen2.5-coder:7b` and `qwen2.5-coder:1.5b-base` must both be listed.

> Windows note: `<PAIEP>\docker\.env` already has `PAIEP_GIT_AUTOCRLF=true`; keep it, otherwise the MCP
> `git_status` tool reports every CRLF file as modified.

---

## 2. Install the scaffolding tool (once per machine)

```powershell
pip install cookiecutter==2.7.1
cookiecutter --version
```

---

## 3. Generate the PAIEP config files into the workspace

This works for a brand-new folder **or** an existing repo. With `--skip-if-file-exists`, files that already
exist are kept untouched, and only missing ones are added.

```powershell
cookiecutter "C:\D Drive\Projects\DE\Personal-AI-Engineering-Platform\templates\workspace" `
  -o "<parent-folder>" `
  --no-input --overwrite-if-exists --skip-if-file-exists `
  project_name=<repo-name> project_slug=<repo-name> `
  ollama_url=http://127.0.0.1:11435
```

Important details:

- Always use the **absolute** template path (the post-generation hook finds the PAIEP checkout from it).
- `ollama_url=http://127.0.0.1:11435` is **required on this machine** (default 11434 is the wrong Ollama).
- `project_slug` must equal the repo **folder name exactly**, because the output folder is
  `<parent-folder>\<project_slug>`. Always pass it: if omitted, it is derived from `project_name` with
  underscores turned into hyphens (`local_agentic_test` → `local-agentic-test`, a *different* folder).
- Optional extra arguments (append to the command above):
  - `copilot=disabled` – sensitive/private repo: turns off Copilot AI features in this workspace.
  - `inline_provider=copilot` – use Copilot instead of Continue for tab completion (only one provider per workspace).
  - `copilot_mcp=yes` – also expose PAIEP tools to Copilot agent mode (tool results then go to the cloud model).
  - `memory_scope=project:<name>` – change the RAG/memory scope (default `project:<repo-name>`).

### 3.1 What gets created

```
<repo-name>\
├── AGENTS.md                        conventions for all AI agents (commit)
├── .github\copilot-instructions.md  Copilot instructions (commit; absent if copilot=disabled)
├── .vscode\
│   ├── settings.json                one inline provider, Continue autocomplete on (commit)
│   └── extensions.json              recommends Continue + Cline, discourages Roo (commit)
├── .continue\
│   ├── models\paiep.yaml            chat 7B via gateway + autocomplete 1.5B via Ollama (commit)
│   ├── mcpServers\paiep.yaml        2 MCP servers (machine-specific paths — your choice)
│   ├── rules\paiep.md               Continue rules (commit)
│   ├── .env.example                 template for the secret (commit)
│   └── .gitignore                   ignores .env (commit)
├── .clinerules\paiep.md             Cline rules (commit)
└── .paiep\
    ├── README.md                    short version of this guide
    └── cline_mcp_settings.json      snippet to merge into Cline's GLOBAL MCP settings
```

Only with options: `.vscode\mcp.json` (`copilot_mcp=yes`) and `.roo\` (`agent_client=roo`, instead of
`.clinerules\`).

Verify the Ollama port landed correctly:

```powershell
Select-String -Path "<parent-folder>\<repo-name>\.continue\models\paiep.yaml" -Pattern "apiBase"
```

Expected: `http://127.0.0.1:8081/v1` (chat) and `http://127.0.0.1:11435` (autocomplete).

---

## 4. Older workspaces only: fix the Continue model file

> **Workspaces generated from the template since 2026-11-21 already contain this fix — skip this step.**
> Check with `Select-String -Path "<repo>\.continue\models\paiep.yaml" -Pattern "apiKey|authorization"`:
> if it shows `authorization: Bearer ...`, you are done.

**Why:** the current `GATEWAY_TOKEN` contains only digits. Continue inserts the secret into the YAML text
*before* parsing it, so `apiKey: 1234…` becomes a **number** and Continue rejects the whole config
(`models.0.apiKey: Expected string, received number`). Symptoms: status bar shows
**Continue (config error)** and the **Select model** picker is empty. Quoting the value does not help
(Continue re-serialises the YAML before substituting).

Open `<repo-name>\.continue\models\paiep.yaml` and, in the **first** model
(`PAIEP qwen2.5-coder:7b (local)`), replace

```yaml
    apiKey: ${{ secrets.PAIEP_GATEWAY_TOKEN }}
```

with

```yaml
    # Header instead of apiKey: an all-digit token would be parsed as a YAML number.
    requestOptions:
      timeout: 1800000   # ms; the default 10 min aborts slow CPU agent prompts (keep < 2147483)
      headers:
        authorization: Bearer ${{ secrets.PAIEP_GATEWAY_TOKEN }}
```

Keep the indentation exactly (4 spaces before `requestOptions`). The resulting model block looks like:

```yaml
  - name: PAIEP qwen2.5-coder:7b (local)
    provider: openai
    model: qwen2.5-coder:7b
    apiBase: http://127.0.0.1:8081/v1
    # Header instead of apiKey: an all-digit token would be parsed as a YAML number.
    requestOptions:
      timeout: 1800000
      headers:
        authorization: Bearer ${{ secrets.PAIEP_GATEWAY_TOKEN }}
    roles: [chat, edit, apply]
    capabilities: [tool_use]
    ...
```

The gateway checks exactly `Authorization: Bearer <GATEWAY_TOKEN>`, so this is equivalent and always a string.

> You can also avoid this by changing `GATEWAY_TOKEN` to a value containing letters (then recreate the
> gateway: `docker compose --profile ui up -d --force-recreate gateway paiep-mcp-http paiep-tools-api`, and
> update the key everywhere it is used: Open WebUI connection, every `.continue\.env`, Cline).

---

## 5. Create the Continue secret file

The secret lives only in git-ignored `.env` files — never in YAML.

```powershell
$repo = "<parent-folder>\<repo-name>"
Copy-Item "$repo\.continue\.env.example" "$repo\.continue\.env"
notepad "$repo\.continue\.env"
```

In Notepad, set the line to the value of `GATEWAY_TOKEN` from `<PAIEP>\docker\.env`:

```
PAIEP_GATEWAY_TOKEN=<value of GATEWAY_TOKEN>
```

Rules for this file: one line, no quotes, no spaces around `=`, no trailing spaces. Save and close.

**Optional fallback:** if Continue still reports `API key secret not found` after a **Reload Window**, add
the same line to the per-user file `C:\Users\user\.continue\.env` (Continue also reads secrets from there).
It already exists on this machine. Remember it is one more place to update if the token changes:

```powershell
notepad "$env:USERPROFILE\.continue\.env"
```

Check (prints only the key names, not the values):

```powershell
foreach ($f in "$repo\.continue\.env", "$env:USERPROFILE\.continue\.env") {
  "$f -> " + ((Get-Content $f | ForEach-Object { ($_ -split '=',2)[0] }) -join ', ')
}
```

The workspace file must show `PAIEP_GATEWAY_TOKEN` (the per-user file only if you added the fallback).

---

## 6. Configure Continue

### 6.1 Keep the user-level config empty

The models come from the workspace file `.continue\models\paiep.yaml`. **Do not** copy them into
`C:\Users\user\.continue\config.yaml` as well (that duplicates models and caused trouble before). That file
should stay:

```yaml
name: Main Config
version: 1.0.0
schema: v1
models: []
```

Also do **not** click "create new config / add agent" in Continue for this workspace: it writes example files
(`.continue\agents\new-config*.yaml`) with placeholder keys. If such files appear, move them out of
`.continue\agents\`.

### 6.2 Open the workspace and reload

1. `code "<parent-folder>\<repo-name>"` (or **File → Open Folder**).
2. Accept "install recommended extensions" if prompted (Continue, Cline, Container Tools, Mermaid).
3. `Ctrl+Shift+P` → **Developer: Reload Window**. Continue reads new `.env` files only after a reload.

### 6.3 Settings inside the Continue panel

1. Click the **Continue** icon in the activity bar.
2. Top-right dropdown: select **Main Config**. (Workspace blocks are merged into it automatically.)
3. Below the input box, set the mode dropdown to **Agent** (MCP tools only work in Agent mode).
4. Click **Select model** → choose **PAIEP qwen2.5-coder:7b (local)**.
5. Tab autocomplete needs no selection: the `autocomplete` role is already assigned to
   **PAIEP autocomplete qwen2.5-coder:1.5b-base**. `.vscode\settings.json` turns it on
   (`continue.enableTabAutocomplete: true`) and Copilot inline completions off.
6. Status bar (bottom right) should read **Continue** (with a check mark) — **not** "Continue (config error)".
7. MCP tools: open Continue settings (gear icon) → **Tools / MCP**. The servers `paiep-local` (fs, git) and
   `paiep` (rag, memory, paiep-tools) should be listed and connected. The first start takes a few seconds per
   container.

### 6.4 Test Continue

In Agent mode, ask:

```
Use rag_search: which Docker networks does PAIEP use and why? Cite sources as [n].
```

(Answered from `knowledge/notes/offline-first.md`. Avoid "what is the default chat model?" — the knowledge
base does not contain that fact.) Expect a few minutes on CPU, and longer if Ollama is busy with another
request (one at a time).

Then open any code file and type — grey inline suggestions should come from the 1.5B model.

---

## 7. Configure Cline

### 7.1 API provider

1. Click the **Cline** icon → gear (**Settings**) → **API Configuration**.
2. **API Provider:** `OpenAI Compatible`
3. **Base URL:** `http://127.0.0.1:8081/v1`
4. **API Key:** the value of `GATEWAY_TOKEN` from `<PAIEP>\docker\.env` (Cline stores it securely; the numeric
   token is fine here).
5. **Model ID:** `qwen2.5-coder:7b`
6. Optional (model info): context window `8192`; leave images/computer-use off.
7. Click **Done / Save**.

Cline settings are global, so this is needed only once per machine.

### 7.2 What the MCP snippet contains

`<repo-name>\.paiep\cline_mcp_settings.json` defines two servers whose names carry the repo slug:

- `paiep-local-<repo-name>` → `docker-compose … run --rm -T mcp-local fs git` (no network, timeout 120 s)
- `paiep-<repo-name>` → `docker-compose … run --rm -T mcp rag memory paiep-tools` (timeout 900 s)

Each has `PAIEP_WORKSPACE` = the repo path and `PAIEP_SCOPE` = `project:<repo-name>`, `disabled: false`, and
an `autoApprove` list of read-only tools only.

### 7.3 Merge it into Cline's global MCP settings

**Via the UI (recommended):**

1. Cline panel → **MCP Servers** icon (stacked-servers icon in the Cline toolbar).
2. **Configure** tab → **Configure MCP Servers**. This opens the global
   `cline_mcp_settings.json` (on this machine `C:\Users\user\.cline\data\settings\cline_mcp_settings.json`).
3. Open `<repo-name>\.paiep\cline_mcp_settings.json` side by side.
4. Copy the **two entries inside** `"mcpServers": { … }` from the snippet and paste them **inside** the existing
   `"mcpServers": { … }` object of the global file. Do **not** replace the whole file — other workspaces'
   entries (e.g. `paiep-local_agentic_test`) must stay. Mind the commas between entries.
5. Save. Cline reloads the file automatically.

**Or via a command** (merges and keeps existing entries; makes a `.bak` first):

```powershell
@'
import json, pathlib, shutil, sys
repo = pathlib.Path(sys.argv[1])
glob = pathlib.Path.home() / ".cline/data/settings/cline_mcp_settings.json"
snippet = json.loads((repo / ".paiep/cline_mcp_settings.json").read_text(encoding="utf-8"))
data = json.loads(glob.read_text(encoding="utf-8")) if glob.exists() else {"mcpServers": {}}
if glob.exists():
    shutil.copy(glob, str(glob) + ".bak")
data.setdefault("mcpServers", {}).update(snippet["mcpServers"])
glob.parent.mkdir(parents=True, exist_ok=True)
glob.write_text(json.dumps(data, indent=2), encoding="utf-8")
print("servers now:", ", ".join(data["mcpServers"]))
'@ | python - "<parent-folder>\<repo-name>"
```

### 7.4 Check the servers

In **MCP Servers → Installed**, both `paiep-local-<repo-name>` and `paiep-<repo-name>` should show a
**green** dot with their tools listed (fs_*, git_*, rag_*, memory_*, agent_*). If one is red, click
**Restart** on it after confirming the backend from step 1 is running.

### 7.5 Test Cline

Start a new Cline task:

```
List the files in this workspace with fs_list, then run git_status.
```

Read-only tools run without asking; writes (`fs_apply_write`) and other destructive tools always ask for approval.

---

## 8. End-to-end verification from the command line (optional but recommended)

The smoke test imports the MCP client library, which lives in PAIEP's virtual environment (the system
`python` does not have it — `ModuleNotFoundError: No module named 'mcp'`):

```powershell
$paiep = "C:\D Drive\Projects\DE\Personal-AI-Engineering-Platform"
& "$paiep\.venv\Scripts\python.exe" "$paiep\scripts\mcp-smoke.py" `
  --workspace "<parent-folder>\<repo-name>" --scope project:<repo-name>
```

Every server should report OK. Quick gateway check (prints only the HTTP status, not the token):

```powershell
$tok = ((Get-Content "<parent-folder>\<repo-name>\.continue\.env" | Select-String '^PAIEP_GATEWAY_TOKEN=').Line -split '=',2)[1]
(Invoke-WebRequest http://127.0.0.1:8081/v1/models -Headers @{ authorization = "Bearer $tok" } -UseBasicParsing).StatusCode
Remove-Variable tok
```

Expected: `200`.

---

## 9. Git: what to commit

| Commit | Do not commit |
|--------|---------------|
| `AGENTS.md`, `.github\`, `.vscode\settings.json`, `.vscode\extensions.json` | `.continue\.env` (already git-ignored) |
| `.continue\models\`, `.continue\rules\`, `.continue\.env.example`, `.continue\.gitignore` | any file containing the token |
| `.clinerules\` | `.continue-backup\` or other local backups |
| `.continue\mcpServers\paiep.yaml` — optional (contains this machine's paths) | |

---

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Status bar **Continue (config error)**, model picker empty, no error visible | Continue only logs config errors to the developer console | `Help → Toggle Developer Tools → Console`, filter `config`, then Continue **Main Config → Reload**; read the red `Errors loading config` line |
| `models.0.apiKey: Expected string, received number` | All-digit token substituted into `apiKey` | Step 4 (use the `authorization` header) |
| `API key secret not found` / HTTP 401 | Token missing or different | Step 5: same value in `.continue\.env`, `~\.continue\.env` and `docker\.env`; then **Reload Window** |
| Picker worked, then disappeared after **Reload Window** | Config only fails when secrets are (re)resolved | Same as the apiKey/number error above |
| Duplicate or unexpected models / "Example Config" | Models copied into `~\.continue\config.yaml`, or `.continue\agents\new-config*.yaml` created | Restore `models: []` (step 6.1); move the `new-config*.yaml` files away |
| No "Continue" entry in **View → Output** | Normal for Continue 2.0 | Use Developer Tools console (first row) |
| Autocomplete: model not found / timeout | Wrong Ollama port or model not pulled | `apiBase` must be `http://127.0.0.1:11435`; `docker exec paiep_ollama ollama pull qwen2.5-coder:1.5b-base` |
| MCP server red, log says `unknown shorthand flag: 'f'` | `docker compose` used under a minimal env | Keep `docker-compose` (template default) |
| MCP server red / connection closed | Backend not running | Step 1 `up -d …`; then Restart the server in Cline / reload Continue |
| `git_status` shows every file modified | CRLF checkout | `PAIEP_GIT_AUTOCRLF=true` in `<PAIEP>\docker\.env` |
| `DENIED: …` from a tool | Server-side policy working as intended | Change `<PAIEP>\config\mcp.yaml`, not the client |
| Cline timeout on `rag_answer` / `agent_approve` | CPU generation takes minutes | Prefer `rag_search`; use `agent_run` + `agent_status`; timeout is already 900 s |
| Continue Agent mode: no reply, aborted after exactly 10 min, then retried | CPU reads prompts at ~5 tok/s, and an agent prompt with all tool schemas is 3k+ tokens (>10 min before the first word) | `requestOptions.timeout: 1800000` (template since 2026-11-21; step 4 for older workspaces), so the first agent message may take 10–15 min. For faster replies use **Chat** mode with `@file` context, or disable unused tools in Continue's tool menu |

---

## 11. Quick checklist

- [ ] Backend containers up (`paiep_gateway`, `paiep_ollama`, `paiep_qdrant`, `paiep_postgres`)
- [ ] Both models pulled (`qwen2.5-coder:7b`, `qwen2.5-coder:1.5b-base`)
- [ ] `cookiecutter … ollama_url=http://127.0.0.1:11435` run with the correct `project_slug`
- [ ] Older workspace only: `.continue\models\paiep.yaml` uses the `authorization` header (not `apiKey`)
- [ ] `.continue\.env` contains `PAIEP_GATEWAY_TOKEN` (and `~\.continue\.env` only if needed)
- [ ] `~\.continue\config.yaml` has `models: []`; no `new-config*.yaml` in `.continue\agents\`
- [ ] **Developer: Reload Window**; Continue status bar without "config error"
- [ ] Continue: **Main Config**, **Agent** mode, model **PAIEP qwen2.5-coder:7b (local)**
- [ ] Cline: OpenAI Compatible, `http://127.0.0.1:8081/v1`, key = gateway token, model `qwen2.5-coder:7b`
- [ ] Cline global MCP: both `paiep-local-<repo-name>` and `paiep-<repo-name>` green
- [ ] Test prompts in Continue (rag_search) and Cline (fs_list + git_status) succeed
