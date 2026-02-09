---
name: holodeck-setup
description: Configure and validate Holodeck preferences and credentials (local vs cloud providers). Use when starting on a new machine, when build fails due to missing keys, or when switching between local and cloud backends.
disable-model-invocation: true
context: fork
allowed-tools: Bash(holodeck:*)
---

# Holodeck Setup (Minimal)

## Goal
Run config + capability checks and produce clear, actionable setup instructions.
- Do NOT ask the user to paste API keys into chat.
- Do NOT write API keys into files from this skill.

## Steps
1) Show effective config:
~~~bash
holodeck config show --json
~~~

2) Validate capabilities:
~~~bash
holodeck debug validate --json
~~~

3) Analyze and Instruct:
- If any provider is unavailable due to missing key:
  - Output exact environment variable name(s) to set.
  - Instruct user to set them locally (e.g., Windows: `setx KEY_NAME "value"`, then restart terminal).
  - Re-run `holodeck debug validate --json` to confirm.

## Output
- effective_config summary (local/cloud choices)
- capabilities summary (available/unavailable + reason)
- next steps (exact commands user should run)