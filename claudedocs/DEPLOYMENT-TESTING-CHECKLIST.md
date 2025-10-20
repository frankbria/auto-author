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

- [x] **PM2 Status**: `pm2 status`
  - [x] `auto-author-frontend` shows **online**
  - [x] `auto-author-backend` shows **online**

- [x] **Backend Logs**: `pm2 logs auto-author-backend --lines 20 --nostream`
  - [x] No **Traceback** or **Error** messages

- [x] **Frontend Logs**: `pm2 logs auto-author-frontend --lines 20 --nostream`
  - [x] Shows "✓ Ready" message

### CORS Configuration

```bash
curl -I -X OPTIONS https://api.dev.autoauthor.app/api/v1/books/ \
  -H "Origin: https://dev.autoauthor.app" \
  -H "Access-Control-Request-Method: GET" | grep access-control
```

- [x] Response includes: `access-control-allow-origin: https://dev.autoauthor.app`
- [x] Response includes: `access-control-allow-credentials: true`

### API Health

```bash
curl -s https://api.dev.autoauthor.app/ | head -20
```

- [x] Response includes: `"message":"Welcome to the Auto Author API"`
- [x] No error messages

---

## User Journey: Book Creation to Export

This section walks through the complete authoring workflow from creating a book to exporting it.

### Step 1: Homepage & Authentication

- [x] Open browser (Chrome/Firefox/Safari)
- [x] Navigate to: `https://dev.autoauthor.app`
- [x] Page loads without errors
- [x] Open DevTools (F12) → **Console** tab
- [x] **No red error messages** in console
- [x] **No CORS errors**
- [x] **No CSP errors**
- [x] Clerk sign-in button visible

**Sign In:**

- [x] Click "Sign In" button
- [x] Clerk authentication modal opens
- [x] No CSP errors when modal opens
- [x] Enter credentials and sign in
- [x] Successfully authenticated
- [x] Redirected to `/dashboard` after sign-in

---

### Step 2: Dashboard & API Connection

- [x] Dashboard page loads
- [x] Open DevTools → **Network** tab
- [x] Clear network log (trash can icon)
- [x] Refresh page or click "Books" in navigation
- [x] Look for request to: `api.dev.autoauthor.app/api/v1/books`
- [x] Request shows **200 OK** or **empty array** response
- [x] **No 500 errors**
- [x] **No CORS errors**
- [x] Response headers include `access-control-allow-origin`

---

### Step 3: Create New Book

- [x] Click "New Book" button or navigate to `/dashboard/new-book`
- [x] Form displays correctly
- [x] Form background is **NOT transparent** (should be visible and readable)

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

- [x] Fill in Book Title
- [x] Fill in Description
- [x] Select Genre from dropdown
- [x] Fill in Target Audience
- [x] Click "Create Book" or "Submit"
- [x] Monitor Network tab for POST to `/api/v1/books/`
- [x] Request includes `Authorization: Bearer ...` header
- [x] Response is **201 Created** or **200 OK** (NOT 500 ✅ FIXED)
- [x] Redirected to book detail page (`/dashboard/books/[bookId]`)
- [x] New book appears in books list

**Book ID from URL**: _____________

---

### Step 4: Add Book Summary

**Required before TOC generation**

- [ ] From book detail page, navigate to `/dashboard/books/[bookId]/summary`
- [ ] Summary form page loads
- [ ] Character counter shows "0 characters"
- [ ] Minimum requirement shown: "Minimum: 30 characters"

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

- [ ] Paste test data into summary field
- [ ] Character counter updates correctly (should show ~558 characters)
- [ ] Voice input button visible (🎤 optional test)
- [ ] No validation errors appear
- [ ] Click "Continue to TOC Generation" button
- [ ] Redirected to `/dashboard/books/[bookId]/generate-toc`

---

### Step 5: Generate Table of Contents (TOC Wizard)

**Step 5a: Readiness Check**

- [ ] TOC generation page loads
- [ ] System automatically checks summary readiness
- [ ] Loading indicator appears during AI analysis
- [ ] If summary too short: "Not Ready" message with guidance
- [ ] If summary adequate: Proceeds to questions automatically

