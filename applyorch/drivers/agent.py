"""Agent driver: hand the rendered brief to a computer-use subagent.

This repository's code never clicks a real Submit button. For a real
application the orchestrator stops here: it has already run every gate it can
run offline and written the brief, and the brief is dispatched to ONE
computer-use subagent (for example a Claude Code subagent with the computer-use
MCP server attached; see docs/computer-use-recipe.md). That agent runs the
fresh-snapshot pre-submit gate itself, inside the browser.

When the agent reports back, record its outcome with:
  python3 -m applyorch record --key <role> --status SUBMITTED --confirmation "<text>"
which appends to the ledger and fires the notification.
"""
from __future__ import annotations


class AgentDriver:
    name = "agent"

    def run(self, packet, expected, resume_path, session, may_submit, brief_path=""):
        return {"status": "HANDED_OFF", "problems": [], "left_for_human": [],
                "confirmation": "", "submitted": False,
                "trajectory": [f"brief written: {brief_path}",
                               "dispatch to one computer-use subagent; wait for its report"]}
