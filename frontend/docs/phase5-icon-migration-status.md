# Phase 5: Icon Migration Status

## Overview

**Migration Status**: IN PROGRESS
**Completed**: 3/32 files (9%)
**Remaining**: 29 files (91%)

This document tracks the progress of migrating from `lucide-react` to `@hugeicons/react` as part of the Nova template migration.

## Packages Installed

✅ `@hugeicons/react` v1.1.3
✅ `@hugeicons/core-free-icons` (4,655 icons available)

## Completed Files

### Book Components (3 files) ✅
- `/frontend/src/components/books/DeleteBookModal.tsx`
  - Migrated: `AlertTriangle` → `Alert02Icon`, `Loader2` → `Loading03Icon`
- `/frontend/src/components/BookCard.tsx`
  - Migrated: `Trash2` → `Delete02Icon`
- `/frontend/src/components/BookCreationWizard.tsx`
  - Migrated: `Loader2` → `Loading03Icon`

## Icon Mapping Reference

Complete mapping documented in `/frontend/docs/icon-migration-map.md`

### Most Frequently Used Icons (Top 10)
1. `AlertCircle` → `AlertCircleIcon` (8 occurrences)
2. `FileText` → `File01Icon` (6 occurrences)
3. `X` → `Cancel01Icon` (5 occurrences)
4. `RefreshCw` → `RefreshIcon` (5 occurrences)
5. `Clock` → `Clock01Icon` (5 occurrences)
6. `BookOpen` → `BookOpen01Icon` (5 occurrences)
7. `Sparkles` → `SparklesIcon` (4 occurrences)
8. `Loader2` → `Loading03Icon` (4 occurrences)
9. `Menu` → `Menu01Icon` (3 occurrences)
10. `CheckCircle` → `CheckmarkCircle01Icon` (3 occurrences)

## Remaining Files to Migrate (29 files)

### Page Components (3 files)
- [ ] `src/app/dashboard/page.tsx`
- [ ] `src/app/dashboard/books/[bookId]/chapters/[chapterId]/page.tsx`
- [ ] `src/app/error.tsx`

### TOC & Navigation Components (2 files)
- [ ] `src/components/toc/TocSidebar.tsx`
- [ ] `src/components/navigation/ChapterBreadcrumb.tsx`

### Export Components (2 files)
- [ ] `src/components/export/ExportProgressModal.tsx`
- [ ] `src/components/export/ExportOptionsModal.tsx`

### Error & Recovery Components (2 files)
- [ ] `src/components/errors/ErrorNotification.tsx`
- [ ] `src/components/recovery/DataRecoveryModal.tsx`

### Chapter Components (14 files)
- [ ] `src/components/chapters/EditorToolbar.tsx`
- [ ] `src/components/chapters/TiptapDemo.tsx`
- [ ] `src/components/chapters/TabOverflowMenu.tsx`
- [ ] `src/components/chapters/TabContextMenu.tsx`
- [ ] `src/components/chapters/TabBar.tsx`
- [ ] `src/components/chapters/DraftGenerator.tsx`
- [ ] `src/components/chapters/VoiceTextInput.tsx`
- [ ] `src/components/chapters/ChapterEditor.tsx`
- [ ] `src/components/chapters/MobileChapterTabs.tsx`
- [ ] `src/components/chapters/ChapterTab.tsx`

### Chapter Question Components (7 files)
- [ ] `src/components/chapters/questions/QuestionProgress.tsx`
- [ ] `src/components/chapters/questions/ChapterQuestions.tsx`
- [ ] `src/components/chapters/questions/DraftGenerationButton.tsx`
- [ ] `src/components/chapters/questions/QuestionContainer.tsx`
- [ ] `src/components/chapters/questions/QuestionGenerator.tsx`
- [ ] `src/components/chapters/questions/QuestionDisplay.tsx`
- [ ] `src/components/chapters/questions/QuestionNavigation.tsx`

### UI & Loading Components (3 files)
- [ ] `src/components/loading/LoadingStateManager.tsx`
- [ ] `src/components/ui/ChapterStatusIndicator.tsx`
- [ ] `src/components/examples/ai-error-handling-example.tsx`

## Migration Pattern

### Step 1: Update Import Statement

**OLD:**
```tsx
import { AlertCircle, Loader2, X } from 'lucide-react';
```

**NEW:**
```tsx
import { HugeiconsIcon } from '@hugeicons/react';
import { AlertCircleIcon, Loading03Icon, Cancel01Icon } from '@hugeicons/core-free-icons';
```

### Step 2: Replace Icon Usage

**Pattern A: Tailwind Classes (h-X w-X)**
```tsx
// OLD
<AlertCircle className="h-4 w-4" />

// NEW (h-4 = 16px, h-5 = 20px, h-6 = 24px)
<HugeiconsIcon icon={AlertCircleIcon} size={16} />
```