**Step 5b: Clarifying Questions**

- [ ] 5-10 clarifying questions appear
- [ ] Questions are relevant to book topic
- [ ] Each question has a text input field
- [ ] Character limit shown for each response (typically 50-500 chars)

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

- [ ] Answer all clarifying questions (paste test data)
- [ ] Click "Generate TOC" or "Continue" button
- [ ] Loading indicator appears
- [ ] AI processes responses (15-60 seconds)
- [ ] Wait for generation to complete

**Step 5c: TOC Review & Confirmation**

- [ ] Generated TOC appears
- [ ] TOC contains 5-15 chapters
- [ ] Each chapter has a title
- [ ] Chapters are logically organized
- [ ] Option to edit chapter titles visible
- [ ] Option to add/remove chapters visible
- [ ] "Save TOC" or "Confirm" button present

**Execute:**

- [ ] Review generated chapters
- [ ] (Optional) Edit a chapter title to test edit functionality
- [ ] Click "Save TOC" or "Confirm"
- [ ] Success message or navigation occurs
- [ ] Redirected to book detail page

---

### Step 6: View Book with Generated TOC

- [ ] Navigate to `/dashboard/books/[bookId]`
- [ ] Book title displayed correctly
- [ ] Table of Contents (TOC) displays
- [ ] Multiple chapters listed (5-15)
- [ ] Each chapter shows:
  - [ ] Chapter number
  - [ ] Chapter title
  - [ ] Status indicator (Draft, In Progress, Completed)
  - [ ] Word count (0 for new chapters)
- [ ] Click on first chapter to open editor

---

### Step 7: Chapter Editor & Content Creation

**Step 7a: Open Chapter Editor**

- [ ] Chapter page loads (`/dashboard/books/[bookId]/chapters/[chapterId]`)
- [ ] Chapter title displayed in breadcrumb
- [ ] Chapter tabs visible on left sidebar (vertical layout)
- [ ] Rich text editor loaded
- [ ] Editor toolbar visible (Bold, Italic, Heading, Lists, etc.)
- [ ] Auto-save indicator present
- [ ] Word count shows "0 words"

**Step 7b: Test Rich Text Editor**

- [ ] Click in editor area
- [ ] Type test text: "This is a test paragraph about urban gardening."
- [ ] Text appears in editor
- [ ] Select text and click **Bold** button
- [ ] Text becomes bold
- [ ] Click **Heading** dropdown and select "Heading 2"
- [ ] Text converts to H2 heading
- [ ] Auto-save indicator shows "Saving..." then "Saved"
- [ ] No console errors

**Step 7c: AI Draft Generation (Q&A to Narrative)**

- [ ] Look for "Generate Draft" or "AI Assistant" button/panel
- [ ] Click to open Q&A wizard
- [ ] Questions appear specific to this chapter
- [ ] Answer 3-5 questions about chapter content

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

- [ ] Paste answers into Q&A form
- [ ] Click "Generate Draft" button
- [ ] Loading indicator appears
- [ ] AI generates draft content (15-60 seconds - Performance Budget: <3000ms)
- [ ] Generated content appears in editor
- [ ] Content is narrative prose (not Q&A format)
- [ ] Content length: 200-800 words
- [ ] Click "Insert Draft" or content auto-inserts
- [ ] Word count updates to show new content
- [ ] Auto-save triggers automatically

**Step 7d: Chapter Tabs & Navigation**

- [ ] Open a second chapter tab by clicking another chapter
- [ ] Chapter tabs appear in sidebar
- [ ] Can switch between chapters using tabs
- [ ] Each tab shows:
  - [ ] Chapter title (truncated if too long)
  - [ ] Status indicator (colored dot)
  - [ ] Unsaved changes indicator (orange dot if edited)
  - [ ] Close button (X with 44x44px touch target)
- [ ] Close one tab using X button
- [ ] Tab closes correctly
- [ ] Active content updates to remaining tab

**Keyboard Navigation (WCAG 2.1 Compliance)**:

