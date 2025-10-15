# Documentation Management

## Document Hierarchy (Single Source of Truth)

**Active Documents** (always current):
- **IMPLEMENTATION_PLAN.md** - Master implementation roadmap (single source of truth)
- **CURRENT_SPRINT.md** - Current sprint tasks and daily progress
- **CLAUDE.md** - Development guidelines and standards

**Detailed Plans** (reference as needed):
- `claudedocs/QUALITY_MONITORING_IMPLEMENTATION_PLAN.md` - Quality monitoring implementation
- `claudedocs/loading_states_audit_report.md` - Loading state gap analysis

**Historical Reference** (archived):
- `archive/TODO.md` - Legacy task tracking
- `archive/PHASE1_IMPLEMENTATION_PLAN.md` - Phase 1 detailed notes
- `archive/UI_IMPROVEMENTS_TODO.md` - Expert panel requirements
- `archive/KEYBOARD_NAVIGATION_ACTION_PLAN.md` - Accessibility action plan

## Where Should Information Go? Decision Tree

```
New information to document?
│
├─ Is it a development standard or guideline?
│  └─ YES → Update CLAUDE.md
│
├─ Is it current sprint work or daily progress?
│  └─ YES → Update CURRENT_SPRINT.md
│
├─ Is it a feature/sprint implementation plan?
│  └─ YES → Update IMPLEMENTATION_PLAN.md (master plan)
│
├─ Is it detailed technical analysis (>500 lines)?
│  ├─ YES → Create in claudedocs/ with descriptive name
│  └─ AND → Reference from IMPLEMENTATION_PLAN.md
│
├─ Is it completed/obsolete planning info?
│  └─ YES → Move to archive/ directory
│
├─ Is it a task or ADR for Backlog?
│  └─ YES → Use `backlog task create` or `backlog doc create`
│
└─ NOT SURE? → Default to updating IMPLEMENTATION_PLAN.md
```

## Document Type Guidelines

