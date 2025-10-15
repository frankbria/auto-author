# Component Documentation

## Loading State Components

**Location**: `frontend/src/components/loading/`

**Description**: Comprehensive loading indicators with progress feedback for async operations.

**Components**:
1. **LoadingStateManager** - Full-featured loading indicator with progress, time estimates, and cancellation
2. **ProgressIndicator** - Visual progress display with percentage and count tracking

**Key Features**:
- Progress bars with smooth transitions
- Time estimates with countdown (uses time budgets from `lib/loading/timeEstimator.ts`)
- Cancellable operations (optional)
- Accessible ARIA labels (WCAG 2.1 compliant)
- Graceful transitions (200ms delay to avoid flicker)
- Inline and full-screen variants
- Compact variant for space-constrained UI

**Usage Example - LoadingStateManager**:
```tsx
import { LoadingStateManager } from '@/components/loading';
import { createProgressTracker } from '@/lib/loading';

// Create progress tracker for time estimates
const getProgress = useMemo(() =>
  createProgressTracker('toc.generation'),
  []
);
const { progress, estimatedTimeRemaining } = getProgress();

<LoadingStateManager
  isLoading={isGenerating}
  operation="Generating Table of Contents"
  progress={progress}
  estimatedTime={estimatedTimeRemaining}
  message="Analyzing your summary and generating chapter structure..."
  onCancel={() => setIsGenerating(false)}
  inline={false}
/>
```

**Usage Example - ProgressIndicator**:
```tsx
import { ProgressIndicator } from '@/components/loading';

<ProgressIndicator
  current={5}
  total={10}
  unit="chapters"
  showPercentage={true}
  message="Processing chapters..."
  size="default"
/>

// Compact variant for space-constrained UI
<ProgressIndicator.Compact
  current={3}
  total={10}
  unit="items"
/>
```

**Time Estimation**:
The `timeEstimator` utility provides intelligent time estimates based on:
- Operation type (TOC generation, export, draft generation, etc.)
- Data size (word count, chapter count)
- Historical performance data

```tsx
import { estimateOperationTime, formatTime } from '@/lib/loading';

// Get time estimate
const estimate = estimateOperationTime('export.pdf', {
  wordCount: 50000,
  chapterCount: 15
});
// Returns: { min: 5000, max: 60000, average: 35000 }

// Format for display
const timeString = formatTime(estimate.average);
// Returns: "35s" or "1m 15s"
```

**Integrated Operations**:
- **TOC Generation**: `components/toc/TocGenerating.tsx` - 10-30 seconds
- **Export Operations**: `app/dashboard/books/[bookId]/export/page.tsx` - 5-20 seconds
- **Draft Generation**: `components/chapters/DraftGenerator.tsx` - 10-30 seconds

**Test Coverage**: 100% (53 tests, 100% pass rate)

**Accessibility**: All components include proper ARIA labels, roles, and live regions for screen reader support

---

## Book Deletion UI

**Location**: `frontend/src/components/books/DeleteBookModal.tsx`

**Description**: A comprehensive deletion confirmation modal that prevents accidental book deletion through a type-to-confirm pattern.

**Key Features**:
- **Type-to-Confirm**: Users must type the exact book title (case-sensitive) to enable deletion
- **Data Loss Warnings**: Displays comprehensive warnings about what will be permanently deleted
- **Book Statistics**: Shows chapter count and word count before deletion
- **Loading States**: Disables all controls during deletion operation
- **Prevention Mechanisms**: Blocks modal closure during deletion, prevents escape key and outside clicks
- **Accessibility**: Full ARIA label support, keyboard navigation, autofocus on input field

**Usage Example**:
```tsx
import { DeleteBookModal } from '@/components/books';

<DeleteBookModal
  isOpen={showDeleteDialog}
  onOpenChange={setShowDeleteDialog}
  bookTitle={book.title}
  bookStats={{
    chapterCount: book.chapters,
    wordCount: book.word_count ?? 0,  // Optional field with null coalescing
  }}
  onConfirm={handleDeleteBook}
  isDeleting={isDeleting}
/>
```

**Props**:
- `isOpen: boolean` - Controls modal visibility
- `onOpenChange: (open: boolean) => void` - Callback when modal open state changes
- `bookTitle: string` - Title of book to delete (used for confirmation)
- `bookStats?: { chapterCount: number; wordCount: number }` - Optional statistics to display
  - Note: `word_count` field may be null/undefined on Book objects; use null coalescing (`?? 0`)
- `onConfirm: () => void | Promise<void>` - Callback when user confirms deletion
- `isDeleting?: boolean` - Loading state during deletion

**Test Coverage**: 86.2% overall, 91.66% for DeleteBookModal.tsx (29 tests, 100% pass rate)

**Integration Points**:
- Dashboard book cards (BookCard.tsx) - Delete button with trash icon
- Book detail page (future enhancement)

**Error Handling**:
- Parent component handles deletion errors
- Toast notifications for success/failure
- Network error retry via parent logic
