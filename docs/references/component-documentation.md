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

---

## Icon Library: Hugeicons

**Location**: Used throughout the application via `@hugeicons/react` package

**Overview**: The application uses Hugeicons instead of lucide-react for consistent iconography aligned with the nova template design system.

**Common Icon Mappings** (from Lucide to Hugeicons migration):
- `FileText` → `FileEditIcon`
- `Clock` → `Loading03Icon`
- `CheckCircle` → `CheckmarkCircle01Icon`
- `BookOpen` → `Book02Icon`
- `ChevronLeft` → `ArrowLeft01Icon`
- `ChevronRight` → `ArrowRight01Icon`
- `Check` → `Tick02Icon`
- `SkipForward` → `FastForwardIcon`
- `Menu` → `Menu01Icon`
- `AlertCircle` → `Alert02Icon`
- `AlertTriangle` → `Alert03Icon`

**Nova Template Patterns**:
- Consistent 24px default size
- Thin stroke weight (1.5px) for clarity
- Integrated with gray color theme
- ARIA labels for accessibility

**Usage Example**:
```tsx
import { CheckmarkCircle01Icon, ArrowRight01Icon } from "@hugeicons/react";

<CheckmarkCircle01Icon className="w-5 h-5 text-primary" />
<ArrowRight01Icon className="w-6 h-6 text-gray-400" />
```

---

## Nova Template Design System

**Overview**: The application implements the nova template design system with gray color palette, enhanced animations, and improved accessibility.

**Key Features**:

### 1. Gray Color Theme
- Primary focus on gray tones (not zinc)
- Consistent palette: `gray-50` through `gray-900`
- Better semantic meaning than zinc colors
- Dark mode optimized

**Color Tokens**:
```css
--color-border: theme color for borders
--color-input: input field background
--color-ring: focus ring color
--color-background: main background
--color-foreground: main text
primary: rgb(79, 70, 229) - Primary brand color
secondary: rgb(30, 41, 59) - Secondary neutral
destructive: rgb(239, 68, 68) - Error/danger states
muted: rgb(39, 39, 42) - Disabled/inactive states
accent: rgb(39, 39, 42) - Hover/focus states
```

### 2. Component Data-Slots
All interactive components include `data-slot` attributes for identification:
- `data-slot="spinner"` - Loading indicators
- `data-slot="avatar"` - Avatar components
- `data-slot="status-indicator"` - Status displays
- `data-slot="question-progress"` - Progress tracking
- `data-slot="delete-modal"` - Deletion dialogs

### 3. Transition Animations
- All interactive elements use `transition-all` for smooth state changes
- Consistent animation timing across components
- Enhanced visual feedback

**Example**:
```tsx
<div className="transition-all duration-300 hover:bg-gray-800">
  {/* Content */}
</div>
```

### 4. Enhanced Focus States
- All focusable elements use `focus-visible:ring-[3px]`
- Improved keyboard navigation visibility
- WCAG 2.1 Level AA compliant

**Example**:
```tsx
<button className="focus-visible:ring-[3px] focus-visible:ring-primary">
  Action
</button>
```

### 5. Nunito Sans Font Family
- Primary font for all text
- Defined via CSS variable: `var(--font-nunito-sans)`
- System fonts as fallback

**Font Loading**:
Located in `/frontend/src/app/layout.tsx`:
```tsx
import { Nunito_Sans } from "next/font/google";

const nunitoSans = Nunito_Sans({
  subsets: ["latin"],
  variable: "--font-nunito-sans",
});
```

---

## Accessibility Standards (WCAG 2.1 Level AA)

**Nova Template Compliance**:
- Color contrast ratios meet WCAG AA standards (4.5:1 minimum)
- Focus indicators clearly visible (3px ring)
- ARIA labels on all icon buttons
- Keyboard navigation fully supported
- Screen reader compatible

**Common Accessibility Patterns**:

1. **Icon-Only Buttons**:
```tsx
<button aria-label="Delete book" className="focus-visible:ring-[3px]">
  <TrashIcon className="w-5 h-5" />
</button>
```

2. **Loading States**:
```tsx
<div role="status" aria-label="Loading content">
  <LoadingSpinner />
</div>
```

3. **Status Indicators**:
```tsx
<div role="status" aria-live="polite">
  Saved successfully
</div>
```
