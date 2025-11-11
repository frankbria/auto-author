# Documentation Management Guidelines - Summary

**Added**: 2025-10-12
**Location**: CLAUDE.md (lines 12-229)
**Purpose**: Prevent document proliferation and maintain single source of truth

---

## What Was Added

A comprehensive "Documentation Management" section with 218 lines of guidelines, rules, and examples to prevent the creation of unnecessary documentation files.

## Key Components

### 1. Document Hierarchy (Single Source of Truth)
- Clear categorization: Active → Detailed → Historical
- Emphasizes IMPLEMENTATION_PLAN.md as master document
- Lists all document types with their purposes

### 2. Decision Tree (7 Decision Points)
Visual ASCII tree answering "Where should information go?":
```
- Development standards → CLAUDE.md
- Sprint work → CURRENT_SPRINT.md
- Implementation plans → IMPLEMENTATION_PLAN.md
- Detailed analysis (>500 lines) → claudedocs/
- Completed work → archive/
- Tasks/ADRs → Backlog system
- Default fallback → IMPLEMENTATION_PLAN.md
```

### 3. Document Type Reference Table
8 document types with location, purpose, and update frequency

### 4. Rules for Creating New Documents
4-question checklist:
1. Does this belong in existing document?
2. Is this >500 lines detailed analysis?
3. Will this be updated regularly?
4. Does this overlap with existing content?

### 5. AI Agent Instructions (CRITICAL)
6 explicit rules for AI agents:
1. **NEVER** create planning docs without approval
2. **ALWAYS** check existing documents first
3. **DEFAULT** to IMPLEMENTATION_PLAN.md
4. **USE** Backlog for tasks/ADRs
5. **ASK** before creating claudedocs/ files
6. **CONSOLIDATE** when duplicates found

### 6. Document Lifecycle Management
- **When to Archive**: 5 specific criteria
- **When to Delete**: 3 rare scenarios (requires approval)
- Archive process with bash commands

### 7. Correct vs Incorrect Behavior
5 concrete examples showing:
- ✅ Update existing document (feature tracking)
- ❌ Create new document (feature tracking)
- ✅ Detailed analysis (800-line audit)
- ❌ Small update as new file (50-line status)
- ✅ Consolidation (merge 3 overlapping files)

### 8. Documentation Quality Standards
5 requirements: Accuracy, Completeness, Consistency, Traceability, Maintainability

### 9. Verification Checklist
7 items AI agents must complete before finishing documentation tasks

---

## Why This Prevents Document Proliferation

### Prevention Mechanisms

1. **Explicit Rules**: "NEVER create planning docs without approval"
2. **Default Behavior**: "When unsure → IMPLEMENTATION_PLAN.md"
3. **Decision Tree**: Visual guide prevents wrong choices
4. **Size Threshold**: Only >500 lines justifies claudedocs/
5. **Checklist Enforcement**: 7-item verification before completion
6. **Real Examples**: Shows actual mistakes to avoid

### Detection Mechanisms

```bash
# AI agents must run these before creating documents:
ls -la *.md
ls -la claudedocs/*.md
ls -la archive/*.md
```

### Consolidation Process

When duplicates found:
1. Analyze content overlap
2. Propose consolidation plan to user
3. Merge into master document
4. Archive obsolete documents
5. Update all references

---

## Usage for AI Agents

### Before Creating ANY Document

**Step 1**: Check decision tree (CLAUDE.md lines 31-56)
**Step 2**: Run verification commands (lines 101-106)
**Step 3**: Answer 4-question checklist (lines 75-90)
**Step 4**: If unsure → default to IMPLEMENTATION_PLAN.md (line 108)
**Step 5**: If creating claudedocs/ → ask for approval (lines 118-122)

### Before Completing Documentation Task

**Verification Checklist** (lines 219-229):
- [ ] Checked all existing documents
- [ ] Updated master documents
- [ ] No new documents without justification
- [ ] All cross-references updated
- [ ] Backlog system used for tasks/ADRs
- [ ] Archive directory properly maintained
- [ ] Document hierarchy reflects structure

---

## Quick Reference

### Information Placement Guide

| Content Type | Location | Why |
|--------------|----------|-----|
| Development standards | CLAUDE.md | Rarely changes, applies to all code |
| Feature/sprint plans | IMPLEMENTATION_PLAN.md | Master roadmap, single source of truth |
| Current work/progress | CURRENT_SPRINT.md | Updated daily, temporary state |
| Detailed analysis (>500 lines) | claudedocs/ | Too large for master plan |
| Tasks and ADRs | Backlog system | Proper task management tool |
| Completed/obsolete | archive/ | Historical reference only |

### Default Behavior for AI Agents

**When in doubt**: Update IMPLEMENTATION_PLAN.md

**Never do this without approval**:
- Create TODO.md, PLAN.md, ROADMAP.md, TASKS.md
- Create any planning document in project root
- Create duplicate information

**Always do this**:
- Check existing documents first
- Use decision tree for placement
- Ask before creating claudedocs/ files
- Consolidate when duplicates found

---

## Expected Impact

### Before Guidelines
- Risk of multiple overlapping documents
- No clear rules for AI agents
- Ad-hoc document creation
- Confusion about information placement

### After Guidelines
- Clear decision tree for every scenario
- Explicit prevention rules for AI agents
- Size threshold for new documents (>500 lines)
- Verification checklist enforcement
- Default behavior when unsure

### Measured Success
- **No new planning documents** in project root (except approved cases)
- **Consolidation** when duplicates found
- **Backlog usage** for tasks and ADRs
- **Archive maintenance** for obsolete content

---

## Maintenance

### Guidelines Update Frequency
- **Rarely**: Core structure and rules stable
- **As needed**: Add examples when new patterns emerge
- **Review**: During document consolidations

### Monitoring
Watch for:
- New .md files in project root
- Duplicate information across documents
- Outdated information in archive/
- Missing cross-references

### Enforcement
- AI agent verification checklist (required)
- User approval for document creation
- Git commit message references to guidelines
- Regular structure audits

---

## Related Documents

- **IMPLEMENTATION_PLAN.md** - Master implementation roadmap
- **CURRENT_SPRINT.md** - Active sprint tasks
- **CLAUDE.md** - Development guidelines (contains these rules)
- **CONSOLIDATION_SUMMARY.md** - Previous consolidation work
- **archive/README.md** - Archive policy documentation

---

**Status**: ✅ Active and Enforced
**Last Updated**: 2025-10-12
**Next Review**: During next documentation consolidation (if needed)
