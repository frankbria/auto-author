# Claude Code Configuration - SPARC Development Environment

## Project Overview
This project uses the SPARC (Specification, Pseudocode, Architecture, Refinement, Completion) methodology for systematic Test-Driven Development with AI assistance through Claude-Flow orchestration.
This is a monorepo for the auto-author project with a Next.js frontend and FastAPI backend.
## Project Structure

-    `frontend/` - Next.js application
-    `backend/` - FastAPI Python application
-    `docs/` - Project documentation

## Development Commands
### Backend (FastAPI)

  -  Setup: `cd backend && uv venv && source .venv/bin/activate && uv sync`
  -  Start server: `cd backend && uv run uvicorn app.main:app --reload --port 8000`
  -  Run tests: `cd backend && uv run pytest`
  -  Quick validation: `cd backend && uv run python quick_validate.py`
  -  Lint/Format: `cd backend && uv run ruff check . && uv run ruff format .`

### Frontend (Next.js)

  -  Start dev server: `cd frontend && npm run dev`
  -  Run tests: `cd frontend && npm test`
  -  Build: `cd frontend && npm run build`
  -  Lint: `cd frontend && npm run lint`
  -  Type check: `cd frontend && npm run type-check`

### Testing

  -  Backend tests are in `backend/tests/`
  -  Frontend tests are in `frontend/src/__tests__/`
  -  Use `pytest` for backend, Jest for frontend
  -  Always run tests after making changes
  -  Maintain 80%+ test coverage for new features

## Key Features

  -  Book creation and metadata management
  -  Chapter editing with rich text editor
  -  Table of contents generation
  -  Question generation system
  -  User authentication with Clerk
  -  File upload for book covers

## Current Implementation Status
### ✅ Completed Features

  -  User authentication (Clerk integration)
  -  Book CRUD operations with metadata
  -  TOC generation with AI wizard
  -  Chapter tabs interface (vertical layout)
  -  Question-based content creation system
  -  Basic test infrastructure

### 🚧 In Progress (High Priority)

  -  Rich Text Editor - Chapter content editing capability
  -  AI Draft Generation - Connect AI service for Q&A to narrative
  -  Voice Input Integration - Production speech-to-text service
  -  Mock Service Replacement - Real transcription and file storage

### 📋 Planned Features

  -  Export functionality (PDF/DOCX)
  -  Collaborative editing
  -  Advanced AI features
  -  Mobile companion app

## Implementation Priorities
### Sprint 1-2: MVP Completion

Focus on completing the core authoring workflow:

    1. Implement rich text editor (TipTap recommended)
    2. Complete AI draft generation integration
    3. Replace mock services with production implementations

### Sprint 3-4: Enhanced UX

Polish and improve reliability:

    1. Voice input integration across all text areas
    2. Basic export functionality
    3. Comprehensive error handling

### Sprint 5: Production Ready

Security and performance:

    1. Security hardening and audit
    2. Performance optimization
    3. Production infrastructure setup

## Development Guidelines
### Code Quality Standards

  -  Write clean, self-documenting code
  -  Follow existing patterns and conventions
  -  Implement proper error handling
  -  Add comprehensive logging
  -  Maintain backward compatibility

### Testing Requirements

  -  Unit tests: 80% minimum coverage
  -  Integration tests for critical flows
  -  E2E tests for happy paths
  -  Performance benchmarks for new features
  -  Security testing for sensitive operations

### Security Considerations

  -  Always validate and sanitize user input
  -  Use proper authentication checks
  -  Implement rate limiting for expensive operations
  -  Encrypt sensitive data
  -  Follow OWASP guidelines

### Performance Guidelines

  -  Optimize database queries
  -  Implement proper caching strategies
  -  Use lazy loading where appropriate
  -  Monitor bundle sizes
  -  Profile and optimize bottlenecks

## Important Notes

  -  Always run linting and type checking before committing
  -  Follow existing code conventions in each directory
  -  Check documentation in docs/ for specific feature guides
  -  Review IMPLEMENTATION_PLAN.md for detailed sprint planning
  -  Test coverage must meet 80% threshold before merging

## SPARC Development Commands

