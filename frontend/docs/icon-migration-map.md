# Icon Migration Map: lucide-react → @hugeicons/react

## Migration Overview

This document maps lucide-react icons to their @hugeicons/react equivalents for the Nova template migration.

**Packages:**
- **Old:** `lucide-react` (direct component imports)
- **New:** `@hugeicons/react` + `@hugeicons/core-free-icons` (icon data + wrapper component)

**Usage Pattern Change:**

```tsx
// OLD (lucide-react)
import { Search, Trash2 } from 'lucide-react';
<Search className="h-4 w-4" />
<Trash2 size={16} color="red" />

// NEW (@hugeicons/react)
import { HugeiconsIcon } from '@hugeicons/react';
import { SearchIcon, Delete02Icon } from '@hugeicons/core-free-icons';
<HugeiconsIcon icon={SearchIcon} size={16} className="text-current" />
<HugeiconsIcon icon={Delete02Icon} size={16} color="red" />
```

## Icon Mapping Table

| Lucide Icon | Hugeicons Icon | Notes |
|------------|----------------|-------|
| `AlertCircle` | `AlertCircleIcon` | Exact match (verified) |
| `AlertTriangle` | `Alert02Icon` | Triangle variant (verified) |
| `ArrowLeft` | `ArrowLeft01Icon` | Use 01 variant (verified) |
| `Bold` | `TextBoldIcon` | Text formatting (verified) |
| `Book` | `Book02Icon` | Book variant (verified) |
| `BookIcon` | `Book02Icon` | Same as Book (verified) |
| `BookOpen` | `BookOpen01Icon` | Open book variant (verified) |
| `Brain` | `BrainIcon` | Brain icon (verified) |
| `Check` | `CheckmarkCircle01Icon` | Check/checkmark (verified) |
| `CheckCircle` | `CheckmarkCircle01Icon` | Circle with check (verified) |
| `CheckCircle2` | `CheckmarkCircle02Icon` | Alternative circle check (verified) |
| `ChevronDown` | `ArrowDown01Icon` | Down chevron/arrow (verified) |
| `ChevronLeft` | `ArrowLeft01Icon` | Left chevron/arrow (verified) |
| `ChevronRight` | `ArrowRight01Icon` | Right chevron/arrow (verified) |
| `ChevronUp` | `ArrowUp01Icon` | Up chevron/arrow (verified) |
| `Circle` | `CircleIcon` | Basic circle (verified) |
| `Clock` | `Clock01Icon` | Clock icon (verified) |
| `Copy` | `Copy01Icon` | Copy/duplicate (verified) |
| `Database` | `Database01Icon` | Database icon (verified) |
| `Download` | `Download01Icon` | Download arrow (verified) |
| `Edit` | `Edit01Icon` | Edit/pencil (verified) |
| `Edit3` | `PencilEdit01Icon` | Pencil edit variant (verified) |
| `ExternalLink` | `LinkSquare01Icon` | External link (verified) |
| `Eye` | `ViewIcon` | View/eye icon (verified) |
| `FileText` | `File01Icon` | Text file (verified) |
| `HelpCircle` | `HelpCircleIcon` | Help/question in circle (verified) |
| `Home` | `Home01Icon` | Home icon (verified) |
| `Italic` | `TextItalicIcon` | Italic text (verified) |
| `LayoutGrid` | `LayoutGridIcon` | Grid layout (verified) |
| `Loader2` | `Loading03Icon` | Loading spinner (verified) |
| `Map` (as MapIcon) | `ViewIcon` | Map/View icon (verified) |
| `Menu` | `Menu01Icon` | Hamburger menu (verified) |
| `MessageSquare` | `Message01Icon` | Message/chat square (verified) |
| `MoreHorizontal` | `MoreHorizontalIcon` | Three horizontal dots (verified) |
| `MoreVertical` | `MoreVerticalIcon` | Three vertical dots (verified) |
| `PenTool` | `PenTool01Icon` | Pen tool (verified) |
| `PlusIcon` | `Add01Icon` | Plus/add icon (verified) |
| `RefreshCw` | `RefreshIcon` | Refresh/reload (verified) |
| `Search` | `SearchIcon` | Search icon (verified) |
| `SkipForward` | `ArrowRight02Icon` | Skip/fast forward (verified) |
| `Sparkles` | `SparklesIcon` | Sparkles/stars effect (verified) |
| `Star` | `StarIcon` | Star icon (verified) |
| `StarHalf` | `StarHalfIcon` | Half star (verified) |
| `StarOff` | `StarOffIcon` | Star off state (verified) |
| `ThumbsDown` | `ThumbsDownIcon` | Thumbs down (verified) |
| `ThumbsUp` | `ThumbsUpIcon` | Thumbs up (verified) |
| `Trash2` | `Delete02Icon` | Delete/trash (verified) |
| `WifiOff` | `WifiOff01Icon` | WiFi disconnected (verified) |
| `X` | `Cancel01Icon` | Close/cancel X (verified) |
| `XCircle` | `CancelCircleIcon` | Cancel in circle (verified) |

