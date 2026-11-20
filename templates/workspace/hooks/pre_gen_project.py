"""Validate answers before anything is generated (fail fast, nothing written)."""
import re
import sys

scope = "{{ cookiecutter.memory_scope }}"
slug = "{{ cookiecutter.project_slug }}"

if not re.match(r"^(global|project:[A-Za-z0-9][A-Za-z0-9._-]{0,63})$", scope):
    sys.exit(f"ERROR: memory_scope '{scope}' must be 'global' or 'project:<name>' ([A-Za-z0-9._-]).")
if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", slug):
    sys.exit(f"ERROR: project_slug '{slug}' must be a simple directory name.")
if "{{ cookiecutter.copilot }}" == "disabled" and "{{ cookiecutter.inline_provider }}" == "copilot":
    sys.exit("ERROR: inline_provider=copilot contradicts copilot=disabled.")
