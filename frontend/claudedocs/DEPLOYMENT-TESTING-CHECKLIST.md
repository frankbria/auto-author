# Auto-Author Deployment Testing Checklist

**Environment**: ClawCloud Production (dev.autoauthor.app)
**Date**: _____________
**Tester**: _____________

---

## Document Purpose

This checklist provides comprehensive end-to-end testing for Auto-Author deployment validation, including:
- Pre-flight system health checks
- Complete user journey testing (book creation → TOC generation → chapter editing → export)
- Copy-paste test data for all forms with field constraints
- Regression testing for critical features
- Performance and security validation

---

## 🤖 Automation Coverage

**Automation Status**: 85% of this checklist is automated using Playwright browser automation.

### Automation Indicators
- **✅ 🤖** Fully automatable with Playwright
- **⚠️ 🤖** Partially automatable (requires workaround or alternative approach)
- **❌ 👤** Manual test required
- **🔧** Requires backend/CI integration

### Coverage Summary
| Test Category | Automatable | Partially | Manual | Total |
|--------------|-------------|-----------|--------|-------|
| Pre-Flight Checks | 60% | 30% | 10% | 100% |
| User Journey | 95% | 5% | 0% | 100% |
| Advanced Features | 75% | 0% | 25% | 100% |
| Security & Performance | 70% | 20% | 10% | 100% |
| Regression Tests | 95% | 5% | 0% | 100% |

### Implementation Details
See [DEPLOYMENT_AUTOMATION_PLAN.md](./DEPLOYMENT_AUTOMATION_PLAN.md) for:
- Complete automation architecture
- Playwright test structure
- MCP integration points
- CI/CD workflow
- Phase-by-phase implementation plan

---

## Table of Contents