### Core SPARC Commands
- `./claude-flow sparc modes`: List all available SPARC development modes
- `./claude-flow sparc run <mode> "<task>"`: Execute specific SPARC mode for a task
- `./claude-flow sparc tdd "<feature>"`: Run complete TDD workflow using SPARC methodology
- `./claude-flow sparc info <mode>`: Get detailed information about a specific mode

### Standard Build Commands for the Frontend, /frontend
- `npm run build`: Build the project
- `npm run test`: Run the test suite
- `npm run lint`: Run linter and format checks
- `npm run typecheck`: Run TypeScript type checking

### Standard Build Commands for the Backend, /backend
- `cd backend && uv venv && source .venv/bin/activate && uv run uvicorn app.main:app --port 8000 --reload`: Run the backend server
- `uv run pytest`: Run the test bed
- `uv add <packagename>`: Add a dependency
- `uv sync`: Build dependency file
- `uv lock`" Lock dependency file

## SPARC Methodology Workflow

### 1. Specification Phase
```bash
# Create detailed specifications and requirements
./claude-flow sparc run spec-pseudocode "Define user authentication requirements"
```
- Define clear functional requirements
- Document edge cases and constraints
- Create user stories and acceptance criteria
- Establish non-functional requirements

### 2. Pseudocode Phase
```bash
# Develop algorithmic logic and data flows
./claude-flow sparc run spec-pseudocode "Create authentication flow pseudocode"
```
- Break down complex logic into steps
- Define data structures and interfaces
- Plan error handling and edge cases
- Create modular, testable components

### 3. Architecture Phase
```bash
# Design system architecture and component structure
./claude-flow sparc run architect "Design authentication service architecture"
```
- Create system diagrams and component relationships
- Define API contracts and interfaces
- Plan database schemas and data flows
- Establish security and scalability patterns

### 4. Refinement Phase (TDD Implementation)
```bash
# Execute Test-Driven Development cycle
./claude-flow sparc tdd "implement user authentication system"
```

**TDD Cycle:**
1. **Red**: Write failing tests first
2. **Green**: Implement minimal code to pass tests
3. **Refactor**: Optimize and clean up code
4. **Repeat**: Continue until feature is complete

### 5. Completion Phase
```bash
# Integration, documentation, and validation
./claude-flow sparc run integration "integrate authentication with user management"
```
- Integrate all components
- Perform end-to-end testing
- Create comprehensive documentation
- Validate against original requirements

## SPARC Mode Reference

### Development Modes
- **`architect`**: System design and architecture planning
- **`code`**: Clean, modular code implementation
- **`tdd`**: Test-driven development and testing
- **`spec-pseudocode`**: Requirements and algorithmic planning
- **`integration`**: System integration and coordination

### Quality Assurance Modes
- **`debug`**: Troubleshooting and bug resolution
- **`security-review`**: Security analysis and vulnerability assessment
- **`refinement-optimization-mode`**: Performance optimization and refactoring

### Support Modes
- **`docs-writer`**: Documentation creation and maintenance
- **`devops`**: Deployment and infrastructure management
- **`mcp`**: External service integration
- **`swarm`**: Multi-agent coordination for complex tasks

## Claude Code Slash Commands

Claude Code slash commands are available in `.claude/commands/`:

### Project Commands
- `/sparc`: Execute SPARC methodology workflows
- `/sparc-<mode>`: Run specific SPARC mode (e.g., /sparc-architect)
- `/claude-flow-help`: Show all Claude-Flow commands
- `/claude-flow-memory`: Interact with memory system
- `/claude-flow-swarm`: Coordinate multi-agent swarms

### Using Slash Commands
1. Type `/` in Claude Code to see available commands
2. Select a command or type its name
3. Commands are context-aware and project-specific
4. Custom commands can be added to `.claude/commands/`

## Code Style and Best Practices

### SPARC Development Principles
- **Modular Design**: Keep files under 500 lines, break into logical components
- **Environment Safety**: Never hardcode secrets or environment-specific values
- **Test-First**: Always write tests before implementation (Red-Green-Refactor)
- **Clean Architecture**: Separate concerns, use dependency injection
- **Documentation**: Maintain clear, up-to-date documentation

### Coding Standards
- Use TypeScript for type safety and better tooling
- Follow consistent naming conventions (camelCase for variables, PascalCase for classes)
- Implement proper error handling and logging
- Use async/await for asynchronous operations
- Prefer composition over inheritance

