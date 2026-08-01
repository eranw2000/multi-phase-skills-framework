---
description: "Standing instruction: finish planning and verification (including plan-gate and plan-auditor), then stop so you can switch the model before implementation. Analysis phases (evidence, audit, strategy brainstorm) run before the switch."
argument-hint: "(none)"
---

Register a standing instruction for THIS session: after the planning and verification phases are complete, stop and wait for the user to switch the model before any implementation begins. Acknowledge in one line that the pause is armed, then carry on with whatever was in progress.

(Deliberately no `model:` frontmatter pin, unlike the rest of this pack. A pin would switch the serving model for the invoking turn, in the middle of the planning session this command exists to protect. It only injects an instruction. Do not "fix" this by adding a pin for consistency with the other artifacts.)

## Why

Planning and implementation are different jobs and are worth running on different models: a frontier model to understand the codebase and choose the design, a cheaper one to write the code against a finished plan. The saving comes from the fact that planning is input-heavy and output-light while coding is the reverse.

The practical problem is the transition. In one continuous session it is easy to roll straight from an approved plan into building on the planning model, and the switch never happens. This command puts a hard stop at the boundary so the switch is a deliberate step.

## The workflow this arms

1. **Planning phase, as normal.** Plan mode, plan file, `ExitPlanMode` approval.
2. **Verification phase, as normal.** The `plan-gate` skill with the `plan-auditor` agent: every weak spot driven to Fixed or explicitly Accepted, the outcome recorded in the plan file. The pause is not a reason to skip or thin the gate. It does change how the gate ends: `plan-gate` normally releases straight into execution, and this instruction overrides that final step.
3. **Then STOP, before any implementation.** No repo edits, no code, no commits, no deploys, no config changes. Stopping here is the instruction, and it is a deliberate exception to any standing "execute autonomously" preference.

   **Analysis phases are NOT implementation.** Planning, evidence-gathering, audits, and strategy brainstorming are all analysis and stay on the planning model. If the approved plan has analysis phases between the gate and implementation, the post-gate handoff says "stay on the planning model, say continue"; those phases then run there, and a SECOND stop fires at the plan's implementation boundary (the first repo or code edit), which is where the model-switch request belongs.
4. **The stop message must hand off cleanly**, containing:
   - confirmation the gate is complete, with the weak-spot tally (N found, X fixed, Y accepted);
   - the plan file path;
   - the exact resume point (the next step);
   - a closing request for input: if the next step is implementation, ask the user to switch the model (`/model opus`, or whichever model they name) and then say "continue"; if analysis phases come first, tell them to stay on the current model and say "continue". In that second case, say that the switch request comes later, at the implementation boundary.
5. **On "continue", proceed.** Run the plan's analysis phases (if any) on the planning model, stop again at the implementation boundary for the switch, then execute implementation end-to-end with full autonomy under the new model. Do not re-ask permission for steps that are part of the approved plan.

## Edge cases

- Invoked when the gate is ALREADY complete: stop immediately with the step-4 handoff message.
- Invoked before any plan exists: hold the instruction and apply it when planning starts.
- The user asks to skip the pause: honor it, but say plainly that the pause is disarmed for this session.
- Only the user can change the serving model, with `/model`. A command's or skill's `model:` pin cannot perform the switch: in a background session a pin can stamp the system prompt while the requests still go out on the session model. If which model actually served a turn matters, the transcript's `.message.model` is the ground truth, not the system prompt's claim.