- [ ] Press **Tab** to focus on chapter tabs
- [ ] Press **Enter** or **Space** to open focused chapter
- [ ] Press **Arrow Keys** to navigate between tabs
- [ ] Press **Escape** to close modals
- [ ] Focus indicators are visible
- [ ] All interactive elements keyboard accessible

---

### Step 8: Export Book

- [ ] Navigate to `/dashboard/books/[bookId]/export`
- [ ] Export options page loads
- [ ] Format selection available:
  - [ ] PDF
  - [ ] DOCX (Microsoft Word)
- [ ] Customization options visible:
  - [ ] Include cover page
  - [ ] Include table of contents
  - [ ] Page numbering
  - [ ] Headers/footers

**Test PDF Export:**

- [ ] Select **PDF** format
- [ ] Enable "Include cover page"
- [ ] Enable "Include table of contents"
- [ ] Click "Export" button
- [ ] Export progress modal appears
- [ ] Progress bar shows processing
- [ ] Operation completes within **5 seconds** (Performance Budget ✅)
- [ ] File downloads automatically
- [ ] File opens correctly in PDF viewer
- [ ] Content is formatted properly
- [ ] Chapters are present
- [ ] Table of contents is functional (hyperlinks work)

**Test DOCX Export:**

- [ ] Select **DOCX** format
- [ ] Configure options (cover page, TOC)
- [ ] Click "Export"
- [ ] Export progress appears
- [ ] Operation completes within **5 seconds** (Performance Budget ✅)
- [ ] File downloads
- [ ] File opens in Microsoft Word/LibreOffice
- [ ] Content is properly formatted
- [ ] Chapters have correct headings
- [ ] Table of contents is functional

---

## Advanced Features Testing

### Voice Input Integration

- [ ] Navigate to book summary page
- [ ] Click "🎤 Voice Input" button
- [ ] Browser asks for microphone permission
- [ ] Grant permission
- [ ] Button shows "Listening..." with red background
- [ ] Speak test phrase: "This is a test of voice input functionality for urban gardening."
- [ ] Text appears in summary field as you speak
- [ ] Click "Stop" button to end recording
- [ ] Voice input stops
- [ ] Text saved correctly in field
- [ ] Character counter updates

### Auto-Save System

**Normal Auto-Save:**

- [ ] Open chapter editor
- [ ] Type text in editor: "Testing auto-save functionality."
- [ ] Watch auto-save indicator
- [ ] Shows "Saving..." after **3 seconds** (debounce)
- [ ] Shows "Saved" when complete (within **1 second** - Performance Budget ✅)
- [ ] Refresh page (F5)
- [ ] Content persists after refresh
- [ ] No data loss

**Network Failure Resilience:**

- [ ] Open chapter editor
- [ ] Open DevTools → Network tab
- [ ] Set throttling to "Offline"
- [ ] Type text in editor: "Testing offline auto-save."
- [ ] Auto-save attempts and fails gracefully
- [ ] Data saved to **localStorage** (backup)
- [ ] Error notification appears: "Unable to save. Changes saved locally."
- [ ] Set throttling back to "No throttling"
- [ ] Auto-save retries automatically
- [ ] Succeeds and syncs to server
- [ ] Success notification appears

### Delete Book Functionality

**Type-to-Confirm Pattern (Data Loss Prevention):**

- [ ] Navigate to dashboard
- [ ] Find test book in list
- [ ] Click "Delete" button or three-dot menu → Delete
- [ ] Confirmation modal appears
- [ ] Modal shows warning: "This action cannot be undone"
- [ ] Modal shows: "Type DELETE to confirm"
- [ ] Type "delete" (lowercase) → Button stays **disabled** ✅
- [ ] Type "delETE" (mixed case) → Button stays **disabled** ✅
- [ ] Clear field and type "DELETE" (uppercase) → Button becomes **enabled** ✅
- [ ] Click "Delete Book" button
- [ ] Modal shows processing indicator
- [ ] Book deleted successfully
- [ ] Redirected to dashboard
- [ ] Book no longer appears in list
- [ ] Audit log recorded (check backend logs if needed)

---

## Security & Performance Checks

### CSP Headers - Frontend

```bash
curl -I https://dev.autoauthor.app | grep content-security-policy
```

