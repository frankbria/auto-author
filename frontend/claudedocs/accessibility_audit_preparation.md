# Accessibility Audit Preparation - Auto-Author Frontend

**Document Version**: 1.0
**Date**: 2025-10-12
**Prepared For**: WCAG 2.1 Level AA Comprehensive Audit
**Application**: Auto-Author Book Writing Platform
**Frontend Stack**: Next.js 15 + React 18 + TypeScript + TailwindCSS

---

## Executive Summary

This document provides complete preparation for conducting a comprehensive WCAG 2.1 Level AA accessibility audit of the Auto-Author frontend application. All required tools have been installed, browser extensions documented, and systematic testing checklists created.

**Current Accessibility Status**:
- ✅ Touch targets: 100% WCAG 2.1 Level AAA compliance (44x44px minimum)
- ✅ Keyboard navigation: WCAG 2.1 compliant (Enter/Space on all interactive elements)
- ✅ Loading states: Comprehensive screen reader support via LoadingStateManager
- 🔍 **Ready for full audit**: All preparation complete

**Tools Installed**:
- @axe-core/react v4.10.2 (automated accessibility testing)
- jest-axe v10.0.0 (accessibility assertions in tests)
- @types/jest-axe v3.5.9 (TypeScript support)

---

## Table of Contents

