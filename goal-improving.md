Use $agent-orchestration-skill for this task.

You are working on https://github.com/ZypherHQ/agent-orchestration-skill.

Goal:
Improve the Agentic Orchestration Control package so it becomes production-ready as a low-friction npm control room for Codex orchestration.

Do not create demo-only features. Implement production-grade changes only.

Main problems to solve:
1. Commands are still too long and require too many flags.
2. TUI/GUI depend too much on .orchestration runs created by the agent.
3. TUI/GUI must be able to open immediately and show real Codex sessions from CODEX_HOME sessions.
4. Documentation is not clear enough for users.
5. CLI, installed shims, docs, and tests must all agree on one command contract.
6. No hidden .skills/.agents/.codex layout should exist in the package. The production layout is:
   - skills/agent-orchestration-skill/
   - subagents/
   - .orchestration/ for runtime state only

Architecture constraints:
- The skill remains explicit-only.
- The root orchestrator remains in control.
- Workers are leaf-only.
- No one-agent-per-file fan-out.
- No full Context Capsule broadcast.
- Keep .orchestration as the source of truth for AOC orchestration state.
- Add Codex session ingestion as a parallel source, not as a replacement for .orchestration.
- Do not expose remote GUI without explicit opt-in and auth.
- Do not add demo commands or demo payloads to the production package.
- Keep commands short and agent-friendly.

Phase 1 — Audit
Read every file in the repo:
- package.json
- bin/aoc.mjs
- install.sh
- skills/agent-orchestration-skill/SKILL.md
- skills/agent-orchestration-skill/scripts/*
- skills/agent-orchestration-skill/references/*
- subagents/*.toml
- tests/*
- tools/*
- docs/*
- README.md
- AGENTS.md
- SKILL_PACK_MANIFEST.json

Also inspect the currently published npm package behavior using:
- npm pack --dry-run
- npm pack
- npm exec --package ./dist/<tarball> -- agentic-orchestration-control ...

Produce a concise audit summary before editing.

Phase 2 — Short command UX
Implement auto-resolution so users can run:

- aoc
- aoc gui
- aoc sessions
- aoc current
- aoc use <run_id>
- aoc init "task title"
- aoc import
- aoc watch
- aoc usage
- aoc budget
- aoc doctor
- aoc search "query"

without requiring --repo or --run-id in normal usage.

Repo resolution order:
1. --repo
2. AOC_REPO
3. nearest git root from cwd
4. cwd if it contains .orchestration, package.json, skills, or .git
5. clear error

Run resolution order:
1. --run-id
2. AOC_RUN_ID
3. .orchestration/current-run
4. latest .orchestration/runs/*
5. latest imported Codex session
6. no run: show empty dashboard and available Codex sessions

Do not default new runs to "latest".
For new runs, generate a unique run id unless explicitly provided.

Phase 3 — Global CLI flags
Normalize global flags:
- --repo
- --run-id
- --json
- --quiet
- --verbose
- --no-open

These flags must not be forwarded accidentally to Python scripts that do not accept them.
All user-facing commands must support --json where useful:
- init
- sessions
- current
- usage
- budget
- stats
- events
- gates
- doctor
- import

Phase 4 — Codex session discovery/import
Add production-grade Codex session ingestion.

Implement scripts:
- codex_session_discovery.py
- codex_session_importer.py
- codex_session_watch.py
- codex_session_normalize.py

They must discover sessions from:
- --codex-home
- AOC_CODEX_HOME
- CODEX_HOME
- ~/.codex
- /root/.codex when readable

Read:
- sessions/YYYY/MM/DD/rollout-*.jsonl

Importer behavior:
- Parse JSONL safely.
- Ignore malformed lines but record warnings.
- Infer repo/cwd when present.
- Infer timestamps, status, thread/session id, user prompts, assistant messages, tool/command events when available.
- Create imported run state under:
  .orchestration/runs/codex-<date>-<shortid>/
- Mark source as "codex_session_import".
- Store original session path in state.json.
- Write normalized events to events.jsonl.
- Do not overwrite AOC-native runs.
- Do not require the agent to call aoc init.

TUI/GUI must show imported Codex sessions even if .orchestration/runs had no native AOC run.

Phase 5 — TUI/GUI changes
Update TUI and GUI so opening them immediately works:

- aoc
- aoc gui

They must display:
- AOC orchestrations
- imported Codex sessions
- current run
- source badge: AOC / CODEX / APP_SERVER
- status
- last event
- repo
- run/session path
- usage estimate when available
- memory/index status
- gates if available

If no sessions exist:
- show an empty-state page with exact next steps
- do not crash
- do not require init

Add "import Codex sessions" action in CLI and GUI-safe API.

Phase 6 — Command contract
Create a command contract file, for example:

tools/aoc.commands.json

It must define:
- commands
- aliases
- options
- default repo/run behavior
- output modes
- target script or JS handler

Use this contract to validate:
- bin/aoc.mjs help
- README command list
- tests
- installed shims

Prevent drift between npm CLI and installed .orchestration/bin/aoc.

Phase 7 — Documentation rewrite
Rewrite README.md to be clear and short.

Required structure:
1. What this is
2. Start in 10 seconds
3. Short commands
4. What opens before a run exists
5. AOC run vs Codex session
6. How the skill works
7. TUI/GUI
8. Usage/budget
9. Codex session import
10. Safety model
11. Troubleshooting
12. Development/publishing

Move large script/reference tables to docs/COMMANDS.md or docs/ARCHITECTURE.md.

Remove confusing placeholder commands like:
- /path/to/repo
- <repo>

Use real examples:
- aoc
- aoc gui
- aoc init "Fix checkout flow"
- aoc sessions
- aoc import
- aoc current
- aoc use <run_id>

Phase 8 — Memory/search improvement
Add or improve:
- aoc search "query"

It should search:
- .orchestration/runs/*/state.json
- events.jsonl
- handoffs
- dispatches
- evidence
- memory notes
- imported Codex session summaries

Prefer a lightweight local index:
- SQLite FTS if available
- fallback to simple text search

Do not require external services.

Phase 9 — Tests
Add strict tests for the exact failures we want to prevent.

Tests must cover:
1. npm test
2. npm run test:npm-cli
3. npm run publish:check
4. npm pack --dry-run
5. npm pack
6. npm exec --package ./dist/*.tgz -- agentic-orchestration-control install <temp-repo>
7. aoc no-flag behavior from inside a git repo
8. aoc gui --once with no AOC run
9. fake CODEX_HOME session import
10. TUI/GUI show imported Codex session without aoc init
11. aoc init "task" --json works
12. aoc sessions --json works
13. installed .orchestration/bin/aoc equals npm CLI behavior
14. package contains skills/ not .skills/
15. package contains subagents/
16. package does not contain .agents, .codex, .skills, demo_run.py, __pycache__, *.pyc
17. workflow-diagram size warning or optimized asset
18. command contract and README commands are in sync

Use temporary directories only.
Do not modify user global ~/.codex during tests.
Use AOC_CODEX_HOME pointing to a fake temp directory.

Phase 10 — Acceptance criteria
The final result is accepted only if all pass:

- npm test
- npm run test:npm-cli
- npm run publish:check
- npm pack --dry-run
- npm pack
- local npm exec tarball install smoke test
- fake Codex session import test
- TUI snapshot without AOC run
- GUI snapshot without AOC run
- no hidden legacy layout in npm tarball
- README no longer recommends long commands as the default path

Return:
1. files changed
2. exact tests run
3. before/after command examples
4. remaining risks
5. publish instructions
