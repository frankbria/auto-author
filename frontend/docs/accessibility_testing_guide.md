# Accessibility Testing Guide for Developers

**Quick Reference Guide for Auto-Author Frontend Development**

This guide provides practical instructions for developers to test and implement accessible components in the Auto-Author application. For comprehensive audit preparation, see `claudedocs/accessibility_audit_preparation.md`.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Using @axe-core/react in Development](#using-axe-corereact-in-development)
3. [Using axe DevTools Extension](#using-axe-devtools-extension)
4. [Common Accessibility Issues & Fixes](#common-accessibility-issues--fixes)
5. [Component-Specific Patterns](#component-specific-patterns)
6. [Testing Workflow](#testing-workflow)

---

## Quick Start

### Prerequisites

```bash
# Already installed in this project
@axe-core/react: v4.10.2
jest-axe: v10.0.0
@types/jest-axe: v3.5.9
```

### Browser Extension

Install **axe DevTools** for your browser:
- **Chrome/Edge**: [Chrome Web Store](https://chrome.google.com/webstore/detail/axe-devtools-web-accessib/lhdoppojpmngadmnindnejefpokejbdd)
- **Firefox**: [Firefox Add-ons](https://addons.mozilla.org/en-US/firefox/addon/axe-devtools/)

### 3-Minute Accessibility Check

1. **Start dev server**: `npm run dev`
2. **Open page in browser**: http://localhost:3000
3. **Open DevTools**: F12 → "axe DevTools" tab
4. **Click**: "Scan ALL of my page"
5. **Review issues**: Fix Critical and Serious issues immediately

---

## Using @axe-core/react in Development

### Option 1: Runtime Accessibility Checks (Development Only)

**Not recommended for this project** - use browser extension instead. Runtime checks can impact performance.

If needed for specific debugging:

```typescript
// src/lib/axe-init.ts
if (process.env.NODE_ENV === 'development') {
  import('@axe-core/react').then((axe) => {
    const React = require('react');
    const ReactDOM = require('react-dom');

    axe.default(React, ReactDOM, 1000, {
      rules: [
        { id: 'wcag2aa', enabled: true },
        { id: 'wcag21aa', enabled: true },
      ],
    });
  });
}

// Import in src/app/layout.tsx
import '@/lib/axe-init';
```

**Recommendation**: Use browser extension for manual testing, jest-axe for automated tests.

---

## Using axe DevTools Extension

### Basic Workflow

1. **Navigate to page**: Open any page in your running application
2. **Open DevTools**: Press F12 or right-click → "Inspect"
3. **Find axe tab**: Click "axe DevTools" tab (may be in "»" overflow menu)
4. **Run scan**: Click "Scan ALL of my page" button
5. **Review results**: Issues grouped by severity

### Understanding Results

**Issue Severity**:
- 🔴 **Critical**: Blocking accessibility failures - fix immediately
- 🟠 **Serious**: Significant barriers - fix soon
- 🟡 **Moderate**: May cause problems - should fix
- 🔵 **Minor**: Minor issues - nice to fix

**Issue Information**:
- **Highlight**: Elements with issues are outlined on page
- **Inspect**: Click issue to see affected element in Elements panel
- **Learn More**: Links to WCAG criterion and remediation guidance
- **Copy Selector**: Get CSS selector for debugging

### Example Scan Results

```
✅ 47 Passed
❌ 3 Violations Found

Critical (1):
- Button does not have accessible name
  Impact: Critical
  Elements: button.delete-btn (1)

Serious (2):
- Form elements must have labels
  Impact: Serious
  Elements: input#book-title (1), textarea#description (1)
```

### Guided Tests

For complex scenarios (keyboard navigation, screen reader testing):

1. Click **"Intelligent Guided Tests"** in axe DevTools
2. Follow step-by-step instructions
3. Answer questions about manual testing
4. Get comprehensive assessment

---

## Common Accessibility Issues & Fixes

### Issue 1: Missing Alt Text on Images

**Problem**: Images without alternative text

**Detection**:
```typescript
// axe DevTools will flag:
<img src="/book-cover.jpg" />
```

**Fix**:
```typescript
// Descriptive alt for meaningful images
<img
  src="/book-cover.jpg"
  alt="Cover of 'The Great Novel' showing mountain landscape"
/>

// Empty alt for decorative images
<img src="/decorative-divider.svg" alt="" />

// Next.js Image component
import Image from 'next/image';

<Image
  src="/book-cover.jpg"
  alt="Cover of 'The Great Novel'"
  width={300}
  height={400}
/>
```

**Test**:
```bash
# Run axe DevTools scan - should pass "Images must have alternative text"
```

---

### Issue 2: Button Without Accessible Name

**Problem**: Icon-only buttons without text labels

**Detection**:
```typescript
// axe DevTools will flag:
<button onClick={handleDelete}>
  <TrashIcon />
</button>
```

**Fix - Option 1: aria-label**:
```typescript
<button onClick={handleDelete} aria-label="Delete book">
  <TrashIcon />
</button>
```

**Fix - Option 2: Visually Hidden Text**:
```typescript
<button onClick={handleDelete}>
  <TrashIcon aria-hidden="true" />
  <span className="sr-only">Delete book</span>
</button>

// Utility class in globals.css:
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
```

**Best Practice**: Use aria-label for brevity, visually hidden text when label needs to be translated.

---

### Issue 3: Form Input Without Label

**Problem**: Input fields missing associated labels

**Detection**:
```typescript
// axe DevTools will flag:
<input type="text" placeholder="Enter book title" />
```

**Fix**:
```typescript
// Explicit label association
<label htmlFor="book-title" className="block mb-2">
  Book Title
</label>
<input
  type="text"
  id="book-title"
  name="title"
  placeholder="Enter book title"
/>

// With required indicator
<label htmlFor="book-title" className="block mb-2">
  Book Title <span className="text-red-500">*</span>
</label>
<input
  type="text"
  id="book-title"
  name="title"
  required
  aria-required="true"
/>
```

**Test**:
```typescript
// jest-axe test
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';

test('form input has label', async () => {
  const { container } = render(
    <form>
      <label htmlFor="book-title">Book Title</label>
      <input type="text" id="book-title" />
    </form>
  );
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

---

### Issue 4: Low Color Contrast

**Problem**: Text doesn't meet WCAG AA contrast ratio (4.5:1 for normal text)

**Detection**:
```typescript
// axe DevTools will flag low contrast, or use WAVE extension
<p className="text-gray-400">Description text</p>
// gray-400 on white background typically fails
```

**Fix**:
```typescript
// Use darker colors
<p className="text-gray-700">Description text</p>
// gray-700 on white background typically passes

// Or use online checker:
// https://webaim.org/resources/contrastchecker/
```

**TailwindCSS Contrast Guidelines**:
- **On white background**: Use gray-700 or darker
- **On dark background**: Use gray-200 or lighter
- **Large text (18pt+)**: Can use gray-600 (3:1 ratio acceptable)

**Quick Test**:
```bash
# In axe DevTools, contrast issues show as:
"Elements must have sufficient color contrast"
Impact: Serious
Ratio: 3.1:1 (needs 4.5:1)
```

---

### Issue 5: Missing Focus Indicator

**Problem**: Focus outline removed or invisible

**Detection**:
```css
/* BAD - removes focus indicator */
button:focus {
  outline: none;
}
```

**Fix**:
```css
/* GOOD - visible focus indicator */
button:focus-visible {
  outline: 2px solid #0066cc;
  outline-offset: 2px;
}

/* TailwindCSS approach */
.btn {
  @apply focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 focus-visible:outline-offset-2;
}
```

**Best Practice**: Never remove `outline` without providing alternative focus indicator.

**Test**:
```bash
# Manual test:
1. Press Tab to navigate to button
2. Verify visible outline or alternative indicator
3. Check contrast ratio of indicator ≥ 3:1
```

---

### Issue 6: Keyboard Trap in Modal

**Problem**: Focus trapped in modal, can't escape with keyboard

**Detection**:
```typescript
// Manual test - press Tab repeatedly in modal
// If focus never reaches "outside" modal, it's trapped
```

**Fix - Use Radix UI Dialog** (recommended):
```typescript
import { Dialog } from '@radix-ui/react-dialog';

// Radix handles focus trap and Esc key automatically
<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <Dialog.Content>
    <Dialog.Title>Delete Book</Dialog.Title>
    <Dialog.Description>
      Are you sure you want to delete this book?
    </Dialog.Description>
    <button onClick={handleDelete}>Delete</button>
    <Dialog.Close asChild>
      <button>Cancel</button>
    </Dialog.Close>
  </Dialog.Content>
</Dialog>
```

**Manual Implementation** (if not using Radix):
```typescript
// Use focus trap library
import { useFocusTrap } from '@/hooks/useFocusTrap';

function Modal({ isOpen, onClose, children }) {
  const modalRef = useFocusTrap(isOpen);

  return (
    <div
      ref={modalRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      {children}
    </div>
  );
}
```

---

### Issue 7: Missing ARIA Attributes on Custom Controls

**Problem**: Custom components (tabs, dropdowns) without proper ARIA

**Detection**:
```typescript
// axe DevTools will flag missing roles/attributes
<div onClick={handleTabClick}>Chapter 1</div>
```

**Fix - Use Radix UI Primitives** (recommended):
```typescript
import * as Tabs from '@radix-ui/react-tabs';

// Radix provides all ARIA attributes automatically
<Tabs.Root value={activeTab} onValueChange={setActiveTab}>
  <Tabs.List aria-label="Book chapters">
    <Tabs.Trigger value="chapter-1">Chapter 1</Tabs.Trigger>
    <Tabs.Trigger value="chapter-2">Chapter 2</Tabs.Trigger>
  </Tabs.List>
  <Tabs.Content value="chapter-1">Content 1</Tabs.Content>
  <Tabs.Content value="chapter-2">Content 2</Tabs.Content>
</Tabs.Root>
```

**Manual Implementation** (if needed):
```typescript
// Full ARIA tabs pattern
<div role="tablist" aria-label="Book chapters">
  <button
    role="tab"
    aria-selected={activeTab === 'chapter-1'}
    aria-controls="panel-chapter-1"
    id="tab-chapter-1"
    onClick={() => setActiveTab('chapter-1')}
  >
    Chapter 1
  </button>
</div>
<div
  role="tabpanel"
  aria-labelledby="tab-chapter-1"
  id="panel-chapter-1"
  hidden={activeTab !== 'chapter-1'}
>
  Content 1
</div>
```

**Reference**: [ARIA Authoring Practices - Tabs Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/)

---

## Component-Specific Patterns

### Pattern 1: Accessible Button

```typescript
import { Button } from '@/components/ui/button';

// Text button (automatically accessible)
<Button onClick={handleSave}>Save Book</Button>

// Icon button - add aria-label
<Button onClick={handleDelete} aria-label="Delete book">
  <TrashIcon />
</Button>

// Button with icon and text
<Button onClick={handleExport}>
  <DownloadIcon aria-hidden="true" />
  Export PDF
</Button>

// Loading state
<Button disabled={isLoading} aria-busy={isLoading}>
  {isLoading ? 'Saving...' : 'Save Book'}
</Button>
```

---

### Pattern 2: Accessible Form

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

const schema = z.object({
  title: z.string().min(3, 'Title must be at least 3 characters'),
  description: z.string().optional(),
});

function BookForm() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      {/* Text input with label and error */}
      <div>
        <label htmlFor="title" className="block mb-2">
          Book Title <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          id="title"
          {...register('title')}
          aria-required="true"
          aria-invalid={errors.title ? 'true' : 'false'}
          aria-describedby={errors.title ? 'title-error' : undefined}
          className="w-full border rounded px-3 py-2"
        />
        {errors.title && (
          <p id="title-error" className="text-red-600 text-sm mt-1" role="alert">
            {errors.title.message}
          </p>
        )}
      </div>

      {/* Textarea with label */}
      <div className="mt-4">
        <label htmlFor="description" className="block mb-2">
          Description
        </label>
        <textarea
          id="description"
          {...register('description')}
          rows={4}
          className="w-full border rounded px-3 py-2"
        />
      </div>

      <button type="submit" className="mt-4">Submit</button>
    </form>
  );
}
```

**Key Accessibility Features**:
- Explicit label association (`htmlFor` + `id`)
- Required field marked visually (`*`) and semantically (`aria-required`)
- Error messages linked to inputs (`aria-describedby`)
- Error alerts use `role="alert"` for screen reader announcement
- Invalid state indicated (`aria-invalid`)

---

### Pattern 3: Accessible Modal Dialog

```typescript
import * as Dialog from '@radix-ui/react-dialog';

function DeleteBookModal({
  isOpen,
  onOpenChange,
  bookTitle,
  onConfirm
}) {
  return (
    <Dialog.Root open={isOpen} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50" />
        <Dialog.Content
          className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded p-6 max-w-md"
          aria-describedby="dialog-description"
        >
          <Dialog.Title className="text-xl font-bold mb-2">
            Delete Book
          </Dialog.Title>
          <Dialog.Description id="dialog-description" className="mb-4">
            Are you sure you want to delete "{bookTitle}"? This action cannot be undone.
          </Dialog.Description>

          <div className="flex gap-3 justify-end">
            <Dialog.Close asChild>
              <button className="px-4 py-2 border rounded">
                Cancel
              </button>
            </Dialog.Close>
            <button
              onClick={onConfirm}
              className="px-4 py-2 bg-red-600 text-white rounded"
            >
              Delete
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
```

**Key Accessibility Features**:
- Radix Dialog handles focus trap automatically
- Esc key closes modal
- Focus returns to trigger on close
- `aria-describedby` links description for screen readers
- Overlay dims background (visual + `aria-hidden` on background content)

---

### Pattern 4: Accessible Tab Interface

```typescript
import * as Tabs from '@radix-ui/react-tabs';

function ChapterTabs({ chapters, activeChapter, onChapterChange }) {
  return (
    <Tabs.Root
      value={activeChapter}
      onValueChange={onChapterChange}
      orientation="vertical"
    >
      <Tabs.List
        aria-label="Book chapters"
        className="flex flex-col space-y-1"
      >
        {chapters.map((chapter, index) => (
          <Tabs.Trigger
            key={chapter.id}
            value={chapter.id}
            className="px-4 py-2 text-left hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-blue-600"
          >
            <span className="text-sm text-gray-500">Chapter {index + 1}</span>
            <span className="block font-medium">{chapter.title}</span>
          </Tabs.Trigger>
        ))}
      </Tabs.List>

      {chapters.map((chapter) => (
        <Tabs.Content
          key={chapter.id}
          value={chapter.id}
          className="flex-1 p-6"
        >
          {/* Chapter content */}
        </Tabs.Content>
      ))}
    </Tabs.Root>
  );
}
```

**Key Accessibility Features**:
- Radix Tabs provides all ARIA attributes automatically
- Keyboard navigation: Arrow keys move between tabs, Tab moves to panel
- Vertical orientation uses Up/Down arrows (horizontal uses Left/Right)
- Focus indicator visible on tabs
- Screen reader announces tab role, selected state, and panel content

---

### Pattern 5: Accessible Loading States

```typescript
import { LoadingStateManager } from '@/components/loading/LoadingStateManager';

function BookEditor() {
  const [isSaving, setIsSaving] = useState(false);

  return (
    <div>
      {/* Loading overlay with screen reader announcement */}
      <LoadingStateManager
        isLoading={isSaving}
        loadingMessage="Saving chapter..."
        successMessage="Chapter saved successfully"
        errorMessage="Failed to save chapter"
      />

      {/* Inline loading indicator */}
      <div className="flex items-center gap-2">
        {isSaving ? (
          <>
            <span
              className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full"
              aria-hidden="true"
            />
            <span aria-live="polite" aria-atomic="true">
              Saving...
            </span>
          </>
        ) : (
          <span aria-live="polite" aria-atomic="true">
            Saved ✓
          </span>
        )}
      </div>
    </div>
  );
}
```

**Key Accessibility Features**:
- `aria-live="polite"` announces status changes to screen readers
- Loading spinner marked `aria-hidden="true"` (decorative)
- Text descriptions for all states (loading, success, error)
- `aria-atomic="true"` ensures entire message announced

---

## Testing Workflow

### During Development (Before Committing)

1. **Visual Check**:
   - Use browser to visually inspect component
   - Ensure all text readable, buttons clear, layout logical

2. **Keyboard Test** (30 seconds):
   ```
   - Press Tab to navigate through interactive elements
   - Press Enter/Space to activate buttons
   - Press Esc to close modals
   - Verify focus indicator visible at all times
   ```

3. **axe DevTools Scan** (1 minute):
   ```
   - Open page in browser
   - F12 → axe DevTools tab
   - Click "Scan ALL of my page"
   - Fix any Critical or Serious issues
   ```

4. **Run Tests**:
   ```bash
   npm test -- --coverage
   # Ensure accessibility tests pass
   ```

### Adding Automated Tests

**Example: jest-axe test for component**

```typescript
// __tests__/BookCard.test.tsx
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import BookCard from '@/components/BookCard';

expect.extend(toHaveNoViolations);

const mockBook = {
  id: '1',
  title: 'Test Book',
  description: 'A test book description',
  chapters: 3,
  word_count: 5000,
};

describe('BookCard Accessibility', () => {
  test('has no accessibility violations', async () => {
    const { container } = render(
      <BookCard book={mockBook} onDelete={jest.fn()} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  test('book cover has alt text', () => {
    const { getByRole } = render(
      <BookCard book={mockBook} onDelete={jest.fn()} />
    );
    const img = getByRole('img');
    expect(img).toHaveAttribute('alt');
    expect(img.getAttribute('alt')).not.toBe('');
  });

  test('delete button has accessible name', () => {
    const { getByRole } = render(
      <BookCard book={mockBook} onDelete={jest.fn()} />
    );
    const deleteButton = getByRole('button', { name: /delete/i });
    expect(deleteButton).toBeInTheDocument();
  });
});
```

### Before Pull Request

**Accessibility Checklist**:
- [ ] All new components pass axe DevTools scan (0 Critical/Serious issues)
- [ ] All new components have jest-axe tests
- [ ] Keyboard navigation tested manually
- [ ] Focus indicators visible on all interactive elements
- [ ] All images have alt text
- [ ] All buttons have accessible names
- [ ] All form inputs have labels
- [ ] Color contrast meets 4.5:1 (text) or 3:1 (UI components)
- [ ] Documentation updated if new patterns introduced

---

## Resources

### Quick Links

- **WCAG 2.1 Quick Reference**: https://www.w3.org/WAI/WCAG21/quickref/?currentsidebar=%23col_overview&levels=aa
- **ARIA Authoring Practices**: https://www.w3.org/WAI/ARIA/apg/
- **WebAIM Contrast Checker**: https://webaim.org/resources/contrastchecker/
- **Radix UI Docs**: https://www.radix-ui.com/primitives/docs/overview/accessibility

### Project-Specific

- **Comprehensive Audit Prep**: `frontend/claudedocs/accessibility_audit_preparation.md`
- **Current Sprint**: `CURRENT_SPRINT.md`
- **Implementation Plan**: `IMPLEMENTATION_PLAN.md`

### Tools

- **axe DevTools**: Browser extension for accessibility testing
- **jest-axe**: Automated accessibility testing in Jest
- **NVDA**: Free screen reader for Windows
- **VoiceOver**: Built-in macOS screen reader (Cmd+F5)

---

## Need Help?

### Common Questions

**Q: Do I need to test with a screen reader for every component?**
A: No. Use jest-axe and axe DevTools for most testing. Screen reader testing is mainly for complex interactive components (tabs, modals, editors) and final QA.

**Q: Which Radix UI components are accessible by default?**
A: All Radix UI primitives are accessible out-of-the-box. They follow ARIA Authoring Practices and handle keyboard navigation, focus management, and ARIA attributes automatically.

**Q: Can I use `aria-label` on a `<div>` to make it a button?**
A: No. Use semantic HTML (`<button>`) first. ARIA should enhance, not replace, proper HTML.

**Q: What if axe DevTools shows issues in third-party libraries (Clerk, TipTap)?**
A: Document these issues separately. Focus on fixing issues in your own components first. Third-party issues may require library updates or custom wrappers.

**Q: How do I handle accessibility for dynamically loaded content?**
A: Use `aria-live` regions to announce changes. See LoadingStateManager for example patterns.

---

**Last Updated**: 2025-10-12
**Next Review**: After comprehensive accessibility audit