### Memory and State Management
- Use claude-flow memory system for persistent state across sessions
- Store progress and findings using namespaced keys
- Query previous work before starting new tasks
- Export/import memory for backup and sharing

## SPARC Memory Integration

### Memory Commands for SPARC Development
```bash
# Store project specifications
./claude-flow memory store spec_auth "User authentication requirements and constraints"

# Store architectural decisions
./claude-flow memory store arch_decisions "Database schema and API design choices"

# Store test results and coverage
./claude-flow memory store test_coverage "Authentication module: 95% coverage, all tests passing"

# Query previous work
./claude-flow memory query auth_implementation

# Export project memory
./claude-flow memory export project_backup.json
```

### Memory Namespaces
- **`spec`**: Requirements and specifications
- **`arch`**: Architecture and design decisions
- **`impl`**: Implementation notes and code patterns
- **`test`**: Test results and coverage reports
- **`debug`**: Bug reports and resolution notes

## Workflow Examples

### Feature Development Workflow
```bash
# 1. Start with specification
./claude-flow sparc run spec-pseudocode "User profile management feature"

# 2. Design architecture
./claude-flow sparc run architect "Profile service architecture with data validation"

# 3. Implement with TDD
./claude-flow sparc tdd "user profile CRUD operations"

# 4. Security review
./claude-flow sparc run security-review "profile data access and validation"

# 5. Integration testing
./claude-flow sparc run integration "profile service with authentication system"

# 6. Documentation
./claude-flow sparc run docs-writer "profile service API documentation"
```

### Bug Fix Workflow
```bash
# 1. Debug and analyze
./claude-flow sparc run debug "authentication token expiration issue"

# 2. Write regression tests
./claude-flow sparc run tdd "token refresh mechanism tests"

# 3. Implement fix
./claude-flow sparc run code "fix token refresh in authentication service"

# 4. Security review
./claude-flow sparc run security-review "token handling security implications"
```

## Configuration Files

### Claude Code Integration
- **`.claude/commands/`**: Claude Code slash commands for all SPARC modes
- **`.claude/logs/`**: Conversation and session logs

### SPARC Configuration
- **`.roomodes`**: SPARC mode definitions and configurations (auto-generated)
- **`.roo/`**: SPARC templates and workflows (auto-generated)

### Claude-Flow Configuration
- **`memory/`**: Persistent memory and session data
- **`coordination/`**: Multi-agent coordination settings
- **`CLAUDE.md`**: Project instructions for Claude Code

## Git Workflow Integration

### Commit Strategy with SPARC
- **Specification commits**: After completing requirements analysis
- **Architecture commits**: After design phase completion
- **TDD commits**: After each Red-Green-Refactor cycle
- **Integration commits**: After successful component integration
- **Documentation commits**: After completing documentation updates

### Branch Strategy
- **`feature/sparc-<feature-name>`**: Feature development with SPARC methodology
- **`hotfix/sparc-<issue>`**: Bug fixes using SPARC debugging workflow
- **`refactor/sparc-<component>`**: Refactoring using optimization mode

## Troubleshooting

### Common SPARC Issues
- **Mode not found**: Check `.roomodes` file exists and is valid JSON
- **Memory persistence**: Ensure `memory/` directory has write permissions
- **Tool access**: Verify required tools are available for the selected mode
- **Namespace conflicts**: Use unique memory namespaces for different features

### Debug Commands
```bash
# Check SPARC configuration
./claude-flow sparc modes

# Verify memory system
./claude-flow memory stats

# Check system status
./claude-flow status

# View detailed mode information
./claude-flow sparc info <mode-name>
```

## Project Architecture

This SPARC-enabled project follows a systematic development approach:
- **Clear separation of concerns** through modular design
- **Test-driven development** ensuring reliability and maintainability
- **Iterative refinement** for continuous improvement
- **Comprehensive documentation** for team collaboration
- **AI-assisted development** through specialized SPARC modes

## Important Notes

- Always run tests before committing (`npm run test` or `uv run pytest`)
- Use SPARC memory system to maintain context across sessions
- Follow the Red-Green-Refactor cycle during TDD phases
- Document architectural decisions in memory for future reference
- Regular security reviews for any authentication or data handling code
- Claude Code slash commands provide quick access to SPARC modes

For more information about SPARC methodology, see: https://github.com/ruvnet/claude-code-flow/docs/sparc.md