1. [Tool Installation & Setup](#tool-installation--setup)
2. [Browser Extensions](#browser-extensions)
3. [WCAG 2.1 AA Requirements Checklist](#wcag-21-aa-requirements-checklist)
4. [Component Testing Checklist](#component-testing-checklist)
5. [Testing Workflow](#testing-workflow)
6. [Resources & References](#resources--references)

---

## 1. Tool Installation & Setup

### 1.1 @axe-core/react Installation

**Status**: ✅ Installed and verified

```bash
# Installation command
npm install --save-dev @axe-core/react

# Verify installation
npm list @axe-core/react
# Output: @axe-core/react@4.10.2
```

**Package.json Entry**:
```json
{
  "devDependencies": {
    "@axe-core/react": "^4.10.2",
    "@types/jest-axe": "^3.5.9",
    "jest-axe": "^10.0.0"
  }
}
```

### 1.2 Integration with Development Environment

**For Development Mode** (optional but recommended):

Create a development initialization file:

```typescript
// src/lib/axe-init.ts
if (process.env.NODE_ENV !== 'production') {
  import('@axe-core/react').then(axe => {
    axe.default(React, ReactDOM, 1000, {
      // Configuration options
      rules: [
        // Enable all WCAG 2.1 Level AA rules
        { id: 'wcag2aa', enabled: true },
        { id: 'wcag21aa', enabled: true },
      ],
    });
  });
}
```

**Note**: This is optional for the audit. We'll primarily use:
1. Browser extension for manual testing
2. jest-axe for automated test assertions
3. Playwright for E2E accessibility validation

### 1.3 Compatibility Verification

**React Version**: 18.2.0 ✅
**Next.js Version**: 15.0.0 ✅
**TypeScript**: 5.x ✅

All dependencies are compatible with @axe-core/react v4.10.2.

---

## 2. Browser Extensions

### 2.1 axe DevTools Browser Extension

**Recommended Extension**: axe DevTools by Deque Systems

**Installation Instructions**:

#### Chrome/Edge
1. Visit Chrome Web Store: https://chrome.google.com/webstore/detail/axe-devtools-web-accessib/lhdoppojpmngadmnindnejefpokejbdd
2. Click "Add to Chrome" / "Add to Edge"
3. Pin extension to toolbar for easy access
4. Grant permissions when prompted

#### Firefox
1. Visit Firefox Add-ons: https://addons.mozilla.org/en-US/firefox/addon/axe-devtools/
2. Click "Add to Firefox"
3. Approve permissions
4. Access via browser toolbar

### 2.2 Extension Configuration

**First-Time Setup**:

1. Open DevTools (F12 or Ctrl+Shift+I)
2. Navigate to "axe DevTools" tab
3. Configure settings:
   - **Standard**: WCAG 2.1 Level AA (our target)
   - **Tags**: Enable "wcag2aa", "wcag21aa", "best-practice"
   - **Issue Reporting**: Group by rule
   - **Highlight Elements**: Enable for visual identification

**Recommended Settings for Audit**:
```
Standard: WCAG 2.1 Level AA
Include: All issue types (Critical, Serious, Moderate, Minor)
Highlight: Enabled
Export Format: CSV or JSON for reporting
```

### 2.3 Quick Start Guide

**Basic Usage**:

1. Navigate to page to test (e.g., http://localhost:3000)
2. Open DevTools → "axe DevTools" tab
3. Click "Scan ALL of my page"
4. Review results organized by severity:
   - **Critical**: Must fix immediately
   - **Serious**: Important to fix
   - **Moderate**: Should fix
   - **Minor**: Nice to fix

5. Click individual issues to:
   - See affected elements highlighted
   - View detailed explanation
   - Access remediation guidance
   - Copy selector for debugging

**Advanced Features**:
- **Intelligent Guided Tests**: Step-by-step manual testing for complex scenarios
- **Export Reports**: Generate CSV/JSON for documentation
- **Issue Filtering**: Filter by WCAG criteria, severity, impact
- **Historical Tracking**: Compare results across scans

### 2.4 Additional Recommended Extensions

**WAVE (Web Accessibility Evaluation Tool)**:
- Chrome: https://chrome.google.com/webstore/detail/wave-evaluation-tool/jbbplnpkjmmeebjpijfedlgcdilocofh
- Firefox: https://addons.mozilla.org/en-US/firefox/addon/wave-accessibility-tool/
- **Use Case**: Visual accessibility feedback directly on page

**HeadingsMap**:
- Chrome: https://chrome.google.com/webstore/detail/headingsmap/flbjommegcjonpdmenkdiocclhjacmbi
- **Use Case**: Document outline validation (headings hierarchy)

**Accessibility Insights for Web**:
- Chrome: https://chrome.google.com/webstore/detail/accessibility-insights-fo/pbjjkligggfmakdaogkfomddhfmpjeni
- **Use Case**: Comprehensive accessibility assessment with guided tests

---

## 3. WCAG 2.1 AA Requirements Checklist

### 3.1 Principle 1: Perceivable

Information and user interface components must be presentable to users in ways they can perceive.

#### 1.1 Text Alternatives (Level A)

| Guideline | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **1.1.1** | Non-text Content | 🔍 | All images, icons, controls need alt text |

**Testing Focus**:
- All `<img>` tags have meaningful `alt` attributes
- Decorative images use `alt=""` (empty string)
- Icon buttons have `aria-label` or visible text
- Form controls have associated labels
- Complex images have long descriptions if needed

**Current Status**: Touch targets achieved AAA (44x44px), need to verify alt text coverage

---

#### 1.2 Time-based Media (Level A)

| Guideline | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **1.2.1** | Audio-only and Video-only (Prerecorded) | N/A | No audio/video content in application |
| **1.2.2** | Captions (Prerecorded) | N/A | No video content |
| **1.2.3** | Audio Description or Media Alternative | N/A | No video content |

**Testing Focus**: Not applicable - application is text-based book writing platform

---

#### 1.3 Adaptable (Level A)

| Guideline | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **1.3.1** | Info and Relationships | 🔍 | Semantic HTML, proper heading hierarchy |
| **1.3.2** | Meaningful Sequence | 🔍 | Logical reading order maintained |
| **1.3.3** | Sensory Characteristics | 🔍 | Instructions don't rely solely on visual cues |
| **1.3.4** | Orientation (2.1) | ✅ | Responsive design supports both orientations |
| **1.3.5** | Identify Input Purpose (2.1) | 🔍 | Form autocomplete attributes |

**Testing Focus**:
- Heading hierarchy (h1 → h2 → h3, no skips)
- Proper use of semantic HTML (`<nav>`, `<main>`, `<article>`, `<section>`)
- Lists use `<ul>`/`<ol>` with `<li>`
- Tables use proper structure (`<thead>`, `<tbody>`, `<th>` with scope)
- Form labels properly associated with inputs
- Autocomplete attributes on forms (name, email, etc.)

**Known Compliant**: Responsive design validated for orientation support

---

#### 1.4 Distinguishable (Level AA)

| Guideline | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **1.4.1** | Use of Color | 🔍 | Color not sole means of conveying info |
| **1.4.2** | Audio Control | N/A | No auto-playing audio |
| **1.4.3** | Contrast (Minimum) - AA | 🔍 | 4.5:1 for text, 3:1 for large text |
| **1.4.4** | Resize Text | 🔍 | Text scalable to 200% without loss |
| **1.4.5** | Images of Text | 🔍 | Text used instead of images where possible |
| **1.4.10** | Reflow (2.1) | ✅ | Responsive design supports 320px width |
| **1.4.11** | Non-text Contrast (2.1) | 🔍 | 3:1 contrast for UI components |
| **1.4.12** | Text Spacing (2.1) | 🔍 | No content loss with adjusted spacing |
| **1.4.13** | Content on Hover/Focus (2.1) | 🔍 | Tooltips dismissible, hoverable, persistent |

**Testing Focus**:
- Run contrast checker on all text/background combinations
- Verify status indicators use icons + text (not color alone)
- Test zoom to 200% in browser
- Test with CSS spacing overrides:
  ```css
  * {
    line-height: 1.5 !important;
    letter-spacing: 0.12em !important;
    word-spacing: 0.16em !important;
  }
  p {
    margin-bottom: 2em !important;
  }
  ```
- Verify tooltips remain visible on hover and can be dismissed

**Current Status**: TailwindCSS colors generally provide good contrast, but need systematic verification

---

### 3.2 Principle 2: Operable

User interface components and navigation must be operable.

#### 2.1 Keyboard Accessible (Level A)

| Guideline | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **2.1.1** | Keyboard | ✅ | All functionality via keyboard |
| **2.1.2** | No Keyboard Trap | 🔍 | Focus never trapped |
| **2.1.4** | Character Key Shortcuts (2.1) | 🔍 | Shortcuts can be turned off/remapped |

**Testing Focus**:
- Tab through entire application
- Verify all interactive elements reachable (buttons, links, forms, tabs)
- Test modal dialogs (can open, navigate within, close with Esc)
- Test dropdown menus
- Test chapter tabs (Ctrl+1-9 shortcuts)
- Verify focus never trapped in component
- Verify custom shortcuts documented and configurable

**Current Status**: ✅ WCAG 2.1 compliant keyboard navigation (Enter/Space on all interactive elements)

---

#### 2.2 Enough Time (Level A)

| Guideline | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **2.2.1** | Timing Adjustable | ✅ | Auto-save with 3-second debounce, no strict timeouts |
| **2.2.2** | Pause, Stop, Hide | N/A | No auto-updating content |

**Testing Focus**:
- Verify auto-save doesn't interrupt user flow
- Check localStorage backup mechanism works
- No session timeouts that lose data

**Current Status**: ✅ Auto-save with localStorage backup provides ample time control

---

#### 2.3 Seizures and Physical Reactions (Level A)

| Guideline | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **2.3.1** | Three Flashes or Below Threshold | ✅ | No flashing content |

**Testing Focus**: Verify no animations flash more than 3 times per second

**Current Status**: ✅ Application uses subtle transitions, no rapid flashing

---

#### 2.4 Navigable (Level AA)

| Guideline | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **2.4.1** | Bypass Blocks | 🔍 | Skip navigation link provided |
| **2.4.2** | Page Titled | 🔍 | Each page has descriptive `<title>` |
| **2.4.3** | Focus Order | ✅ | Logical focus order maintained |
| **2.4.4** | Link Purpose (In Context) | 🔍 | Link text describes destination |
| **2.4.5** | Multiple Ways - AA | 🔍 | Navigation menu + breadcrumbs/search |
| **2.4.6** | Headings and Labels - AA | 🔍 | Descriptive headings and labels |
| **2.4.7** | Focus Visible - AA | 🔍 | Keyboard focus indicator visible |

**Testing Focus**:
- Add skip navigation link if missing: "Skip to main content"
- Verify every page has unique, descriptive `<title>`
- Tab through pages to verify logical focus order
- Check all links have descriptive text (not "click here")
- Verify multiple navigation paths (menu, dashboard cards, breadcrumbs)
- Verify all headings accurately describe content sections
- Check focus indicator contrast ratio meets 3:1 minimum
- Test with browser zoom to ensure focus indicator scales

**Current Status**: Focus order validated in responsive design audit; need to verify skip links and page titles

---

#### 2.5 Input Modalities (Level AA - WCAG 2.1)

| Guideline | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **2.5.1** | Pointer Gestures (2.1) | ✅ | No complex gestures required |
| **2.5.2** | Pointer Cancellation (2.1) | 🔍 | Down-event doesn't trigger action |
| **2.5.3** | Label in Name (2.1) | 🔍 | Visible labels match accessible names |
| **2.5.4** | Motion Actuation (2.1) | N/A | No motion-based controls |
| **2.5.5** | Target Size (2.1 - AAA) | ✅ | 44x44px minimum (exceeds AA requirement) |

**Testing Focus**:
- Verify drag-and-drop alternatives available (TOC reordering)
- Test pointer cancellation: clicking and moving away should cancel
- Verify aria-label matches visible label text
- Confirm all touch targets meet 44x44px minimum

**Current Status**: ✅ Touch targets achieve Level AAA compliance (44x44px minimum)

---

### 3.3 Principle 3: Understandable

Information and the operation of user interface must be understandable.

#### 3.1 Readable (Level AA)

| Guideline | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **3.1.1** | Language of Page | 🔍 | `<html lang="en">` present |
| **3.1.2** | Language of Parts - AA | 🔍 | Foreign language content marked |

**Testing Focus**:
- Verify `<html lang="en">` in document
- Check for any non-English content with appropriate `lang` attribute

**Current Status**: Next.js typically sets this automatically, but need verification

---

#### 3.2 Predictable (Level AA)

| Guideline | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **3.2.1** | On Focus | 🔍 | Focus doesn't trigger context change |
| **3.2.2** | On Input | 🔍 | Input doesn't trigger unexpected change |
| **3.2.3** | Consistent Navigation - AA | 🔍 | Navigation consistent across pages |
| **3.2.4** | Consistent Identification - AA | 🔍 | Components identified consistently |

**Testing Focus**:
- Tab through forms - focus alone shouldn't submit or change context
- Type in inputs - character entry shouldn't submit unexpectedly
- Verify navigation menu appears in same location on all pages
- Check that "Save" buttons always look/behave same way
- Verify icons (save, delete, etc.) used consistently

**Current Status**: Need systematic verification of consistency patterns

---

#### 3.3 Input Assistance (Level AA)

| Guideline | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **3.3.1** | Error Identification | 🔍 | Errors identified in text |
| **3.3.2** | Labels or Instructions - AA | 🔍 | Labels/instructions provided |
| **3.3.3** | Error Suggestion - AA | 🔍 | Suggestions provided for errors |
| **3.3.4** | Error Prevention (Legal/Financial) - AA | ✅ | Reversible, checked, confirmed |

**Testing Focus**:
- Submit forms with errors - verify error messages are clear text (not just red borders)
- Check all form fields have visible labels
- Verify required fields marked with both `*` and text ("required")
- Test validation messages provide helpful suggestions
- Verify delete confirmation dialogs (book deletion requires typing title)
- Check form data can be reviewed before submission

**Current Status**: ✅ Delete confirmation with type-to-confirm pattern; need to verify error handling patterns

---

### 3.4 Principle 4: Robust

Content must be robust enough to be interpreted by a wide variety of user agents, including assistive technologies.

#### 4.1 Compatible (Level AA)

| Guideline | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **4.1.1** | Parsing | ✅ | Valid HTML (React enforces this) |
| **4.1.2** | Name, Role, Value - AA | 🔍 | All UI components properly exposed |
| **4.1.3** | Status Messages (2.1) | ✅ | LoadingStateManager provides ARIA live regions |

**Testing Focus**:
- Run HTML validator (optional - React usually ensures validity)
- Test with screen reader (NVDA/JAWS/VoiceOver):
  - All interactive elements announced correctly
  - Button roles and labels clear
  - Form labels associated
  - Tab list/tab panel relationships clear
  - Dialog roles and labels correct
- Verify loading states use `aria-live` regions (LoadingStateManager)
- Check success/error toasts announced to screen readers

**Current Status**: ✅ LoadingStateManager provides comprehensive screen reader support for loading states

---

## 4. Component Testing Checklist

### 4.1 Navigation Components

#### Primary Navigation (Navigation Menu)

**File**: `src/components/navigation/*`

**WCAG Criteria**: 2.4.1 (Bypass Blocks), 2.4.3 (Focus Order), 2.4.7 (Focus Visible), 4.1.2 (Name, Role, Value)

**Manual Tests**:
- [ ] Tab key reaches all menu items in logical order
- [ ] Enter/Space activates menu items
- [ ] Current page indicated with aria-current="page"
- [ ] Menu has `<nav>` landmark with aria-label="Main navigation"
- [ ] Focus indicator visible on all menu items (3:1 contrast)
- [ ] Mobile menu can be opened and closed with keyboard
- [ ] Screen reader announces menu structure correctly

**Automated Tests** (axe DevTools):
- [ ] Scan navigation component for landmark roles
- [ ] Verify no duplicate IDs
- [ ] Check color contrast on menu items

**Priority**: Critical (impacts all pages)

---

#### Skip Navigation Link

**File**: Check `src/app/layout.tsx` or main layout

**WCAG Criteria**: 2.4.1 (Bypass Blocks)

**Manual Tests**:
- [ ] Press Tab on page load - skip link appears
- [ ] Activating skip link moves focus to main content
- [ ] Skip link visible when focused (not hidden off-screen)
- [ ] Skip link contrast meets 4.5:1 ratio

**Implementation** (if missing):
```tsx
<a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-white focus:text-black">
  Skip to main content
</a>
```

**Priority**: High (Level A requirement)

---

### 4.2 Book Management Components

#### BookCard Component

**File**: `src/components/BookCard.tsx`

**WCAG Criteria**: 1.1.1 (Text Alternatives), 2.4.4 (Link Purpose), 2.5.3 (Label in Name), 2.5.5 (Target Size)

**Manual Tests**:
- [ ] Book cover image has descriptive alt text (or alt="" if decorative)
- [ ] Card is keyboard accessible (Tab to focus)
- [ ] Enter/Space opens book detail view
- [ ] Delete button has clear aria-label: "Delete [book title]"
- [ ] Touch targets meet 44x44px minimum (AAA compliance)
- [ ] Focus indicator visible on card and buttons
- [ ] Book title is properly announced by screen reader
- [ ] Card actions (open, delete) announced clearly

**Automated Tests** (jest-axe):
```typescript
import { axe } from 'jest-axe';
import { render } from '@testing-library/react';
import BookCard from '@/components/BookCard';

test('BookCard is accessible', async () => {
  const { container } = render(
    <BookCard book={mockBook} onDelete={jest.fn()} />
  );
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

**Priority**: High (primary interaction point)

---

#### DeleteBookModal Component

**File**: `src/components/books/DeleteBookModal.tsx`

**WCAG Criteria**: 2.1.2 (No Keyboard Trap), 2.4.7 (Focus Visible), 3.3.2 (Labels/Instructions), 4.1.2 (Name, Role, Value)

**Manual Tests**:
- [ ] Modal opens with focus on title input field
- [ ] Tab cycles through modal elements only (focus trapped appropriately)
- [ ] Esc key closes modal (unless deletion in progress)
- [ ] Enter in input field does NOT submit (only button activates delete)
- [ ] Modal has role="alertdialog" or role="dialog"
- [ ] Modal has accessible name (aria-labelledby or aria-label)
- [ ] Warning message announced by screen reader
- [ ] Input field has clear label: "Type book title to confirm"
- [ ] Confirm button disabled until exact match typed
- [ ] Loading state announced: "Deleting book, please wait"

**Automated Tests**:
```typescript
test('DeleteBookModal is accessible', async () => {
  const { container } = render(
    <DeleteBookModal
      isOpen={true}
      bookTitle="Test Book"
      onConfirm={jest.fn()}
    />
  );
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

**Priority**: Critical (data loss prevention)

---

#### EmptyBookState Component

**File**: `src/components/EmptyBookState.tsx`

**WCAG Criteria**: 1.1.1 (Text Alternatives), 1.3.1 (Info and Relationships), 2.4.4 (Link Purpose)

**Manual Tests**:
- [ ] Empty state illustration has descriptive alt text or aria-label
- [ ] Heading hierarchy logical (h1/h2 for "No books yet")
- [ ] Call-to-action button clearly labeled: "Create Your First Book"
- [ ] Button keyboard accessible

**Priority**: Low (informational component)

---

### 4.3 Chapter Editing Components

#### Chapter Tabs Interface

**File**: `src/components/chapters/*`

**WCAG Criteria**: 2.1.1 (Keyboard), 2.4.3 (Focus Order), 4.1.2 (Name, Role, Value)

**Manual Tests**:
- [ ] Tabs use proper ARIA: role="tablist", role="tab", role="tabpanel"
- [ ] aria-selected="true" on active tab
- [ ] Arrow keys navigate between tabs (Left/Right)
- [ ] Home/End jump to first/last tab
- [ ] Tab key moves from tab list to tab panel content
- [ ] Keyboard shortcuts (Ctrl+1-9) work and are documented
- [ ] aria-controls links tabs to panels
- [ ] Tab panels have aria-labelledby pointing to tab
- [ ] Vertical layout: Up/Down arrows navigate (not Left/Right)

**Automated Tests**:
```typescript
test('Chapter tabs are accessible', async () => {
  const { container } = render(<ChapterTabs chapters={mockChapters} />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

**Reference**: [ARIA Authoring Practices - Tabs Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/)

**Priority**: Critical (primary content editing interface)

---

#### Rich Text Editor (TipTap)

**File**: `src/components/chapters/editor/*` (or similar)

**WCAG Criteria**: 2.1.1 (Keyboard), 3.3.2 (Labels/Instructions), 4.1.2 (Name, Role, Value)

**Manual Tests**:
- [ ] Editor has clear label: "Chapter content editor"
- [ ] Editor region has role="textbox" and aria-multiline="true"
- [ ] Toolbar buttons keyboard accessible (Tab to reach)
- [ ] Toolbar buttons have clear labels (not just icons)
- [ ] Formatting shortcuts documented (Ctrl+B for bold, etc.)
- [ ] Character count announced periodically to screen reader
- [ ] Save status changes announced (aria-live="polite")
- [ ] Editor can receive focus via Tab key
- [ ] Screen reader announces editor as "editable text"

**Automated Tests**:
```typescript
test('TipTap editor is accessible', async () => {
  const { container } = render(<ChapterEditor content="" onChange={jest.fn()} />);
  const results = await axe(container, {
    rules: {
      // TipTap may have contenteditable-specific considerations
      'aria-input-field-name': { enabled: true },
    },
  });
  expect(results).toHaveNoViolations();
});
```

**Priority**: Critical (core content creation tool)

---

#### Auto-save Status Indicator

**File**: Part of editor component

**WCAG Criteria**: 1.3.3 (Sensory Characteristics), 1.4.1 (Use of Color), 4.1.3 (Status Messages)

**Manual Tests**:
- [ ] Status uses icon + text (not color alone)
- [ ] Status messages use aria-live="polite" region
- [ ] Changes announced: "Not saved yet" → "Saving..." → "Saved ✓"
- [ ] Save failure announced with error message
- [ ] Visual indicator has 3:1 contrast ratio (color + icon)
- [ ] Status persists long enough to read (minimum 3 seconds)

**Priority**: High (user feedback critical)

---

### 4.4 Form Components

#### BookCreationWizard

**File**: `src/components/BookCreationWizard.tsx`

**WCAG Criteria**: 3.3.2 (Labels/Instructions), 3.3.3 (Error Suggestion), 4.1.2 (Name, Role, Value)

**Manual Tests**:
- [ ] All form fields have visible labels
- [ ] Required fields marked with `*` and aria-required="true"
- [ ] Multi-step wizard has clear progress indicator
- [ ] Current step announced to screen reader
- [ ] Validation errors displayed as text (not just red border)
- [ ] Error messages linked to fields (aria-describedby)
- [ ] Error suggestions helpful: "Title required (minimum 3 characters)"
- [ ] Previous/Next buttons clearly labeled
- [ ] Focus moves to error summary on validation failure

**Automated Tests**:
```typescript
test('BookCreationWizard is accessible', async () => {
  const { container } = render(<BookCreationWizard onComplete={jest.fn()} />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

**Priority**: High (primary user flow)

---

#### BookMetadataForm

**File**: `src/components/BookMetadataForm.tsx`

**WCAG Criteria**: 1.3.5 (Identify Input Purpose), 3.3.2 (Labels/Instructions)

**Manual Tests**:
- [ ] All inputs have autocomplete attributes where applicable
- [ ] Labels explicitly associated via `htmlFor` and `id`
- [ ] Input purpose clear from label text
- [ ] Validation messages provide helpful guidance
- [ ] File upload (cover image) has clear instructions
- [ ] File upload accepts label includes supported formats

**Priority**: Medium (metadata optional, but important)

---

### 4.5 Modal & Dialog Components

#### General Modal Pattern

**File**: Multiple components using Radix UI Dialog

**WCAG Criteria**: 2.1.2 (No Keyboard Trap), 2.4.3 (Focus Order), 4.1.2 (Name, Role, Value)

**Manual Tests**:
- [ ] Modal traps focus appropriately (Tab cycles within modal)
- [ ] Esc key closes modal (unless blocked by loading state)
- [ ] Focus returns to trigger element on close
- [ ] Modal has role="dialog" or role="alertdialog"
- [ ] Modal has accessible name (aria-labelledby or aria-label)
- [ ] Modal description available (aria-describedby)
- [ ] Background content marked inert or aria-hidden="true"
- [ ] Close button (X) has aria-label="Close"

**Priority**: Critical (used throughout application)

---

### 4.6 Loading & Error States

#### LoadingStateManager

**File**: `src/components/loading/LoadingStateManager.tsx`

**WCAG Criteria**: 4.1.3 (Status Messages)

**Manual Tests**:
- [ ] Loading states use aria-live="polite" or "assertive"
- [ ] Loading spinner has aria-label="Loading" or equivalent
- [ ] Screen reader announces loading state changes
- [ ] Loading overlay has appropriate role
- [ ] Focus management during loading (disable controls)
- [ ] Error states announced clearly
- [ ] Success states announced

**Current Status**: ✅ LoadingStateManager provides comprehensive ARIA live region support

**Priority**: High (affects user feedback throughout app)

---

### 4.7 Export Functionality

#### Export Modal/Dialog

**File**: `src/components/export/*`

**WCAG Criteria**: 3.3.2 (Labels/Instructions), 4.1.2 (Name, Role, Value)

**Manual Tests**:
- [ ] Export format options (PDF/DOCX) keyboard accessible
- [ ] Radio buttons or checkboxes properly labeled
- [ ] Export options clearly explained
- [ ] Progress indicator during export announced
- [ ] Success/failure messages announced
- [ ] Download link has descriptive text

**Priority**: Medium (secondary feature)

---

### 4.8 Table of Contents (TOC)

#### TOC Generation Wizard

**File**: `src/components/toc/*`

**WCAG Criteria**: 2.1.1 (Keyboard), 4.1.2 (Name, Role, Value)

**Manual Tests**:
- [ ] AI wizard steps keyboard navigable
- [ ] Drag-and-drop reordering has keyboard alternative
- [ ] Chapter list uses proper list markup (`<ul>`, `<li>`)
- [ ] Reorder controls have clear labels: "Move up", "Move down"
- [ ] Focus visible on list items and controls
- [ ] Screen reader announces list structure

**Priority**: Medium (important but not critical path)

---

## 5. Testing Workflow

### 5.1 Pre-Audit Preparation

**Before starting the 24-hour audit**:

1. **Environment Setup**:
   ```bash
   # Start development server
   cd /home/frankbria/projects/auto-author/frontend
   npm run dev
   ```

2. **Browser Setup**:
   - Install axe DevTools extension (see Section 2.1)
   - Configure extension settings for WCAG 2.1 AA
   - Install WAVE extension for visual feedback
   - Install HeadingsMap for document structure validation

3. **Screen Reader Setup**:
   - **Windows**: Install NVDA (free) - https://www.nvaccess.org/download/
   - **macOS**: Enable VoiceOver (built-in) - Cmd+F5
   - **Linux**: Install Orca (usually pre-installed)

4. **Documentation Review**:
   - Review this document thoroughly
   - Familiarize with WCAG 2.1 AA criteria
   - Review component file structure
   - Understand application user flows

### 5.2 Systematic Testing Process

**Phase 1: Automated Scanning (4 hours)**

1. **Component-Level Scanning**:
   ```bash
   # Run existing tests with jest-axe
   npm test

   # Run tests with coverage
   npm run test:coverage
   ```

2. **Page-Level Scanning**:
   - Navigate to each major page
   - Run axe DevTools full page scan
   - Export results to CSV/JSON
   - Document issues by severity

**Pages to Scan**:
- [ ] Homepage / Dashboard (`/`)
- [ ] Sign in / Sign up (`/sign-in`, `/sign-up`)
- [ ] Book creation wizard (`/books/new`)
- [ ] Book detail / Chapter editing (`/books/[id]`)
- [ ] Profile page (`/profile`)
- [ ] Any settings pages

3. **Issue Categorization**:
   - Create spreadsheet with columns:
     - Component/Page
     - Issue Description
     - WCAG Criterion
     - Severity (Critical/Serious/Moderate/Minor)
     - Remediation Plan
     - Time Estimate

---

**Phase 2: Manual Keyboard Testing (6 hours)**

1. **Full Keyboard Navigation**:
   - Unplug mouse (force keyboard-only testing)
   - Tab through every page
   - Test all interactive elements with Enter/Space
   - Verify focus never trapped
   - Check focus indicator always visible

2. **Keyboard Shortcuts**:
   - Test chapter tab shortcuts (Ctrl+1-9)
   - Test any editor shortcuts
   - Verify shortcuts don't conflict with browser/screen reader
   - Document undocumented shortcuts

3. **Focus Management**:
   - Test modal opening: focus moves to modal
   - Test modal closing: focus returns to trigger
   - Test form submission: focus moves to success message or first error
   - Test dynamic content: focus management on content updates

**Testing Checklist** (use this systematically):
- [ ] Tab key reaches all interactive elements
- [ ] Shift+Tab moves backwards correctly
- [ ] Enter activates buttons and links
- [ ] Space activates buttons and toggles checkboxes
- [ ] Arrow keys work in tabs, radio groups, select menus
- [ ] Esc closes modals and dropdowns
- [ ] Home/End work where expected (tabs, select)
- [ ] No focus trapped in any component
- [ ] Focus indicator always visible (3:1 contrast)

---

**Phase 3: Screen Reader Testing (8 hours)**

**Screen Reader Basics**:

- **NVDA (Windows)**:
  - Start/Stop: Ctrl+Alt+N
  - Navigate: Arrow keys (browse mode) or Tab (focus mode)
  - Read all: NVDA+Down arrow
  - Stop reading: Ctrl

- **VoiceOver (macOS)**:
  - Start/Stop: Cmd+F5
  - Navigate: VO keys (Ctrl+Option) + Arrow keys
  - Read all: VO+A
  - Stop reading: Ctrl

- **Orca (Linux)**:
  - Start/Stop: Super+Alt+S
  - Navigate: Arrow keys
  - Read all: Insert+;

**Testing Process**:

1. **Document Structure Test**:
   - Navigate by headings (H key in NVDA)
   - Verify heading hierarchy (no skips)
   - Navigate by landmarks (D key in NVDA)
   - Verify main, nav, complementary regions

2. **Forms Test**:
   - Navigate by form fields (F key in NVDA)
   - Verify all labels announced
   - Verify required fields announced
   - Verify error messages announced
   - Test form submission flow

3. **Interactive Elements Test**:
   - Navigate by buttons (B key in NVDA)
   - Navigate by links (K key in NVDA)
   - Verify button vs link roles correct
   - Verify all elements have accessible names
   - Test custom controls (tabs, editor toolbar)

4. **Dynamic Content Test**:
   - Trigger loading states: verify announcements
   - Submit forms: verify success/error announcements
   - Save content: verify auto-save announcements
   - Test live regions (aria-live)

**Screen Reader Testing Checklist**:
- [ ] All text content announced correctly
- [ ] All images have alt text announced
- [ ] All form labels announced
- [ ] All buttons have clear names
- [ ] All links describe destination
- [ ] Heading hierarchy logical
- [ ] Landmarks properly labeled
- [ ] Tab structure announced (role=tablist, tabpanel)
- [ ] Loading states announced
- [ ] Error messages announced
- [ ] Success messages announced
- [ ] Modal dialogs announced with role and label

---

**Phase 4: Visual Testing (4 hours)**

1. **Color Contrast Testing**:
   - Use axe DevTools contrast checker
   - Use browser extension: WAVE or Colour Contrast Analyser
   - Test all text/background combinations
   - Test focus indicators (3:1 minimum)
   - Test UI component boundaries (3:1 minimum)

**Target Ratios**:
- Regular text (<18pt): 4.5:1 minimum (AA)
- Large text (≥18pt or ≥14pt bold): 3:1 minimum (AA)
- UI components: 3:1 minimum (AA)
- Focus indicators: 3:1 minimum (AA)

2. **Zoom Testing**:
   - Zoom browser to 200% (Ctrl+Plus)
   - Verify no horizontal scrolling (reflow works)
   - Verify no content loss
   - Verify all functionality still works
   - Test at 320px width (mobile minimum)

3. **Text Spacing Testing**:
   - Apply CSS overrides (see Section 3.1.4, criterion 1.4.12)
   - Verify no content loss or overlap
   - Verify all functionality still works

4. **Responsive Design Testing**:
   - Test at mobile (375px), tablet (768px), desktop (1280px)
   - Verify touch targets meet 44x44px on mobile
   - Verify orientation changes work (portrait/landscape)

---

**Phase 5: Documentation & Reporting (2 hours)**

1. **Create Audit Report**:
   ```markdown
   # WCAG 2.1 AA Accessibility Audit Report

   ## Executive Summary
   - Total issues found: [number]
   - Critical: [number]
   - Serious: [number]
   - Moderate: [number]
   - Minor: [number]

   ## Issues by Component
   [Component-by-component breakdown]

   ## Issues by WCAG Criterion
   [Criterion-by-criterion breakdown]

   ## Remediation Plan
   [Prioritized list with time estimates]

   ## Recommendations
   [Process improvements, training needs, etc.]
   ```

2. **Export axe DevTools Results**:
   - Export CSV with all issues
   - Attach to audit report
   - Create GitHub issues for critical/serious items

3. **Update Implementation Plan**:
   - Add accessibility remediation tasks to sprint backlog
   - Prioritize by severity and user impact
   - Estimate effort for each remediation

---

### 5.3 Remediation Prioritization

**Priority 1 - Critical (fix immediately)**:
- Keyboard traps (2.1.2)
- Missing form labels (3.3.2, 4.1.2)
- Insufficient contrast on critical elements (1.4.3)
- Missing alternative text on meaningful images (1.1.1)

**Priority 2 - High (fix within 1 week)**:
- Missing skip navigation (2.4.1)
- Inconsistent focus indicators (2.4.7)
- Poor error messages (3.3.1, 3.3.3)
- Missing page titles (2.4.2)

**Priority 3 - Medium (fix within 1 month)**:
- Minor contrast issues (1.4.3)
- Missing ARIA attributes on custom controls (4.1.2)
- Inconsistent labeling (3.2.4)
- Missing autocomplete attributes (1.3.5)

**Priority 4 - Low (fix as resources allow)**:
- Heading hierarchy improvements (1.3.1)
- Link text improvements (2.4.4)
- Minor ARIA refinements (4.1.2)

---

## 6. Resources & References

### 6.1 Official WCAG Documentation

- **WCAG 2.1 Overview**: https://www.w3.org/WAI/WCAG21/quickref/
- **Understanding WCAG 2.1**: https://www.w3.org/WAI/WCAG21/Understanding/
- **How to Meet WCAG (Quick Reference)**: https://www.w3.org/WAI/WCAG21/quickref/?currentsidebar=%23col_overview&levels=aa

### 6.2 ARIA Authoring Practices

- **ARIA Authoring Practices Guide (APG)**: https://www.w3.org/WAI/ARIA/apg/
- **Tab Pattern**: https://www.w3.org/WAI/ARIA/apg/patterns/tabs/
- **Dialog Pattern**: https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/
- **Alert Dialog Pattern**: https://www.w3.org/WAI/ARIA/apg/patterns/alertdialog/
- **Menu Button Pattern**: https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/

### 6.3 Testing Tools

**Browser Extensions**:
- axe DevTools: https://www.deque.com/axe/devtools/
- WAVE: https://wave.webaim.org/extension/
- Accessibility Insights: https://accessibilityinsights.io/

**Screen Readers**:
- NVDA (Windows - Free): https://www.nvaccess.org/
- JAWS (Windows - Commercial): https://www.freedomscientific.com/products/software/jaws/
- VoiceOver (macOS - Built-in)
- Orca (Linux - Usually pre-installed)

**Color Contrast Checkers**:
- WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
- Colour Contrast Analyser: https://www.tpgi.com/color-contrast-checker/

**Automated Testing**:
- @axe-core/react: https://github.com/dequelabs/axe-core-npm/tree/develop/packages/react
- jest-axe: https://github.com/nickcolley/jest-axe
- Playwright Accessibility Testing: https://playwright.dev/docs/accessibility-testing

### 6.4 Learning Resources

- **WebAIM**: https://webaim.org/ (excellent articles and tutorials)
- **A11y Project**: https://www.a11yproject.com/ (community-driven accessibility resources)
- **Inclusive Components**: https://inclusive-components.design/ (accessible component patterns)
- **Sara Soueidan's Blog**: https://www.sarasoueidan.com/blog/ (CSS and accessibility expert)

### 6.5 Component-Specific Guidance

**Radix UI (used in this project)**:
- Radix UI Accessibility: https://www.radix-ui.com/primitives/docs/overview/accessibility
- Components built with accessibility in mind (Dialog, Tabs, etc.)

**TipTap Editor**:
- TipTap Accessibility: https://tiptap.dev/guide/accessibility
- Considerations for rich text editor accessibility

**Next.js**:
- Next.js Accessibility: https://nextjs.org/docs/accessibility
- Image optimization with alt text
- Built-in font optimization

### 6.6 Internal Documentation

**Auto-Author Specific**:
- CURRENT_SPRINT.md: Current accessibility work status
- IMPLEMENTATION_PLAN.md: Sprint plans and feature specs
- CLAUDE.md: Development standards and component documentation
- LoadingStateManager.tsx: Example of WCAG-compliant component

### 6.7 Compliance & Legal

- **Section 508**: https://www.section508.gov/ (US federal accessibility standard)
- **ADA**: https://www.ada.gov/ (Americans with Disabilities Act)
- **EN 301 549**: https://www.etsi.org/deliver/etsi_en/301500_301599/301549/ (EU accessibility standard)

---

## Next Steps

After completing this preparation:

1. **Schedule 24-Hour Audit Window**:
   - Block dedicated time for comprehensive audit
   - Minimize interruptions
   - Ensure all team members aware of audit in progress

2. **Assign Roles** (if team audit):
   - Automated scanning lead
   - Keyboard testing lead
   - Screen reader testing lead
   - Visual testing lead
   - Documentation/reporting lead

3. **Execute Audit**:
   - Follow systematic testing process (Section 5.2)
   - Document all issues in real-time
   - Take screenshots/videos for reference
   - Export axe DevTools results regularly

4. **Post-Audit**:
   - Compile comprehensive audit report
   - Create prioritized remediation backlog
   - Schedule remediation sprints
   - Plan for ongoing accessibility testing

5. **Continuous Accessibility**:
   - Integrate jest-axe into CI/CD pipeline
   - Add accessibility checks to PR review process
   - Train team on accessibility best practices
   - Schedule quarterly accessibility reviews

---

## Appendix: Common Issues & Quick Fixes

### Issue: Missing Alt Text

**Problem**: `<img>` without alt attribute

**Fix**:
```tsx
// Bad
<img src="/book-cover.jpg" />

// Good
<img src="/book-cover.jpg" alt="Cover of 'The Great Novel' by Author Name" />

// Decorative (empty alt)
<img src="/decorative-line.svg" alt="" />
```

---

### Issue: Button Without Accessible Name

**Problem**: Icon button without text

**Fix**:
```tsx
// Bad
<button><TrashIcon /></button>

// Good - Option 1: aria-label
<button aria-label="Delete book"><TrashIcon /></button>

// Good - Option 2: visually hidden text
<button>
  <TrashIcon />
  <span className="sr-only">Delete book</span>
</button>
```

---

### Issue: Form Input Without Label

**Problem**: Input field missing associated label

**Fix**:
```tsx
// Bad
<input type="text" placeholder="Enter title" />

// Good
<label htmlFor="book-title">Book Title</label>
<input type="text" id="book-title" name="title" />
```

---

### Issue: Low Contrast Text

**Problem**: Text doesn't meet 4.5:1 contrast ratio

**Fix**:
```tsx
// Bad (assuming gray-400 on white background)
<p className="text-gray-400">Description text</p>

// Good (use darker gray)
<p className="text-gray-700">Description text</p>

// Or check TailwindCSS contrast:
// https://www.tailwindcss-color-contrast-checker.vercel.app/
```

---

### Issue: Missing Focus Indicator

**Problem**: Custom component removes focus outline

**Fix**:
```css
/* Bad */
button:focus {
  outline: none;
}

/* Good */
button:focus-visible {
  outline: 2px solid #0066cc;
  outline-offset: 2px;
}
```

---

### Issue: Keyboard Trap in Modal

**Problem**: Focus escapes modal to background content

**Fix**: Use Radix UI Dialog or ensure focus trap:
```tsx
import { Dialog } from '@radix-ui/react-dialog';

// Radix handles focus trap automatically
<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <Dialog.Content>
    {/* Modal content */}
  </Dialog.Content>
</Dialog>
```

---

**End of Accessibility Audit Preparation Document**

**Version**: 1.0
**Last Updated**: 2025-10-12
**Next Review**: After 24-hour audit completion