## Size and Styling Considerations

### Size Mapping
- Lucide uses `size` prop or Tailwind classes like `h-4 w-4`
- Hugeicons uses `size` prop (number in pixels)
- Default size is 24px for both

### Color Mapping
- Lucide: `color` prop or Tailwind text color classes
- Hugeicons: `color` prop or `primaryColor`/`secondaryColor` for multicolor icons
- Use `className` with Tailwind classes for consistent styling

### Stroke Width
- Lucide: Default stroke width varies by icon
- Hugeicons: Use `strokeWidth` prop (default: 1.5)
- Adjust as needed for visual consistency

## Migration Checklist

- [ ] Install `@hugeicons/react` package
- [ ] Install `@hugeicons/core-free-icons` package
- [ ] Create this mapping document
- [ ] Update all component imports
- [ ] Replace icon usage with HugeiconsIcon wrapper
- [ ] Test all icon appearances
- [ ] Verify accessibility (aria-labels, etc.)
- [ ] Remove lucide-react dependency
- [ ] Update tests if needed

## Common Patterns

### Button with Icon
```tsx
// OLD
import { Search } from 'lucide-react';
<button><Search className="h-4 w-4 mr-2" /> Search</button>

// NEW
import { HugeiconsIcon } from '@hugeicons/react';
import { SearchIcon } from '@hugeicons/core-free-icons';
<button><HugeiconsIcon icon={SearchIcon} size={16} className="mr-2" /> Search</button>
```

### Icon Button
```tsx
// OLD
import { Trash2 } from 'lucide-react';
<button aria-label="Delete"><Trash2 className="h-5 w-5" /></button>

// NEW
import { HugeiconsIcon } from '@hugeicons/react';
import { Delete02Icon } from '@hugeicons/core-free-icons';
<button aria-label="Delete"><HugeiconsIcon icon={Delete02Icon} size={20} /></button>
```

### Conditional Icons
```tsx
// OLD
import { Eye, EyeOff } from 'lucide-react';
{isVisible ? <Eye /> : <EyeOff />}

// NEW
import { HugeiconsIcon } from '@hugeicons/react';
import { View01Icon, ViewOffIcon } from '@hugeicons/core-free-icons';
<HugeiconsIcon icon={isVisible ? View01Icon : ViewOffIcon} size={24} />
```

## Files to Update

### Book Components
- `/frontend/src/components/BookCard.tsx`
- `/frontend/src/components/BookCreationWizard.tsx`
- `/frontend/src/components/books/DeleteBookModal.tsx`

### Chapter Components
- `/frontend/src/components/chapters/*.tsx` (all files)

### UI Components
- `/frontend/src/components/ui/dialog.tsx`
- `/frontend/src/components/ui/user-button.tsx`
- `/frontend/src/components/ui/refresh-button.tsx`
- `/frontend/src/components/ui/ChapterStatusIndicator.tsx`

### Page Components
- `/frontend/src/app/dashboard/page.tsx`
- `/frontend/src/app/dashboard/books/[bookId]/chapters/[chapterId]/page.tsx`
- `/frontend/src/app/error.tsx`

### Other Components
- All components in TOC, navigation, export, errors, recovery, loading directories

## Testing After Migration

1. Visual inspection of all pages with icons
2. Verify icon sizes are consistent
3. Test hover states and interactions
4. Verify accessibility (screen reader labels)
5. Check responsive behavior
6. Test dark mode compatibility (if applicable)

## References

- Hugeicons Documentation: https://hugeicons.com/docs
- Hugeicons React: https://www.npmjs.com/package/@hugeicons/react
- Hugeicons Free Icons: https://www.npmjs.com/package/@hugeicons/core-free-icons
