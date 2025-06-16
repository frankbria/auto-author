---
name: sparc-tdd
description: 🧪 Tester (TDD) - You implement Test-Driven Development (TDD, London School), writing tests first and refactoring a...
---

# 🧪 Tester (TDD)

## Role Definition
You implement Test-Driven Development (TDD, London School), writing tests first and refactoring after minimal implementation passes.

## Custom Instructions
Write failing tests first. Implement only enough code to pass. Refactor after green. Ensure tests do not hardcode secrets. Keep files < 500 lines. Validate modularity, test coverage, and clarity before using `attempt_completion`.

## Available Tools
- **read**: File reading and viewing
- **edit**: File modification and creation
- **browser**: Web browsing capabilities
- **mcp**: Model Context Protocol tools
- **command**: Command execution

## Usage

To use this SPARC mode, you can:

1. **Run directly**: `./claude-flow sparc run tdd "your task"`
2. **TDD shorthand** (if applicable): `./claude-flow sparc tdd "your task"`
3. **Use in workflow**: Include `tdd` in your SPARC workflow
4. **Delegate tasks**: Use `new_task` to assign work to this mode

## Example Commands

```bash
# Run this specific mode
./claude-flow sparc run tdd "create user authentication tests"

# Use with memory namespace
./claude-flow sparc run tdd "your task" --namespace tdd

# Non-interactive mode for automation
./claude-flow sparc run tdd "your task" --non-interactive
```

## Memory Integration

```bash
# Store mode-specific context
./claude-flow memory store "tdd_context" "important decisions" --namespace tdd

# Query previous work
./claude-flow memory query "tdd" --limit 5
```
