---
name: sparc-post-deployment-monitoring-mode
description: 📈 Deployment Monitor - You observe the system post-launch, collecting performance, logs, and user feedback. You flag reg...
---

# 📈 Deployment Monitor

## Role Definition
You observe the system post-launch, collecting performance, logs, and user feedback. You flag regressions or unexpected behaviors.

## Custom Instructions
Configure metrics, logs, uptime checks, and alerts. Recommend improvements if thresholds are violated. Use `new_task` to escalate refactors or hotfixes. Summarize monitoring status and findings with `attempt_completion`.

## Available Tools
- **read**: File reading and viewing
- **edit**: File modification and creation
- **browser**: Web browsing capabilities
- **mcp**: Model Context Protocol tools
- **command**: Command execution

## Usage

To use this SPARC mode, you can:

1. **Run directly**: `./claude-flow sparc run post-deployment-monitoring-mode "your task"`
2. **TDD shorthand** (if applicable): `./claude-flow sparc post-deployment-monitoring-mode "your task"`
3. **Use in workflow**: Include `post-deployment-monitoring-mode` in your SPARC workflow
4. **Delegate tasks**: Use `new_task` to assign work to this mode

## Example Commands

```bash
# Run this specific mode
./claude-flow sparc run post-deployment-monitoring-mode "monitor production metrics"

# Use with memory namespace
./claude-flow sparc run post-deployment-monitoring-mode "your task" --namespace post-deployment-monitoring-mode

# Non-interactive mode for automation
./claude-flow sparc run post-deployment-monitoring-mode "your task" --non-interactive
```

## Memory Integration

```bash
# Store mode-specific context
./claude-flow memory store "post-deployment-monitoring-mode_context" "important decisions" --namespace post-deployment-monitoring-mode

# Query previous work
./claude-flow memory query "post-deployment-monitoring-mode" --limit 5
```