- [ ] Includes: `connect-src` with `api.dev.autoauthor.app`
- [ ] Includes: `script-src` with `clerk.accounts.dev`
- [ ] No violations in browser console

### CSP Headers - Backend

```bash
curl -I https://api.dev.autoauthor.app/docs | grep content-security-policy
```

- [ ] Includes: `script-src` with `cdn.jsdelivr.net`
- [ ] Includes: `style-src` with `cdn.jsdelivr.net`
- [ ] Includes: `img-src` with `fastapi.tiangolo.com`

### Swagger API Documentation

- [ ] Navigate to: `https://api.dev.autoauthor.app/docs`
- [ ] Swagger UI interface loads completely
- [ ] **No white/blank page**
- [ ] No CSP errors in console
- [ ] Can expand/collapse endpoints
- [ ] FastAPI logo/favicon loads
- [ ] Can test endpoints with "Try it out" button

### Performance - Core Web Vitals

- [ ] Open: `https://dev.autoauthor.app`
- [ ] Open DevTools → **Lighthouse** tab
- [ ] Click "Analyze page load"
- [ ] Performance score: _______ (target: **>80** ✅)
- [ ] LCP (Largest Contentful Paint): _______ (target: **<2.5s** ✅)
- [ ] CLS (Cumulative Layout Shift): _______ (target: **<0.1** ✅)

### Performance - Operation Budgets

- [ ] **TOC Generation**: Completes in < **3000ms** ✅
- [ ] **Export (PDF/DOCX)**: Completes in < **5000ms** ✅
- [ ] **Chapter Auto-Save**: Completes in < **1000ms** ✅
- [ ] **Page Navigation**: < **500ms** ✅

---

## Regression Tests

### Critical User Flows

**Flow 1: Sign Out → Sign In → Dashboard**

- [ ] Click sign out button
- [ ] Redirected to homepage
- [ ] Clerk session cleared
- [ ] Click "Sign In"
- [ ] Clerk modal appears
- [ ] Sign in successful
- [ ] Redirected to dashboard
- [ ] Books list loads
- [ ] User data persists

**Flow 2: Edit Book Metadata**

- [ ] Open book detail page
- [ ] Click "Edit" button
- [ ] Edit mode activates
- [ ] Change book title to: "Updated Title - Deployment Test"
- [ ] Change description
- [ ] Click "Save"
- [ ] Title updates successfully
- [ ] Description updates
- [ ] No errors in console
- [ ] Changes persist on page refresh

**Flow 3: Multiple Chapter Tabs**

- [ ] Open book with 5+ chapters
- [ ] Open 5 different chapter tabs
- [ ] Each tab loads in sidebar
- [ ] Switch between tabs multiple times
- [ ] Each tab loads correct content
- [ ] Close 2 tabs using X button
- [ ] Remaining 3 tabs still functional
- [ ] Tab order persists
- [ ] Active tab state saved

**Flow 4: Keyboard Shortcuts**

- [ ] In chapter editor, select text
- [ ] Press `Ctrl+B` (or `Cmd+B` on Mac)
- [ ] Selected text becomes **bold**
- [ ] Press `Ctrl+I` (or `Cmd+I`)
- [ ] Selected text becomes *italic*
- [ ] Press `Ctrl+S` (or `Cmd+S`)
- [ ] Document saves (auto-save may prevent default)
- [ ] Press `Escape`
- [ ] Closes modal (if open)

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

- [ ] No CORS errors in any console
- [ ] No CSP violations in any console
- [ ] No 500 errors in Network tab
- [ ] No 401/403 errors on authenticated endpoints
- [ ] All PM2 processes remain **online**
- [ ] Backend logs show no errors during testing

### Functional Completeness

- [ ] User can sign in
- [ ] User can create a book with metadata
- [ ] User can add a book summary
- [ ] User can generate TOC with AI wizard
- [ ] User can view books with chapters
- [ ] User can edit chapters with rich text editor
- [ ] User can generate AI drafts from Q&A
- [ ] User can use keyboard shortcuts
- [ ] User can export books (PDF/DOCX)
- [ ] User can delete books safely
- [ ] API documentation accessible (Swagger)
- [ ] No broken features from previous version

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