| Document Type | Location | Purpose | Update Frequency |
|--------------|----------|---------|------------------|
| **Development Standards** | CLAUDE.md | Code quality, testing, git workflow, security | Rarely (major policy changes) |
| **Implementation Roadmap** | IMPLEMENTATION_PLAN.md | Sprint plans, feature specs, timelines | Weekly (sprint planning) |
| **Current Work** | CURRENT_SPRINT.md | Active tasks, daily progress, blockers | Daily (progress updates) |
| **Technical Analysis** | claudedocs/*.md | Detailed audits, gap analysis, designs | As needed (specific analyses) |
| **Architecture Decisions** | Backlog ADRs | Technical choices, trade-offs | Per decision |
| **Historical Plans** | archive/*.md | Completed/obsolete planning docs | Never (read-only) |
| **API Documentation** | Code comments | Endpoint specs, schemas, examples | Per code change |
| **Component Docs** | CLAUDE.md | Reusable component usage patterns | Per component addition |

## Rules for Creating New Documents

**BEFORE creating any new document, answer these questions:**

1. **Does this information belong in an existing document?**
   - Check IMPLEMENTATION_PLAN.md first (90% of planning goes here)
   - Check CURRENT_SPRINT.md for active work
   - Check CLAUDE.md for standards/guidelines

2. **Is this document >500 lines of detailed analysis?**
   - NO → Add to IMPLEMENTATION_PLAN.md or CURRENT_SPRINT.md
   - YES → Consider claudedocs/ but get justification first

3. **Will this document be updated regularly?**
   - YES → Use CURRENT_SPRINT.md (daily) or IMPLEMENTATION_PLAN.md (weekly)
   - NO → Probably doesn't need a separate document

4. **Does this overlap with existing content?**
   - YES → Update existing document, DO NOT create duplicate
   - NO → Proceed with creation (but verify with decision tree)

## AI Agent Instructions: Document Creation Prevention

**CRITICAL RULES FOR AI AGENTS:**

1. **NEVER create a new planning document without explicit user approval**
   - This includes: TODO.md, PLAN.md, ROADMAP.md, TASKS.md, etc.
   - Exception: Files in claudedocs/ for detailed analysis (>500 lines)

2. **ALWAYS check existing documents first**
   ```bash
   # Before creating any document, run:
   ls -la *.md
   ls -la claudedocs/*.md
   ls -la archive/*.md
   ```

3. **DEFAULT to updating IMPLEMENTATION_PLAN.md**
   - When unsure where information goes → IMPLEMENTATION_PLAN.md
   - When planning features → IMPLEMENTATION_PLAN.md
   - When tracking progress → CURRENT_SPRINT.md (if active) or IMPLEMENTATION_PLAN.md

4. **USE Backlog for tasks and ADRs**
   - Task tracking → `backlog task create`
   - Architecture decisions → `backlog doc create "ADR: Title"`
   - NOT separate markdown files in project root

5. **ASK before creating claudedocs/ files**
   - Justify: "This analysis is >500 lines and references specific data"
   - Get user approval before proceeding
   - Always reference from IMPLEMENTATION_PLAN.md

6. **CONSOLIDATE when you find duplicates**
   - If multiple documents cover same topic → merge into master document
   - Move obsolete versions to archive/
   - Update references in other documents

## Document Lifecycle Management

### When to Archive Documents

Move documents to `archive/` when:
- ✅ All tasks completed and verified
- ✅ Sprint/phase finished and retrospective done
- ✅ Information no longer relevant to current work
- ✅ Superseded by newer planning document
- ✅ >30 days since last update AND not referenced

**Archive Process**:
```bash
# 1. Verify document is truly obsolete
grep -r "DOCUMENT_NAME" *.md claudedocs/*.md

# 2. Move to archive with descriptive name
mv DOCUMENT.md archive/DOCUMENT_$(date +%Y%m%d).md

# 3. Update references in active documents
# 4. Add note in IMPLEMENTATION_PLAN.md if historically significant
```

### When to Delete Documents (RARE)

Delete documents only when:
- ❌ Duplicate information with no unique content
- ❌ Incorrect/misleading information that was never implemented
- ❌ Test/scratch files accidentally committed

**Deletion requires explicit user approval.**

## Examples of Correct vs Incorrect Behavior

### ✅ CORRECT: Update Existing Document
```
Situation: User asks to track new feature implementation
AI Action:
1. Check IMPLEMENTATION_PLAN.md for relevant section
2. Update appropriate sprint section with feature details
3. Reference detailed specs if needed from claudedocs/
4. Update CURRENT_SPRINT.md with active tasks
```

### ❌ INCORRECT: Create New Document
```
Situation: User asks to track new feature implementation
AI Action: Creates "FEATURE_PLAN.md" in project root
Problem: Proliferates documents, creates duplicate information
Fix: Consolidate into IMPLEMENTATION_PLAN.md
```

### ✅ CORRECT: Detailed Analysis
```
Situation: 800-line security audit with specific vulnerability data
AI Action:
1. Ask user: "This analysis is extensive. Create claudedocs/security_audit_2024.md?"
2. Get approval
3. Create detailed document in claudedocs/
4. Add summary and reference to IMPLEMENTATION_PLAN.md
```

### ❌ INCORRECT: Small Update as New File
```
Situation: 50-line status update on current sprint
AI Action: Creates "STATUS_UPDATE.md"
Problem: Small updates don't need separate files
Fix: Add to CURRENT_SPRINT.md or IMPLEMENTATION_PLAN.md
```

### ✅ CORRECT: Consolidation
```
Situation: Discovers 3 files with overlapping TODOs
AI Action:
1. Analyze content overlap
2. Propose consolidation plan to user
3. Merge into IMPLEMENTATION_PLAN.md
4. Archive obsolete documents
5. Update all references
```

## Documentation Quality Standards

All documentation must meet these standards:

1. **Accuracy**: Information reflects current implementation state
2. **Completeness**: No TODOs or incomplete sections in active docs
3. **Consistency**: Terminology and formatting matches project standards
4. **Traceability**: Clear references between related documents
5. **Maintainability**: Easy to find, update, and understand

## Verification Checklist for AI Agents

Before completing any documentation task:

- [ ] Checked all existing documents for relevant content
- [ ] Updated master documents (IMPLEMENTATION_PLAN.md, CURRENT_SPRINT.md, CLAUDE.md)
- [ ] No new documents created without justification and approval
- [ ] All cross-references updated if documents moved/renamed
- [ ] Backlog system used for tasks and ADRs
- [ ] Archive directory contains only historical/completed content
- [ ] Document hierarchy reflects current project structure
