Two paths. **Default to Path B (`/prd-to-issues`).** Use Path A (OpenSpec) ONLY when the user explicitly asks for the OpenSpec / `opsx:propose` route. If the repo already standardizes on OpenSpec, you may surface it as an option, but do not switch to it without the user opting in.

**Path B (default): direct slicing.** Slice SPEC.md into tracer-bullet vertical slices as issues on the project tracker. Right for nearly every project: lightweight, no new dependency, and the slices become assignable, closeable, PR-linkable work items. The durable design rationale already lives in the versioned `SPEC.md` and `architecture.drawio`, so the issues only need to carry the sliced work.

1. Invoke `/prd-to-issues` with SPEC.md as input.
2. Confirm the tracer-bullet vertical slices match the module inventory in SPEC.md.
3. Hand off to `/tdd` against the top-priority issue.

**Path A (opt-in): OpenSpec.** Use only when the user explicitly requests it, or the repo's established workflow is OpenSpec and the user confirms staying on it. Its value is per-change spec deltas versioned alongside code and a living spec corpus; without that need it is ceremony.

If OpenSpec is not installed in this project:
```
npm install -g @fission-ai/openspec
openspec init . --tools claude
```
Restart this Claude session afterwards so the slash commands register.

Once SPEC.md is approved:

1. Pick a kebab-case change name (e.g., `add-billing-export`, `migrate-to-postgres`).
2. Run `/opsx:propose <change-name>` and provide SPEC.md content as the description input. OpenSpec scaffolds `openspec/changes/<change-name>/` and generates `proposal.md`, `design.md`, `tasks.md`, and spec deltas.
3. Review the generated artifacts. Edit any that diverge from SPEC.md.
4. Validate: `openspec validate <change-name>`. Resolve any failures.

Do NOT install OpenSpec into a project just to satisfy this skill. Default to Path B.
