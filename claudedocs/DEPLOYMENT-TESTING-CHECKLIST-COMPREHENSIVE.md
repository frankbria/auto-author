# Auto-Author Comprehensive Deployment Testing Checklist

**Environment**: ClawCloud Production (dev.autoauthor.app)
**Date**: _____________
**Tester**: _____________

---

## Document Purpose

This checklist provides a complete end-to-end testing workflow for Auto-Author deployment validation. It includes:
- **Pre-flight system health checks**
- **Complete user journey testing** (book creation → TOC generation → chapter editing → export)
- **Copy-paste test data** for all forms with field constraints
- **Regression testing** for critical features
- **Performance validation**

---

## Table of Contents

1. [Pre-Flight Checks](#pre-flight-checks)
2. [Complete User Journey Testing](#complete-user-journey-testing)
3. [Advanced Features Testing](#advanced-features-testing)
4. [Security & Performance Checks](#security--performance-checks)
5. [Regression Tests](#regression-tests)
6. [Sign-Off](#sign-off)

---

## Pre-Flight Checks

### Server Health

```bash
ssh root@47.88.89.175
```

- [ ] **PM2 Status**: `pm2 status`
  - [ ] `auto-author-frontend` shows **online**
  - [ ] `auto-author-backend` shows **online**

- [ ] **Backend Logs**: `pm2 logs auto-author-backend --lines 20 --nostream`
  - [ ] No **Traceback** or **Error** messages

- [ ] **Frontend Logs**: `pm2 logs auto-author-frontend --lines 20 --nostream`
  - [ ] Shows "✓ Ready" message

### CORS Configuration

```bash
curl -I -X OPTIONS https://api.dev.autoauthor.app/api/v1/books/ \
  -H "Origin: https://dev.autoauthor.app" \
  -H "Access-Control-Request-Method: GET" | grep access-control
```

- [ ] Response includes: `access-control-allow-origin: https://dev.autoauthor.app`
- [ ] Response includes: `access-control-allow-credentials: true`

### API Health

```bash
curl -s https://api.dev.autoauthor.app/ | head -20
```

- [ ] Response includes: `"message":"Welcome to the Auto Author API"`
- [ ] No error messages

---

## Complete User Journey Testing

### Journey 1: Create Book → Add Summary → Generate TOC → Edit Chapters → Export

This section tests the complete authoring workflow from book creation to export.

---

#### Step 1: Homepage & Authentication

- [ ] Open browser (Chrome/Firefox/Safari)
- [ ] Navigate to: `https://dev.autoauthor.app`
- [ ] Page loads without errors
- [ ] Open DevTools (F12) → **Console** tab
- [ ] **No red error messages** in console
- [ ] **No CORS errors**
- [ ] **No CSP errors**
- [ ] Clerk sign-in button visible

**Sign In:**

- [ ] Click "Sign In" button
- [ ] Clerk authentication modal opens
- [ ] No CSP errors when modal opens
- [ ] Enter credentials and sign in
- [ ] Successfully authenticated
- [ ] Redirected to `/dashboard` after sign-in

---

#### Step 2: Create New Book

- [ ] Navigate to `/dashboard/new-book` OR click "New Book" button
- [ ] Form displays correctly
- [ ] Form background is **NOT transparent** (should be visible and readable)

**Test Data (Copy & Paste)**:

```
Book Title: Sustainable Urban Gardening: A Practical Guide

Description: A comprehensive guide for city dwellers to grow fresh produce

Genre: Select "business" from dropdown

Target Audience: Urban residents interested in growing their own food in limited spaces
```

**Field Constraints**:
- Title: Min 1 char, Max 100 chars
- Description: Max 5000 chars
- Genre: Required selection
- Target Audience: Max 100 chars

**Execute:**

- [ ] Fill in Book Title
- [ ] Fill in Description
- [ ] Select Genre from dropdown
- [ ] Fill in Target Audience
- [ ] Click "Create Book" or "Submit"
- [ ] Monitor Network tab for POST to `/api/v1/books/`
- [ ] Request includes `Authorization: Bearer ...` header
- [ ] Response is **201 Created** or **200 OK** (NOT 500)
- [ ] Redirected to book detail page (`/dashboard/books/[bookId]`)
- [ ] New book appears in books list
- [ ] Note the **Book ID** from URL: _____________

**If creation fails, record error**:
- Status Code: _______
- Error Message: _______________________

---

#### Step 3: Add Book Summary

Book must have a summary before TOC can be generated.

- [ ] From book detail page, click "Summary" or navigate to `/dashboard/books/[bookId]/summary`
- [ ] Summary form page loads
- [ ] Character counter shows "0 characters"
- [ ] Minimum requirement shown: "Minimum: 30 characters"

**Test Data (Copy & Paste)**:

```
This practical guide teaches urban dwellers how to create productive gardens in small spaces. Topics include container gardening basics, vertical growing techniques for balconies and patios, composting in urban environments, seasonal planning for year-round harvests, and selecting the best vegetables and herbs for limited space. Readers will learn water-efficient irrigation methods, organic pest control strategies, and how to maximize yields in apartments and small yards. The book includes detailed growing calendars, troubleshooting guides, and case studies from successful urban gardeners in major cities.
```

**Field Constraints**:
- Minimum: 30 characters
- Maximum: 2000 characters
- Must be in English (no Cyrillic, Arabic, CJK characters)
- No offensive language

**Execute:**

- [ ] Paste test data into summary field
- [ ] Character counter updates correctly
- [ ] Voice input button visible (optional test)
- [ ] No validation errors appear
- [ ] Click "Continue to TOC Generation" button
- [ ] Redirected to `/dashboard/books/[bookId]/generate-toc`

---

#### Step 4: Generate Table of Contents (TOC Wizard)

The TOC wizard analyzes the summary and generates clarifying questions.

**Step 4a: Readiness Check**

- [ ] TOC generation page loads
- [ ] System automatically checks summary readiness
- [ ] Loading indicator appears during AI analysis
- [ ] If summary too short: "Not Ready" message appears with specific guidance
- [ ] If summary adequate: Proceeds to questions automatically

**Step 4b: Clarifying Questions**

- [ ] 5-10 clarifying questions appear
- [ ] Questions are relevant to book topic
- [ ] Each question has a text input field
- [ ] Character limit shown for each response

**Test Data for Questions (Use these as responses)**:

```
Question 1 (Main Topics): This book covers container gardening, vertical growing, composting, seasonal planning, and space-efficient techniques for urban environments.

Question 2 (Target Readers): Beginners with no gardening experience living in apartments or homes with limited outdoor space who want to grow fresh food.

Question 3 (Key Takeaways): Readers will learn that productive gardening is possible in small spaces, understand basic techniques, and feel motivated to start their own urban garden.

Question 4 (Scope): The book focuses on vegetables, herbs, and small fruits suitable for containers and small urban spaces, not large-scale farming.

Question 5 (Unique Approach): Emphasizes practical, budget-friendly solutions using recycled materials and minimal space, with real-world examples from city gardeners.
```

**Execute:**

- [ ] Answer all clarifying questions (paste test data)
- [ ] Click "Generate TOC" or "Continue" button
- [ ] Loading indicator appears
- [ ] AI processes responses (may take 15-60 seconds)

**Step 4c: TOC Generation & Review**

- [ ] Generated TOC appears
- [ ] TOC contains 5-15 chapters
- [ ] Each chapter has a title
- [ ] Chapters are logically organized
- [ ] Option to edit chapter titles
- [ ] Option to add/remove chapters
- [ ] "Save TOC" or "Confirm" button visible

**Execute:**

- [ ] Review generated chapters
- [ ] (Optional) Edit a chapter title to test edit functionality
- [ ] Click "Save TOC" or "Confirm"
- [ ] Success message or navigation occurs
- [ ] Redirected to book detail page with chapters visible

---

#### Step 5: View Book with Generated TOC

- [ ] Navigate to `/dashboard/books/[bookId]`
- [ ] Book title displayed correctly
- [ ] Table of Contents (TOC) displays
- [ ] Multiple chapters listed
- [ ] Each chapter shows:
  - [ ] Chapter number
  - [ ] Chapter title
  - [ ] Status indicator (Draft, In Progress, Completed)
  - [ ] Word count (0 for new chapters)
- [ ] Click on first chapter

---

#### Step 6: Chapter Editor & AI Draft Generation

**Step 6a: Open Chapter Editor**

- [ ] Chapter page loads (`/dashboard/books/[bookId]/chapters/[chapterId]`)
- [ ] Chapter title displayed in breadcrumb
- [ ] Chapter tabs visible on left sidebar (if vertical layout)
- [ ] Rich text editor loaded
- [ ] Editor toolbar visible (Bold, Italic, Heading, etc.)
- [ ] Auto-save indicator present
- [ ] Word count shows "0 words"

**Step 6b: Test Rich Text Editor**

- [ ] Click in editor area
- [ ] Type test text: "This is a test paragraph."
- [ ] Text appears in editor
- [ ] Select text and click **Bold** button
- [ ] Text becomes bold
- [ ] Click **Heading** dropdown and select "Heading 2"
- [ ] Text converts to H2
- [ ] Auto-save indicator shows "Saving..." then "Saved"

**Step 6c: AI Draft Generation (Q&A to Narrative)**

Many chapters support AI draft generation through Q&A.

- [ ] Look for "Generate Draft" or "AI Assistant" button/panel
- [ ] Click to open Q&A wizard
- [ ] Questions appear specific to this chapter
- [ ] Answer 3-5 questions about chapter content

**Test Data for Chapter Q&A**:

```
Q: What are the main topics for this chapter?
A: Introduction to container gardening, choosing the right containers, soil selection, and drainage requirements for urban gardens.

Q: What should readers learn by the end?
A: Readers will understand how to select appropriate containers, prepare proper soil mixes, and ensure adequate drainage for healthy plant growth.

Q: What examples or case studies should be included?
A: Show examples of different container types (terracotta, plastic, fabric), a recipe for DIY potting mix, and a troubleshooting guide for common drainage problems.
```

**Execute:**

- [ ] Paste answers into Q&A form
- [ ] Click "Generate Draft" button
- [ ] Loading indicator appears
- [ ] AI generates draft content (15-60 seconds)
- [ ] Generated content appears in editor
- [ ] Content is narrative prose (not Q&A format)
- [ ] Content length: 200-800 words
- [ ] Click "Insert Draft" or content auto-inserts
- [ ] Word count updates to show new content
- [ ] Auto-save triggers

**Step 6d: Chapter Tabs & Navigation**

- [ ] Open a second chapter tab by clicking another chapter
- [ ] Chapter tabs appear in sidebar
- [ ] Can switch between chapters using tabs
- [ ] Each tab shows:
  - [ ] Chapter title
  - [ ] Status indicator
  - [ ] Unsaved changes indicator (orange dot)
  - [ ] Close button (X)
- [ ] Close one tab using X button
- [ ] Tab closes correctly
- [ ] Keyboard navigation works (Tab, Enter, Arrow keys)

**Accessibility Check (WCAG 2.1)**:

- [ ] All interactive elements keyboard accessible
- [ ] Focus indicators visible
- [ ] Screen reader can announce chapter names
- [ ] Touch targets minimum 44x44px (close buttons)

---

#### Step 7: Export Book

- [ ] Navigate to `/dashboard/books/[bookId]/export`
- [ ] Export options page loads
- [ ] Format selection available:
  - [ ] PDF
  - [ ] DOCX (Microsoft Word)
- [ ] Customization options:
  - [ ] Include cover page
  - [ ] Include table of contents
  - [ ] Page numbering
  - [ ] Headers/footers

**Execute:**

- [ ] Select **PDF** format
- [ ] Enable "Include cover page"
- [ ] Enable "Include table of contents"
- [ ] Click "Export" button
- [ ] Export progress modal appears
- [ ] Progress bar shows processing
- [ ] Operation completes within 5 seconds (Performance Budget)
- [ ] File downloads automatically
- [ ] File opens correctly in PDF viewer
- [ ] Content is formatted properly
- [ ] Chapters are present

**Repeat for DOCX:**

- [ ] Select **DOCX** format
- [ ] Configure options
- [ ] Click "Export"
- [ ] File downloads
- [ ] File opens in Microsoft Word/LibreOffice
- [ ] Content is properly formatted

---

## Advanced Features Testing

### Voice Input Integration

- [ ] Navigate to book summary page
- [ ] Click "🎤 Voice Input" button
- [ ] Browser asks for microphone permission
- [ ] Grant permission
- [ ] Speak test phrase: "This is a test of voice input functionality."
- [ ] Text appears in summary field
- [ ] Click "Stop" to end recording
- [ ] Voice input stops
- [ ] Text saved correctly

### Auto-Save System

- [ ] Open chapter editor
- [ ] Type text in editor
- [ ] Watch auto-save indicator
- [ ] Shows "Saving..." after 3 seconds
- [ ] Shows "Saved" when complete
- [ ] Refresh page
- [ ] Content persists after refresh

**Network Failure Test:**

- [ ] Open DevTools → Network tab
- [ ] Set throttling to "Offline"
- [ ] Type text in editor
- [ ] Auto-save attempts and fails
- [ ] Data saved to localStorage (backup)
- [ ] Error notification appears
- [ ] Set throttling back to "No throttling"
- [ ] Auto-save retries and succeeds

### Delete Book Functionality

- [ ] Navigate to dashboard
- [ ] Find test book in list
- [ ] Click "Delete" button or menu
- [ ] Confirmation modal appears
- [ ] Modal shows: "Type DELETE to confirm"
- [ ] Type "delete" (lowercase) → Button stays disabled
- [ ] Type "DELETE" (uppercase) → Button becomes enabled
- [ ] Click "Delete Book" button
- [ ] Book deleted successfully
- [ ] Redirected to dashboard
- [ ] Book no longer appears in list

---

## Security & Performance Checks

### CSP Headers - Frontend

```bash
curl -I https://dev.autoauthor.app | grep content-security-policy
```

- [ ] Includes: `connect-src` with `api.dev.autoauthor.app`
- [ ] Includes: `script-src` with `clerk.accounts.dev`

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

### Performance - Core Web Vitals

- [ ] Open: `https://dev.autoauthor.app`
- [ ] Open DevTools → **Lighthouse** tab
- [ ] Click "Analyze page load"
- [ ] Performance score: _______ (target: >80)
- [ ] LCP (Largest Contentful Paint): _______ (target: <2.5s)
- [ ] CLS (Cumulative Layout Shift): _______ (target: <0.1)

### Performance - Operation Budgets

- [ ] TOC Generation completes in < 3000ms
- [ ] Export (PDF/DOCX) completes in < 5000ms
- [ ] Chapter auto-save completes in < 1000ms
- [ ] Page navigation < 500ms

---

## Regression Tests

### Critical User Flows

**Flow 1: Sign Out → Sign In → Dashboard**

- [ ] Click sign out button
- [ ] Redirected to homepage
- [ ] Click "Sign In"
- [ ] Clerk modal appears
- [ ] Sign in successful
- [ ] Redirected to dashboard
- [ ] Books list loads

**Flow 2: Edit Book Metadata**

- [ ] Open book detail page
- [ ] Click "Edit" button
- [ ] Edit mode activates
- [ ] Change book title
- [ ] Click "Save"
- [ ] Title updates successfully
- [ ] No errors in console

**Flow 3: Multiple Chapter Tabs**

- [ ] Open book with 5+ chapters
- [ ] Open 5 chapter tabs
- [ ] Switch between tabs
- [ ] Each tab loads correct content
- [ ] Close 2 tabs
- [ ] Remaining tabs still functional
- [ ] Tab order persists

**Flow 4: Keyboard Shortcuts**

- [ ] In chapter editor, press `Ctrl+B` (or `Cmd+B` on Mac)
- [ ] Selected text becomes bold
- [ ] Press `Ctrl+S` (or `Cmd+S`)
- [ ] Document saves
- [ ] Press `Escape`
- [ ] Closes modal (if open)

---

## Test Data Reference

### Book Creation

```
Title (1-100 chars): Sustainable Urban Gardening: A Practical Guide
Description (max 5000): A comprehensive guide for city dwellers to grow fresh produce
Genre: business | science | selfHelp | history | health | philosophy | education | other
Target Audience (max 100): Urban residents interested in growing their own food
```

### Book Summary

```
Min 30 chars, Max 2000 chars, English only, No profanity

Example (550 chars):
This practical guide teaches urban dwellers how to create productive gardens in small spaces. Topics include container gardening basics, vertical growing techniques for balconies and patios, composting in urban environments, seasonal planning for year-round harvests, and selecting the best vegetables and herbs for limited space. Readers will learn water-efficient irrigation methods, organic pest control strategies, and how to maximize yields in apartments and small yards. The book includes detailed growing calendars, troubleshooting guides, and case studies from successful urban gardeners.
```

### TOC Questions

```
Response length: 50-500 chars each

Q1 - Main Topics: [Describe 3-5 key topics the book will cover]
Q2 - Target Readers: [Who is this book for? Be specific about their needs]
Q3 - Key Takeaways: [What will readers learn or be able to do after reading?]
Q4 - Scope: [What is included and what is NOT included in the book?]
Q5 - Unique Approach: [What makes this book different from others on the topic?]
```

### Chapter Q&A

```
Response length: 50-300 chars each

Q: Main topics for this chapter?
A: [List 3-5 specific topics this chapter will address]

Q: What should readers learn?
A: [Specific skills or knowledge readers will gain]

Q: Examples or case studies?
A: [Real-world examples to include in the chapter]
```

---

## FIXES APPLIED (2025-10-20)

### Issue 1: 500 Error on Book Creation ✅ FIXED

**Root Cause**: `audit_request()` function in `backend/app/api/dependencies.py` was missing the `metadata` parameter.

**Fix Applied**:
- Added `metadata: Optional[Dict] = None` parameter to function signature
- Updated function to merge metadata into the details dictionary
- Deployed to production server
- Backend service restarted successfully

**Status**: ✅ Ready for re-test

### Issue 2: New Book Page Transparency ✅ FIXED

**Root Cause**: Form background `bg-zinc-800` appeared transparent against `bg-zinc-950` page background.

**Fix Applied**:
- Changed form background from `bg-zinc-800` to `bg-zinc-900` (darker, more opaque)
- Added `border border-zinc-700` for better visual definition
- Added `shadow-xl` for depth and separation
- Deployed to production
- Frontend rebuilt and service restarted successfully

**Status**: ✅ Ready for re-test

### Deployment Status

- Both fixes committed to git: `708a871`
- Backend service: ✅ Running (PM2 process 3)
- Frontend service: ✅ Running (PM2 process 2)
- Ready for continued testing

---

## Final Verification

### No Errors Checklist

- [ ] No CORS errors in any console
- [ ] No CSP violations in any console
- [ ] No 500 errors in Network tab
- [ ] No 401/403 errors on authenticated endpoints
- [ ] All PM2 processes remain **online**
- [ ] Backend logs show no errors during testing

### Functional Completeness

- [ ] User can sign in
- [ ] User can create a book
- [ ] User can add a book summary
- [ ] User can generate TOC with AI wizard
- [ ] User can view books with chapters
- [ ] User can edit chapters with rich text editor
- [ ] User can generate AI drafts from Q&A
- [ ] User can export books (PDF/DOCX)
- [ ] API documentation accessible
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

Check console for "refused to load" errors. Fix: Backend CSP headers need `cdn.jsdelivr.net`.

### If frontend can't connect to API

1. Frontend .env has correct API URL: `NEXT_PUBLIC_API_URL=https://api.dev.autoauthor.app/api/v1`
2. Frontend was rebuilt after .env change: `npm run build`
3. PM2 restarted: `pm2 restart auto-author-frontend`

---

## Rollback Procedure

**If critical issues found**:

1. ☐ Document all issues above
2. ☐ Notify deployment team
3. ☐ Execute rollback:

```bash
ssh root@47.88.89.175
cd /opt/auto-author
# Restore from backup tarball if available
tar -xzf backup-[timestamp].tar.gz -C current/
pm2 restart all
```

4. ☐ Verify rollback successful by re-running tests