**Pattern B: Size Prop**
```tsx
// OLD
<Loader2 size={24} className="animate-spin" />

// NEW
<HugeiconsIcon icon={Loading03Icon} size={24} className="animate-spin" />
```

**Pattern C: With Additional Classes**
```tsx
// OLD
<X className="h-4 w-4 text-destructive hover:text-destructive/80" />

// NEW
<HugeiconsIcon
  icon={Cancel01Icon}
  size={16}
  className="text-destructive hover:text-destructive/80"
/>
```

**Pattern D: With Color Prop**
```tsx
// OLD
<AlertTriangle className="h-4 w-4 text-yellow-500" />

// NEW
<HugeiconsIcon
  icon={Alert02Icon}
  size={16}
  color="rgb(234 179 8)"  // or use className="text-yellow-500"
/>
```

### Tailwind Size to Pixel Conversion
- `h-3 w-3` → `size={12}`
- `h-4 w-4` → `size={16}`
- `h-5 w-5` → `size={20}`
- `h-6 w-6` → `size={24}`
- `h-8 w-8` → `size={32}`

## Batch Migration Approach

### Recommended Order:
1. **UI Components** (3 files) - Fewest dependencies
2. **Page Components** (3 files) - High visibility
3. **Chapter Question Components** (7 files) - Related functionality
4. **Chapter Editor Components** (7 files) - Core functionality
5. **Export/Error/Recovery** (6 files) - Support components
6. **TOC/Navigation** (2 files) - Navigation
7. **Examples** (1 file) - Low priority

### For Each File:
1. Read the file with Read tool
2. Identify all lucide-react icons used
3. Look up mapping in `/frontend/docs/icon-migration-map.md`
4. Use Edit tool to:
   - Replace import statement
   - Replace each icon usage (check all patterns)
5. Mark file as complete in this document

## Testing Checklist

After migration, verify:

- [ ] No lucide-react imports remain: `grep -r "from 'lucide-react'" src --include="*.tsx" --include="*.ts"`
- [ ] All icons render correctly (visual check)
- [ ] Icon sizes match original appearance
- [ ] Icon colors are correct
- [ ] Animations still work (e.g., `animate-spin` on Loading03Icon)
- [ ] Hover states and interactions work
- [ ] Accessibility (aria-labels, etc.) preserved
- [ ] TypeScript compiles without errors
- [ ] No console errors in browser

## Final Cleanup

Once all files are migrated:

1. Remove lucide-react from package.json:
   ```bash
   npm uninstall lucide-react
   ```

2. Verify no imports remain:
   ```bash
   grep -r "lucide-react" src
   ```

3. Run tests:
   ```bash
   npm test
   npm run typecheck
   npm run lint
   ```

4. Visual regression testing in browser

## Notes

- Hugeicons uses a wrapper component pattern (`HugeiconsIcon`) unlike lucide-react's direct component imports
- The `size` prop uses pixels, not Tailwind classes
- Some icons have numbered variants (01, 02, etc.) - use 01 by default unless specific variant needed
- Multicolor icons (Bulk, Duotone, Twotone) support `primaryColor` and `secondaryColor` props
- Default stroke width is 1.5, can be adjusted with `strokeWidth` prop

## Icon Verification

If an icon doesn't look right, check:
1. Icon mapping is correct in `/frontend/docs/icon-migration-map.md`
2. Icon exists in `@hugeicons/core-free-icons` (not Pro-only)
3. Size conversion is accurate (Tailwind → pixels)
4. Any custom styles/colors are preserved

Run this to check all available icons:
```bash
grep "declare const" node_modules/@hugeicons/core-free-icons/dist/types/index.d.ts | awk '{print $3}' | sort
```

## Resources

- **Icon Mapping**: `/frontend/docs/icon-migration-map.md`
- **Hugeicons Docs**: https://hugeicons.com/docs
- **Hugeicons React**: https://www.npmjs.com/package/@hugeicons/react
- **Free Icons**: https://www.npmjs.com/package/@hugeicons/core-free-icons
- **Icon Browser**: https://hugeicons.com/icons

## Progress Tracking

**Last Updated**: 2025-12-23

| Category | Files | Completed | Remaining |
|----------|-------|-----------|-----------|
| Book Components | 3 | 3 | 0 |
| Page Components | 3 | 0 | 3 |
| TOC/Navigation | 2 | 0 | 2 |
| Export Components | 2 | 0 | 2 |
| Error/Recovery | 2 | 0 | 2 |
| Chapter Components | 14 | 0 | 14 |
| UI/Loading | 3 | 0 | 3 |
| Examples | 1 | 0 | 1 |
| **TOTAL** | **32** | **3** | **29** |

**Completion**: 9% (3/32 files)
