"""Resolve machine-specific paths and drop files for options that are off.

Placeholders replaced in every generated text file:
  __PAIEP_HOME__       absolute path of the PAIEP checkout (forward slashes)
  __PAIEP_WORKSPACE__  absolute path of this generated workspace (forward slashes)
"""
import shutil
import sys
from pathlib import Path

ws = Path.cwd().resolve()
home_raw = r"""{{ cookiecutter.paiep_home }}""".strip()


def default_home() -> Path | None:
    """The PAIEP checkout this template lives in. cookiecutter passes the template path through
    as typed (maybe relative to the caller's cwd, while hooks run in the generated dir)."""
    repo = Path(r"""{{ cookiecutter._repo_dir }}""")
    if not repo.is_absolute():
        out = Path(r"""{{ cookiecutter._output_dir }}""")
        if out.is_absolute() or ".." in out.parts:
            return None
        origin = ws.parent
        for _ in [p for p in out.parts if p != "."]:
            origin = origin.parent
        repo = origin / repo
    return repo.resolve().parents[1]


home = Path(home_raw).expanduser().resolve() if home_raw else default_home()
if home is None or not (home / "docker" / "docker-compose.yml").is_file():
    sys.exit(f"ERROR: cannot locate the PAIEP checkout ({home}). Use an absolute template path "
             "(cookiecutter <PAIEP>/templates/workspace) or pass paiep_home=<absolute PAIEP path>.")

copilot_on = "{{ cookiecutter.copilot }}" == "enabled"
agent = "{{ cookiecutter.agent_client }}"
remove = []
if not (copilot_on and "{{ cookiecutter.copilot_mcp }}" == "yes"):
    remove.append(".vscode/mcp.json")       # keep PAIEP tool results away from the cloud model
if not copilot_on:
    remove.append(".github/copilot-instructions.md")
remove += [".roo"] if agent == "cline" else [".clinerules", ".paiep/cline_mcp_settings.json"]

for rel in remove:
    p = ws / rel
    if p.is_dir():
        shutil.rmtree(p)
    elif p.exists():
        p.unlink()

subs = {"__PAIEP_HOME__": home.as_posix(), "__PAIEP_WORKSPACE__": ws.as_posix()}
for p in ws.rglob("*"):
    if p.is_file() and p.suffix in (".json", ".yaml", ".yml", ".md"):
        text = p.read_text(encoding="utf-8")
        if any(k in text for k in subs):
            for k, v in subs.items():
                text = text.replace(k, v)
            p.write_text(text, encoding="utf-8")

print(f"PAIEP workspace config written to {ws}")
print(f"  backend: {home.as_posix()}  (see .paiep/README.md to finish setup)")
