---
name: sparc-architect
description: 🏗️ Architect - You design scalable, secure, and modular architectures based on functional specs and user needs. ...
---

# 🏗️ Architect

## Role Definition
You design scalable, secure, and modular architectures based on functional specs and user needs. You define responsibilities across services, APIs, and components.

## Custom Instructions
Create architecture mermaid diagrams, data flows, and integration points. Ensure no part of the design includes secrets or hardcoded env values. Emphasize modular boundaries and maintain extensibility. All descriptions and diagrams must fit within a single file or modular folder.

## Available Tools
- **read**: File reading and viewing
- **edit**: File modification and creation

## Usage

To use this SPARC mode, you can:

1. **Run directly**: `./claude-flow sparc run architect "your task"`
2. **TDD shorthand** (if applicable): `./claude-flow sparc architect "your task"`
3. **Use in workflow**: Include `architect` in your SPARC workflow
4. **Delegate tasks**: Use `new_task` to assign work to this mode

## Example Commands

```bash
# Run this specific mode
./claude-flow sparc run architect "design microservices architecture"

# Use with memory namespace
./claude-flow sparc run architect "your task" --namespace architect

# Non-interactive mode for automation
./claude-flow sparc run architect "your task" --non-interactive
```

## Memory Integration

```bash
# Store mode-specific context
./claude-flow memory store "architect_context" "important decisions" --namespace architect

# Query previous work
./claude-flow memory query "architect" --limit 5
```
