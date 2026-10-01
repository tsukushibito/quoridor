<!-- setup-godot-devcontainer:start -->
- Before creating DevContainer Worktrees or downloading inference models, read [.devcontainer/storage-policy.md](.devcontainer/storage-policy.md).
<!-- setup-godot-devcontainer:end -->

## Task tracking

- Use Beads for task status, ownership, dependencies, and handoffs. Follow [the project workflow](docs/development/beads-workflow.md).
- Use `bash scripts/dev/beads.sh` for all project Beads operations (including reads); it shares one store across worktrees and serializes access. Start with `ready --json` and `show <id>`. Run `backup sync` before ending a work session.
- This applies to individual work and delegated work. Beads does not require or authorize Lead/Sidekick; use that workflow only when the user explicitly invokes it.
- The current task owner maintains the issue and closes it after verification. With Lead/Sidekick, the Sidekick reports readiness and the Lead closes it after acceptance.
- Keep design specifications and verification evidence in their existing documents; link them from issues instead of maintaining duplicate task lists.
- Respect an explicit user pause. An issue becoming ready or a late agent notification does not by itself authorize resuming paused work.
- Until Beads installation and shared storage are verified, report that setup is incomplete; do not claim tasks were registered or automatically resume work paused for that setup.

## AI research team

- When the user invokes the AI research team, follow [the team design](docs/design/ai-research-team.md) and the common and role instructions in `.agents/research-team/`.
- The five roles use independent saved sessions on the existing App Server. Research follows competing hypotheses and experiments; it is not a fixed sequential implementation pipeline.
- Role instructions alone do not authorize research execution or recursive delegation. Each task needs its Beads issue, scope, worktree/write owner, resource budget, and verification contract. Team setup does not resume deferred AI implementation or start training.