1. [Pre-Flight Checks](#pre-flight-checks)
2. [User Journey: Book Creation to Export](#user-journey-book-creation-to-export)
3. [Advanced Features Testing](#advanced-features-testing)
4. [Security & Performance Checks](#security--performance-checks)
5. [Regression Tests](#regression-tests)
6. [Fixes Applied](#fixes-applied-2025-10-20)
7. [Final Verification & Sign-Off](#final-verification--sign-off)

---

## Pre-Flight Checks

### Server Health

```bash
ssh root@47.88.89.175
```

- [x] **PM2 Status**: `pm2 status` **🔧 Backend/CI**
  - [x] `auto-author-frontend` shows **online**
  - [x] `auto-author-backend` shows **online**

- [x] **Backend Logs**: `pm2 logs auto-author-backend --lines 20 --nostream` **🔧 Backend/CI**
  - [x] No **Traceback** or **Error** messages

- [x] **Frontend Logs**: `pm2 logs auto-author-frontend --lines 20 --nostream` **🔧 Backend/CI**
  - [x] Shows "✓ Ready" message

### CORS Configuration

```bash
curl -I -X OPTIONS https://api.dev.autoauthor.app/api/v1/books/ \
  -H "Origin: https://dev.autoauthor.app" \
  -H "Access-Control-Request-Method: GET" | grep access-control
```

- [x] Response includes: `access-control-allow-origin: https://dev.autoauthor.app` **✅ 🤖 Automated**
- [x] Response includes: `access-control-allow-credentials: true` **✅ 🤖 Automated**

### API Health

```bash
curl -s https://api.dev.autoauthor.app/ | head -20
```

- [x] Response includes: `"message":"Welcome to the Auto Author API"` **✅ 🤖 Automated**
- [x] No error messages **✅ 🤖 Automated**

---

## User Journey: Book Creation to Export

This section walks through the complete authoring workflow from creating a book to exporting it.

### Step 1: Homepage & Authentication

- [x] Open browser (Chrome/Firefox/Safari) **✅ 🤖 Automated**
- [x] Navigate to: `https://dev.autoauthor.app` **✅ 🤖 Automated**
- [x] Page loads without errors **✅ 🤖 Automated**
- [x] Open DevTools (F12) → **Console** tab **✅ 🤖 Automated**
- [x] **No red error messages** in console **✅ 🤖 Automated**
- [x] **No CORS errors** **✅ 🤖 Automated**
- [x] **No CSP errors** **✅ 🤖 Automated**
- [x] Clerk sign-in button visible **✅ 🤖 Automated**

**Sign In:**

- [x] Click "Sign In" button **✅ 🤖 Automated**
- [x] Clerk authentication modal opens **✅ 🤖 Automated**
- [x] No CSP errors when modal opens **✅ 🤖 Automated**
- [x] Enter credentials and sign in **⚠️ 🤖 Requires test account**
- [x] Successfully authenticated **✅ 🤖 Automated**
- [x] Redirected to `/dashboard` after sign-in **✅ 🤖 Automated**

---

### Step 2: Dashboard & API Connection

- [x] Dashboard page loads **✅ 🤖 Automated**
- [x] Open DevTools → **Network** tab **✅ 🤖 Automated**
- [x] Clear network log (trash can icon) **✅ 🤖 Automated**
- [x] Refresh page or click "Books" in navigation **✅ 🤖 Automated**
- [x] Look for request to: `api.dev.autoauthor.app/api/v1/books` **✅ 🤖 Automated**
- [x] Request shows **200 OK** or **empty array** response **✅ 🤖 Automated**
- [x] **No 500 errors** **✅ 🤖 Automated**
- [x] **No CORS errors** **✅ 🤖 Automated**
- [x] Response headers include `access-control-allow-origin` **✅ 🤖 Automated**

---

### Step 3: Create New Book

- [x] Click "Create New Book" button on the dashboard (opens the BookCreationWizard modal; the `/dashboard/new-book` page was removed in #205) **✅ 🤖 Automated**
- [x] Form displays correctly **✅ 🤖 Automated**
- [x] Form background is **NOT transparent** (should be visible and readable) **✅ 🤖 Automated**

**Test Data (Copy & Paste)**:

```
Book Title: Sustainable Urban Gardening: A Practical Guide

Description: A comprehensive guide for city dwellers to grow fresh produce in limited spaces

Genre: Select "business" from dropdown

Target Audience: Urban residents interested in growing their own food in limited spaces
```

**Field Constraints**:
- Title: Min 1 char, Max 100 chars ✅
- Description: Max 5000 chars ✅
- Genre: Required selection ✅
- Target Audience: Max 100 chars ✅

**Execute:**

- [x] Fill in Book Title **✅ 🤖 Automated**
- [x] Fill in Description **✅ 🤖 Automated**
- [x] Select Genre from dropdown **✅ 🤖 Automated**
- [x] Fill in Target Audience **✅ 🤖 Automated**
- [x] Click "Create Book" or "Submit" **✅ 🤖 Automated**
- [x] Monitor Network tab for POST to `/api/v1/books/` **✅ 🤖 Automated**
- [x] Request includes `Authorization: Bearer ...` header **✅ 🤖 Automated**
- [x] Response is **201 Created** or **200 OK** (NOT 500 ✅ FIXED) **✅ 🤖 Automated**
- [x] Redirected to book detail page (`/dashboard/books/[bookId]`) **✅ 🤖 Automated**
- [x] New book appears in books list **✅ 🤖 Automated**

**Book ID from URL**: _____________ **✅ 🤖 Captured automatically**

---

### Step 4: Add Book Summary

**Required before TOC generation**

- [ ] From book detail page, navigate to `/dashboard/books/[bookId]/summary` **✅ 🤖 Automated**
- [ ] Summary form page loads **✅ 🤖 Automated**
- [ ] Character counter shows "0 characters" **✅ 🤖 Automated**
- [ ] Minimum requirement shown: "Minimum: 30 characters" **✅ 🤖 Automated**

**Test Data (Copy & Paste) - 558 characters**:

```
This practical guide teaches urban dwellers how to create productive gardens in small spaces. Topics include container gardening basics, vertical growing techniques for balconies and patios, composting in urban environments, seasonal planning for year-round harvests, and selecting the best vegetables and herbs for limited space. Readers will learn water-efficient irrigation methods, organic pest control strategies, and how to maximize yields in apartments and small yards. The book includes detailed growing calendars, troubleshooting guides, and case studies from successful urban gardeners.
```

**Field Constraints**:
- Minimum: 30 characters ✅
- Maximum: 2000 characters ✅
- Must be in English (no Cyrillic, Arabic, CJK characters) ✅
- No offensive language ✅

**Execute:**

- [ ] Paste test data into summary field **✅ 🤖 Automated**
- [ ] Character counter updates correctly (should show ~558 characters) **✅ 🤖 Automated**
- [ ] Voice input button visible (🎤 optional test) **✅ 🤖 Automated**
- [ ] No validation errors appear **✅ 🤖 Automated**
- [ ] Click "Continue to TOC Generation" button **✅ 🤖 Automated**
- [ ] Redirected to `/dashboard/books/[bookId]/generate-toc` **✅ 🤖 Automated**

---

### Step 5: Generate Table of Contents (TOC Wizard)

**Step 5a: Readiness Check**

- [ ] TOC generation page loads **✅ 🤖 Automated**
- [ ] System automatically checks summary readiness **✅ 🤖 Automated**
- [ ] Loading indicator appears during AI analysis **✅ 🤖 Automated**
- [ ] If summary too short: "Not Ready" message with guidance **✅ 🤖 Automated**
- [ ] If summary adequate: Proceeds to questions automatically **✅ 🤖 Automated**

**Step 5b: Clarifying Questions**

- [ ] 5-10 clarifying questions appear **✅ 🤖 Automated**
- [ ] Questions are relevant to book topic **❌ 👤 Manual judgment**
- [ ] Each question has a text input field **✅ 🤖 Automated**
- [ ] Character limit shown for each response (typically 50-500 chars) **✅ 🤖 Automated**

**Test Data for Questions (Copy & Paste)**:

```
Q1 - Main Topics:
This book covers container gardening, vertical growing, composting, seasonal planning, and space-efficient techniques for urban environments.

Q2 - Target Readers:
Beginners with no gardening experience living in apartments or homes with limited outdoor space who want to grow fresh food.

Q3 - Key Takeaways:
Readers will learn that productive gardening is possible in small spaces, understand basic techniques, and feel motivated to start their own urban garden.

Q4 - Scope:
The book focuses on vegetables, herbs, and small fruits suitable for containers and small urban spaces, not large-scale farming.

Q5 - Unique Approach:
Emphasizes practical, budget-friendly solutions using recycled materials and minimal space, with real-world examples from city gardeners.
```

**Execute:**

- [ ] Answer all clarifying questions (paste test data) **✅ 🤖 Automated**
- [ ] Click "Generate TOC" or "Continue" button **✅ 🤖 Automated**
- [ ] Loading indicator appears **✅ 🤖 Automated**
- [ ] AI processes responses (15-60 seconds) **⚠️ 🤖 Timeout handling required**
- [ ] Wait for generation to complete **✅ 🤖 Automated**

**Step 5c: TOC Review & Confirmation**

- [ ] Generated TOC appears **✅ 🤖 Automated**
- [ ] TOC contains 5-15 chapters **✅ 🤖 Automated**
- [ ] Each chapter has a title **✅ 🤖 Automated**
- [ ] Chapters are logically organized **❌ 👤 Manual judgment**
- [ ] Option to edit chapter titles visible **✅ 🤖 Automated**
- [ ] Option to add/remove chapters visible **✅ 🤖 Automated**
- [ ] "Save TOC" or "Confirm" button present **✅ 🤖 Automated**

**Execute:**

- [ ] Review generated chapters **❌ 👤 Manual review**
- [ ] (Optional) Edit a chapter title to test edit functionality **✅ 🤖 Automated**
- [ ] Click "Save TOC" or "Confirm" **✅ 🤖 Automated**
- [ ] Success message or navigation occurs **✅ 🤖 Automated**
- [ ] Redirected to book detail page **✅ 🤖 Automated**

---

### Step 6: View Book with Generated TOC

- [ ] Navigate to `/dashboard/books/[bookId]` **✅ 🤖 Automated**
- [ ] Book title displayed correctly **✅ 🤖 Automated**
- [ ] Table of Contents (TOC) displays **✅ 🤖 Automated**
- [ ] Multiple chapters listed (5-15) **✅ 🤖 Automated**
- [ ] Each chapter shows:
  - [ ] Chapter number **✅ 🤖 Automated**
  - [ ] Chapter title **✅ 🤖 Automated**
  - [ ] Status indicator (Draft, In Progress, Completed) **✅ 🤖 Automated**
  - [ ] Word count (0 for new chapters) **✅ 🤖 Automated**
- [ ] Click on first chapter to open editor **✅ 🤖 Automated**

---

### Step 7: Chapter Editor & Content Creation

**Step 7a: Open Chapter Editor**

- [ ] Chapter page loads (`/dashboard/books/[bookId]/chapters/[chapterId]`) **✅ 🤖 Automated**
- [ ] Chapter title displayed in breadcrumb **✅ 🤖 Automated**
- [ ] Chapter tabs visible on left sidebar (vertical layout) **✅ 🤖 Automated**
- [ ] Rich text editor loaded **✅ 🤖 Automated**
- [ ] Editor toolbar visible (Bold, Italic, Heading, Lists, etc.) **✅ 🤖 Automated**
- [ ] Auto-save indicator present **✅ 🤖 Automated**
- [ ] Word count shows "0 words" **✅ 🤖 Automated**

**Step 7b: Test Rich Text Editor**

- [ ] Click in editor area **✅ 🤖 Automated**
- [ ] Type test text: "This is a test paragraph about urban gardening." **✅ 🤖 Automated**
- [ ] Text appears in editor **✅ 🤖 Automated**
- [ ] Select text and click **Bold** button **✅ 🤖 Automated**
- [ ] Text becomes bold **✅ 🤖 Automated**
- [ ] Click **Heading** dropdown and select "Heading 2" **✅ 🤖 Automated**
- [ ] Text converts to H2 heading **✅ 🤖 Automated**
- [ ] Auto-save indicator shows "Saving..." then "Saved" **✅ 🤖 Automated**
- [ ] No console errors **✅ 🤖 Automated**

**Step 7c: AI Draft Generation (Q&A to Narrative)**

- [ ] Look for "Generate Draft" or "AI Assistant" button/panel **✅ 🤖 Automated**
- [ ] Click to open Q&A wizard **✅ 🤖 Automated**
- [ ] Questions appear specific to this chapter **✅ 🤖 Automated**
- [ ] Answer 3-5 questions about chapter content **✅ 🤖 Automated**

**Test Data for Chapter Q&A (Copy & Paste)**:

```
Q: What are the main topics for this chapter?
A: Introduction to container gardening, choosing the right containers, soil selection, and drainage requirements for successful urban gardens.

Q: What should readers learn by the end?
A: Readers will understand how to select appropriate containers, prepare proper soil mixes, and ensure adequate drainage for healthy plant growth in limited spaces.

Q: What examples or case studies should be included?
A: Show examples of different container types (terracotta, plastic, fabric), a recipe for DIY potting mix, and a troubleshooting guide for common drainage problems.
```

**Execute:**

- [ ] Paste answers into Q&A form **✅ 🤖 Automated**
- [ ] Click "Generate Draft" button **✅ 🤖 Automated**
- [ ] Loading indicator appears **✅ 🤖 Automated**
- [ ] AI generates draft content (15-60 seconds - Performance Budget: <3000ms) **⚠️ 🤖 Timeout handling required**
- [ ] Generated content appears in editor **✅ 🤖 Automated**
- [ ] Content is narrative prose (not Q&A format) **✅ 🤖 Automated**
- [ ] Content length: 200-800 words **✅ 🤖 Automated**
- [ ] Click "Insert Draft" or content auto-inserts **✅ 🤖 Automated**
- [ ] Word count updates to show new content **✅ 🤖 Automated**
- [ ] Auto-save triggers automatically **✅ 🤖 Automated**

**Step 7d: Chapter Tabs & Navigation**

- [ ] Open a second chapter tab by clicking another chapter **✅ 🤖 Automated**
- [ ] Chapter tabs appear in sidebar **✅ 🤖 Automated**
- [ ] Can switch between chapters using tabs **✅ 🤖 Automated**
- [ ] Each tab shows:
  - [ ] Chapter title (truncated if too long) **✅ 🤖 Automated**
  - [ ] Status indicator (colored dot) **✅ 🤖 Automated**
  - [ ] Unsaved changes indicator (orange dot if edited) **✅ 🤖 Automated**
  - [ ] Close button (X with 44x44px touch target) **✅ 🤖 Automated**
- [ ] Close one tab using X button **✅ 🤖 Automated**
- [ ] Tab closes correctly **✅ 🤖 Automated**
- [ ] Active content updates to remaining tab **✅ 🤖 Automated**

**Keyboard Navigation (WCAG 2.1 Compliance)**:

- [ ] Press **Tab** to focus on chapter tabs **✅ 🤖 Automated**
- [ ] Press **Enter** or **Space** to open focused chapter **✅ 🤖 Automated**
- [ ] Press **Arrow Keys** to navigate between tabs **✅ 🤖 Automated**
- [ ] Press **Escape** to close modals **✅ 🤖 Automated**
- [ ] Focus indicators are visible **✅ 🤖 Automated**
- [ ] All interactive elements keyboard accessible **✅ 🤖 Automated**

---

### Step 8: Export Book

- [ ] Navigate to `/dashboard/books/[bookId]/export` **✅ 🤖 Automated**
- [ ] Export options page loads **✅ 🤖 Automated**
- [ ] Format selection available:
  - [ ] PDF **✅ 🤖 Automated**
  - [ ] DOCX (Microsoft Word) **✅ 🤖 Automated**

**Test PDF Export:**

- [ ] Select **PDF** format **✅ 🤖 Automated**
- [ ] Enable "Include cover page" **✅ 🤖 Automated**
- [ ] Enable "Include table of contents" **✅ 🤖 Automated**
- [ ] Click "Export" button **✅ 🤖 Automated**
- [ ] Export progress modal appears **✅ 🤖 Automated**
- [ ] Progress bar shows processing **✅ 🤖 Automated**
- [ ] Operation completes within **5 seconds** (Performance Budget ✅) **✅ 🤖 Automated**
- [ ] File downloads automatically **✅ 🤖 Automated**
- [ ] File opens correctly in PDF viewer **⚠️ 🤖 File validation**
- [ ] Content is formatted properly **⚠️ 🤖 PDF parsing required**
- [ ] Chapters are present **⚠️ 🤖 PDF parsing required**
- [ ] Table of contents is functional (hyperlinks work) **⚠️ 🤖 PDF parsing required**

**Test DOCX Export:**

- [ ] Select **DOCX** format **✅ 🤖 Automated**
- [ ] Configure options (cover page, TOC) **✅ 🤖 Automated**
- [ ] Click "Export" **✅ 🤖 Automated**
- [ ] Export progress appears **✅ 🤖 Automated**
- [ ] Operation completes within **5 seconds** (Performance Budget ✅) **✅ 🤖 Automated**
- [ ] File downloads **✅ 🤖 Automated**
- [ ] File opens in Microsoft Word/LibreOffice **⚠️ 🤖 File validation**
- [ ] Content is properly formatted **⚠️ 🤖 DOCX parsing required**
- [ ] Chapters have correct headings **⚠️ 🤖 DOCX parsing required**
- [ ] Table of contents is functional **⚠️ 🤖 DOCX parsing required**

---

## Advanced Features Testing

### Voice Input Integration

- [ ] Navigate to book summary page **✅ 🤖 Automated**
- [ ] Click "🎤 Voice Input" button **✅ 🤖 Automated**
- [ ] Browser asks for microphone permission **❌ 👤 Cannot automate in headless**
- [ ] Grant permission **❌ 👤 Manual interaction required**
- [ ] Button shows "Listening..." with red background **❌ 👤 Requires microphone**
- [ ] Speak test phrase: "This is a test of voice input functionality for urban gardening." **❌ 👤 Requires microphone**
- [ ] Text appears in summary field as you speak **❌ 👤 Requires microphone**
- [ ] Click "Stop" button to end recording **⚠️ 🤖 UI interaction only**
- [ ] Voice input stops **❌ 👤 Requires microphone**
- [ ] Text saved correctly in field **⚠️ 🤖 Can mock Speech API**
- [ ] Character counter updates **⚠️ 🤖 Can mock Speech API**

### Auto-Save System

**Normal Auto-Save:**

- [ ] Open chapter editor **✅ 🤖 Automated**
- [ ] Type text in editor: "Testing auto-save functionality." **✅ 🤖 Automated**
- [ ] Watch auto-save indicator **✅ 🤖 Automated**
- [ ] Shows "Saving..." after **3 seconds** (debounce) **✅ 🤖 Automated**
- [ ] Shows "Saved" when complete (within **1 second** - Performance Budget ✅) **✅ 🤖 Automated**
- [ ] Refresh page (F5) **✅ 🤖 Automated**
- [ ] Content persists after refresh **✅ 🤖 Automated**
- [ ] No data loss **✅ 🤖 Automated**

**Network Failure Resilience:**

- [ ] Open chapter editor **✅ 🤖 Automated**
- [ ] Open DevTools → Network tab **✅ 🤖 Automated**
- [ ] Set throttling to "Offline" **✅ 🤖 Automated**
- [ ] Type text in editor: "Testing offline auto-save." **✅ 🤖 Automated**
- [ ] Auto-save attempts and fails gracefully **✅ 🤖 Automated**
- [ ] Data saved to **localStorage** (backup) **✅ 🤖 Automated**
- [ ] Error notification appears: "Unable to save. Changes saved locally." **✅ 🤖 Automated**
- [ ] Set throttling back to "No throttling" **✅ 🤖 Automated**
- [ ] Auto-save retries automatically **✅ 🤖 Automated**
- [ ] Succeeds and syncs to server **✅ 🤖 Automated**
- [ ] Success notification appears **✅ 🤖 Automated**

### Delete Book Functionality

**Type-to-Confirm Pattern (Data Loss Prevention):**

- [ ] Navigate to dashboard **✅ 🤖 Automated**
- [ ] Find test book in list **✅ 🤖 Automated**
- [ ] Click "Delete" button or three-dot menu → Delete **✅ 🤖 Automated**
- [ ] Confirmation modal appears **✅ 🤖 Automated**
- [ ] Modal shows warning: "This action cannot be undone" **✅ 🤖 Automated**
- [ ] Modal shows: "Type DELETE to confirm" **✅ 🤖 Automated**
- [ ] Type "delete" (lowercase) → Button stays **disabled** ✅ **✅ 🤖 Automated**
- [ ] Type "delETE" (mixed case) → Button stays **disabled** ✅ **✅ 🤖 Automated**
- [ ] Clear field and type "DELETE" (uppercase) → Button becomes **enabled** ✅ **✅ 🤖 Automated**
- [ ] Click "Delete Book" button **✅ 🤖 Automated**
- [ ] Modal shows processing indicator **✅ 🤖 Automated**
- [ ] Book deleted successfully **✅ 🤖 Automated**
- [ ] Redirected to dashboard **✅ 🤖 Automated**
- [ ] Book no longer appears in list **✅ 🤖 Automated**
- [ ] Audit log recorded (check backend logs if needed) **🔧 Backend verification**

---

## Security & Performance Checks

### CSP Headers - Frontend

```bash
curl -I https://dev.autoauthor.app | grep content-security-policy
```

- [ ] Includes: `connect-src` with `api.dev.autoauthor.app` **✅ 🤖 Automated**
- [ ] Includes: `script-src` with `clerk.accounts.dev` **✅ 🤖 Automated**
- [ ] No violations in browser console **✅ 🤖 Automated**

### CSP Headers - Backend

```bash
curl -I https://api.dev.autoauthor.app/docs | grep content-security-policy
```

- [ ] Includes: `script-src` with `cdn.jsdelivr.net` **✅ 🤖 Automated**
- [ ] Includes: `style-src` with `cdn.jsdelivr.net` **✅ 🤖 Automated**
- [ ] Includes: `img-src` with `fastapi.tiangolo.com` **✅ 🤖 Automated**

### Swagger API Documentation

- [ ] Navigate to: `https://api.dev.autoauthor.app/docs` **✅ 🤖 Automated**
- [ ] Swagger UI interface loads completely **✅ 🤖 Automated**
- [ ] **No white/blank page** **✅ 🤖 Automated**
- [ ] No CSP errors in console **✅ 🤖 Automated**
- [ ] Can expand/collapse endpoints **✅ 🤖 Automated**
- [ ] FastAPI logo/favicon loads **✅ 🤖 Automated**
- [ ] Can test endpoints with "Try it out" button **⚠️ 🤖 Interactive API testing**

### Performance - Core Web Vitals

- [ ] Open: `https://dev.autoauthor.app` **✅ 🤖 Automated**
- [ ] Open DevTools → **Lighthouse** tab **⚠️ 🤖 Lighthouse integration**
- [ ] Click "Analyze page load" **⚠️ 🤖 Lighthouse integration**
- [ ] Performance score: _______ (target: **>80** ✅) **⚠️ 🤖 Lighthouse integration**
- [ ] LCP (Largest Contentful Paint): _______ (target: **<2.5s** ✅) **✅ 🤖 Automated**
- [ ] CLS (Cumulative Layout Shift): _______ (target: **<0.1** ✅) **✅ 🤖 Automated**

### Performance - Operation Budgets

- [ ] **TOC Generation**: Completes in < **3000ms** ✅ **✅ 🤖 Automated**
- [ ] **Export (PDF/DOCX)**: Completes in < **5000ms** ✅ **✅ 🤖 Automated**
- [ ] **Chapter Auto-Save**: Completes in < **1000ms** ✅ **✅ 🤖 Automated**
- [ ] **Page Navigation**: < **500ms** ✅ **✅ 🤖 Automated**

---

## Regression Tests

### Critical User Flows

**Flow 1: Sign Out → Sign In → Dashboard**

- [ ] Click sign out button **✅ 🤖 Automated**
- [ ] Redirected to homepage **✅ 🤖 Automated**
- [ ] Clerk session cleared **✅ 🤖 Automated**
- [ ] Click "Sign In" **✅ 🤖 Automated**
- [ ] Clerk modal appears **✅ 🤖 Automated**
- [ ] Sign in successful **✅ 🤖 Automated**
- [ ] Redirected to dashboard **✅ 🤖 Automated**
- [ ] Books list loads **✅ 🤖 Automated**
- [ ] User data persists **✅ 🤖 Automated**

**Flow 2: Edit Book Metadata**

- [ ] Open book detail page **✅ 🤖 Automated**
- [ ] Click "Edit" button **✅ 🤖 Automated**
- [ ] Edit mode activates **✅ 🤖 Automated**
- [ ] Change book title to: "Updated Title - Deployment Test" **✅ 🤖 Automated**
- [ ] Change description **✅ 🤖 Automated**
- [ ] Click "Save" **✅ 🤖 Automated**
- [ ] Title updates successfully **✅ 🤖 Automated**
- [ ] Description updates **✅ 🤖 Automated**
- [ ] No errors in console **✅ 🤖 Automated**
- [ ] Changes persist on page refresh **✅ 🤖 Automated**

**Flow 3: Multiple Chapter Tabs**

- [ ] Open book with 5+ chapters **✅ 🤖 Automated**
- [ ] Open 5 different chapter tabs **✅ 🤖 Automated**
- [ ] Each tab loads in sidebar **✅ 🤖 Automated**
- [ ] Switch between tabs multiple times **✅ 🤖 Automated**
- [ ] Each tab loads correct content **✅ 🤖 Automated**
- [ ] Close 2 tabs using X button **✅ 🤖 Automated**
- [ ] Remaining 3 tabs still functional **✅ 🤖 Automated**
- [ ] Tab order persists **✅ 🤖 Automated**
- [ ] Active tab state saved **✅ 🤖 Automated**

**Flow 4: Keyboard Shortcuts**

- [ ] In chapter editor, select text **✅ 🤖 Automated**
- [ ] Press `Ctrl+B` (or `Cmd+B` on Mac) **✅ 🤖 Automated**
- [ ] Selected text becomes **bold** **✅ 🤖 Automated**
- [ ] Press `Ctrl+I` (or `Cmd+I`) **✅ 🤖 Automated**
- [ ] Selected text becomes *italic* **✅ 🤖 Automated**
- [ ] Press `Ctrl+S` (or `Cmd+S`) **✅ 🤖 Automated**
- [ ] Document saves (auto-save may prevent default) **✅ 🤖 Automated**
- [ ] Press `Escape` **✅ 🤖 Automated**
- [ ] Closes modal (if open) **✅ 🤖 Automated**

---

## Fixes Applied (2025-10-20)

### Issue 1: 500 Error on Book Creation ✅ FIXED

**Root Cause**: `audit_request()` function in `backend/app/api/dependencies.py` was missing the `metadata` parameter, but multiple endpoints were calling it with this argument.

**Fix Applied**:

- Added `metadata: Optional[Dict] = None` parameter to function signature
- Updated function to merge metadata into the details dictionary
- Deployed to production server at `/opt/auto-author/current/backend/app/api/dependencies.py`
- Backend service restarted successfully

**Testing**: Step 3 (Create New Book) now completes successfully with 201 Created response

**Status**: ✅ Verified in Step 3

---

### Issue 2: New Book Page Transparency ✅ FIXED

**Root Cause**: Form background `bg-zinc-800` appeared transparent against `bg-zinc-950` page background, making text hard to read.

**Fix Applied**:

- Changed form background from `bg-zinc-800` to `bg-zinc-900` (darker, more opaque)
- Added `border border-zinc-700` for better visual definition
- Added `shadow-xl` for depth and separation
- Deployed to production at `/opt/auto-author/current/frontend/src/app/dashboard/new-book/page.tsx`
- Frontend rebuilt and service restarted successfully

**Testing**: Step 3 form should be clearly visible and readable

**Status**: ✅ Verified in Step 3

---

### Deployment Status

- Both fixes committed to git: `708a871`
- Backend service: ✅ Running (PM2 process 3)
- Frontend service: ✅ Running (PM2 process 2)
- Ready for continued testing

---

## Final Verification & Sign-Off

### No Errors Checklist

- [ ] No CORS errors in any console **✅ 🤖 Automated**
- [ ] No CSP violations in any console **✅ 🤖 Automated**
- [ ] No 500 errors in Network tab **✅ 🤖 Automated**
- [ ] No 401/403 errors on authenticated endpoints **✅ 🤖 Automated**
- [ ] All PM2 processes remain **online** **🔧 Backend/CI**
- [ ] Backend logs show no errors during testing **🔧 Backend/CI**

### Functional Completeness

- [ ] User can sign in **✅ 🤖 Automated**
- [ ] User can create a book with metadata **✅ 🤖 Automated**
- [ ] User can add a book summary **✅ 🤖 Automated**
- [ ] User can generate TOC with AI wizard **✅ 🤖 Automated**
- [ ] User can view books with chapters **✅ 🤖 Automated**
- [ ] User can edit chapters with rich text editor **✅ 🤖 Automated**
- [ ] User can generate AI drafts from Q&A **✅ 🤖 Automated**
- [ ] User can use keyboard shortcuts **✅ 🤖 Automated**
- [ ] User can export books (PDF/DOCX) **✅ 🤖 Automated**
- [ ] User can delete books safely **✅ 🤖 Automated**
- [ ] API documentation accessible (Swagger) **✅ 🤖 Automated**
- [ ] No broken features from previous version **✅ 🤖 Automated**

---

## Sign-Off

**All tests passed**: ☐ Yes  ☐ No

**Issues found**:

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

**Deployment Status**: ☐ Approved  ☐ Needs Fixes

**Tester Signature**: _______________ **Date**: _______________

---

## Test Data Reference

Quick reference for copy-paste test data:

### Book Creation

```
Title: Sustainable Urban Gardening: A Practical Guide
Description: A comprehensive guide for city dwellers to grow fresh produce in limited spaces
Genre: business
Target Audience: Urban residents interested in growing their own food in limited spaces
```

### Book Summary (558 chars)

```
This practical guide teaches urban dwellers how to create productive gardens in small spaces. Topics include container gardening basics, vertical growing techniques for balconies and patios, composting in urban environments, seasonal planning for year-round harvests, and selecting the best vegetables and herbs for limited space. Readers will learn water-efficient irrigation methods, organic pest control strategies, and how to maximize yields in apartments and small yards. The book includes detailed growing calendars, troubleshooting guides, and case studies from successful urban gardeners.
```

### TOC Questions Responses

```
Q1: This book covers container gardening, vertical growing, composting, seasonal planning, and space-efficient techniques for urban environments.

Q2: Beginners with no gardening experience living in apartments or homes with limited outdoor space who want to grow fresh food.

Q3: Readers will learn that productive gardening is possible in small spaces, understand basic techniques, and feel motivated to start their own urban garden.

Q4: The book focuses on vegetables, herbs, and small fruits suitable for containers and small urban spaces, not large-scale farming.

Q5: Emphasizes practical, budget-friendly solutions using recycled materials and minimal space, with real-world examples from city gardeners.
```

### Chapter Q&A Responses

```
Main Topics: Introduction to container gardening, choosing the right containers, soil selection, and drainage requirements for successful urban gardens.

Learning Outcomes: Readers will understand how to select appropriate containers, prepare proper soil mixes, and ensure adequate drainage for healthy plant growth in limited spaces.

Examples: Show examples of different container types (terracotta, plastic, fabric), a recipe for DIY potting mix, and a troubleshooting guide for common drainage problems.
```

---

## Quick Troubleshooting

### If you see: "Access blocked by CORS policy"

```bash
ssh root@47.88.89.175
grep BACKEND_CORS_ORIGINS /opt/auto-author/current/backend/.env
# Should include: "https://dev.autoauthor.app"
# If missing, add it and restart: pm2 restart auto-author-backend
```

### If you see: 500 Internal Server Error

```bash
ssh root@47.88.89.175
pm2 logs auto-author-backend --lines 50 | grep -A 10 "Error\|Traceback"
```

### If Swagger UI is blank/white

Check console for "refused to load" errors. **Fix**: Backend CSP headers need `cdn.jsdelivr.net`.

### If frontend can't connect to API

1. Frontend `.env.production` has correct API URL: `NEXT_PUBLIC_API_URL=https://api.dev.autoauthor.app/api/v1`
2. Frontend was rebuilt after .env change: `npm run build`
3. PM2 restarted: `pm2 restart auto-author-frontend`

---

## Rollback Procedure

**If critical issues found**:

1. ☐ Document all issues in Sign-Off section
2. ☐ Notify deployment team
3. ☐ Execute rollback:

```bash
ssh root@47.88.89.175
cd /opt/auto-author
# Restore from backup tarball if available
tar -xzf backup-[timestamp].tar.gz -C current/
pm2 restart all
```

4. ☐ Verify rollback successful by re-running Pre-Flight Checks
