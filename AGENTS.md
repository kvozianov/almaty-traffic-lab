# Agent Instructions

This project uses Obsidian as the operating layer for AI-agent work. Do not treat the Obsidian files as passive documentation. They define the current project strategy, acceptance gates, claim labels, and handoff format.

## Required Start Sequence

Before changing code or project documents, read:

1. `docs/obsidian/00-command-center/Almaty Mobility Command Center.md`
2. `docs/obsidian/00-command-center/AI Agent Operating Manual.md`
3. `docs/obsidian/00-command-center/Obsidian Vault Contract.md`

If the task mentions a durable goal such as `G002`, also read the matching note in:

`docs/obsidian/01-goals/`

## Project Spine

The first product priority is not a generic dashboard. The first sellable epic is `G002 - Scenario Dossier MVP`.

Implementation should strengthen this chain:

`scenario config -> run metadata -> KPI JSON -> scenario dossier -> audit/procurement evidence`

If a task does not improve this chain, treat it as lower priority unless the user explicitly says otherwise.

## Obsidian Workbench Rules

- Use `docs/obsidian/01-goals/*.md` as the source of goal-specific intent, next action, files to touch, and acceptance gates.
- Use `docs/obsidian/03-registries/Artifact Registry.md` to track generated artifacts and evidence.
- Use `docs/obsidian/03-registries/Claim Ledger.md` before making buyer-facing claims.
- Use `docs/obsidian/03-registries/First Corridor Pack - Abay.md` as the first corridor anchor unless the user chooses another corridor.
- Use the templates in `docs/obsidian/04-templates/` for new goal/evidence notes.
- Keep Obsidian links as wikilinks for vault notes, for example `[[G002 - Scenario Dossier MVP]]`.

## Claim Labels

Use these labels consistently:

- `demo`
- `proxy`
- `calibrated`
- `real-data`
- `procurement-ready`

Never silently upgrade a claim level. Add evidence first, then update `Claim Ledger.md`.

## After Completing Work

When a task changes behavior, artifacts, or evidence, update the relevant Obsidian note with:

- what changed
- files touched
- verification command or generated artifact
- unresolved risks
- next action for the next AI agent

For implementation tasks, update `Artifact Registry.md` if a new artifact, API route, report, screenshot, export, or config is created.

## Preferred Task Interpretation

When the user asks for work like "do G002" or "continue the dossier", interpret it as:

1. Read the matching goal note.
2. Follow its acceptance gate.
3. Keep the first-epic Abay dossier path coherent.
4. Update Obsidian workbench notes after implementation.

Do not create broad platform features, public narrative mode, decision knowledge graph, or partner APIs until the first Scenario Dossier path is defensible, unless explicitly requested.

## Obsidian CLI

The `obsidian` CLI may not be installed in the shell environment. Direct file edits in the vault are acceptable. Validate `.base` files as YAML and `.canvas` files as JSON when editing them.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
