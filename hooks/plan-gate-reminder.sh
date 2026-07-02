#!/bin/bash
# PostToolUse hook for the ExitPlanMode tool.
# When a plan is approved and Claude is about to start executing (switching from plan
# mode to auto / accept mode), inject a non-blocking reminder to run the plan-gate skill
# first: surface every weak spot in the approved plan and get each one fixed or
# explicitly accepted with the user before any change is made.
#
# Wire it in ~/.claude/settings.json under hooks.PostToolUse with matcher "ExitPlanMode"
# (see the framework README for the exact snippet).
# Protocol: read JSON from stdin, emit JSON to stdout with hookSpecificOutput.additionalContext, exit 0.
# Non-blocking: the plan is already approved; this is a reminder, not a hard block.

set -u

cat >/dev/null  # consume the tool payload on stdin; the reminder is static

# Static JSON, no jq dependency.
cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "PLAN-GATE: a plan was just approved and you are about to switch from planning to doing. Before you make any change, run the plan-gate skill (~/.claude/skills/plan-gate/SKILL.md): surface every weak spot in the approved plan and drive each one to fixed or explicitly accepted WITH the user, one at a time, until you share a complete understanding. Then proceed. Do not start the implementation until the gate is complete, or the user explicitly tells you to skip it. For a genuinely trivial plan, you may say so and ask the user whether to skip the gate."
  }
}
EOF

exit 0
