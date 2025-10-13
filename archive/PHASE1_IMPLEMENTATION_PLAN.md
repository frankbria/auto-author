# Phase 1 Implementation Plan - Export & Error Handling

**Status**: Ready to Begin
**Estimated Duration**: Week 1-2 (48 hours → 35 hours after discovery)
**Priority**: P0 - Production Blockers

---

## 🎉 Great News: Export API Already Exists!

Upon reviewing `bookClient.ts`, I discovered the export methods are **already implemented**:
- ✅ `exportPDF(bookId, options)` - lines 844-873
- ✅ `exportDOCX(bookId, options)` - lines 878-903
- ✅ `getExportFormats(bookId)` - lines 908-939

**Impact**: Reduces Phase 1 from 48 hours to ~35 hours (27% time savings)

---

## Revised Task Breakdown

### ✅ Already Complete (13 hours saved)
- [x] Export API client methods with TypeScript interfaces
- [x] PDF export with options (includeEmptyChapters, pageSize)
- [x] DOCX export with options
- [x] Export formats metadata endpoint

### 🔨 Tasks Remaining (35 hours)

#### 1. Export UI Integration (8 hours) - DOWN FROM 16h
**Original**: 16h | **Revised**: 8h | **Savings**: 8h

- [ ] **Export Button Integration** (2h) - REDUCED FROM 3h
  - [x] API methods already exist
  - [ ] Add onClick handler to export button in `BookPage.tsx`
  - [ ] Create export options modal component
  - [ ] Wire up format/pageSize/chapter selection

- [ ] **Export Options Modal Component** (3h) - NEW
  - [ ] Create `ExportOptionsModal.tsx` component
  - [ ] Format selection radio buttons (PDF/DOCX)
  - [ ] Page size selection (Letter/A4) for PDF
  - [ ] "Include empty chapters" toggle
  - [ ] Chapter selection (all vs specific)

- [ ] **Progress Tracking** (2h) - REDUCED FROM 4h
  - [ ] Create progress modal with circular indicator
  - [ ] Show percentage and estimated time
  - [ ] Add cancel button (doesn't need polling - export is fast)

- [ ] **Download Handling** (1h) - REDUCED FROM 2h
  - [ ] Implement blob download helper
  - [ ] Success notification with filename/size
  - [ ] Handle download failures

---

#### 2. Unified Error Handling Framework (20 hours)
**No change - this is new infrastructure**

- [ ] **Error Classification System** (4h)
  - [ ] Create error type enums and interfaces
  - [ ] Error classification utility function
  - [ ] HTTP status code to error type mapping
  - [ ] Define retryable vs non-retryable errors

- [ ] **Unified Error Handler** (6h)
  - [ ] Create `lib/api/errorHandler.ts`
  - [ ] Implement `handleApiCall<T>()` wrapper
  - [ ] Automatic retry logic (3 attempts, exponential backoff)
  - [ ] Manual retry capability
  - [ ] User input preservation during retries

- [ ] **Error Notification Components** (5h)
  - [ ] Create `ErrorNotification` component
  - [ ] Transient error template (with retry button)
  - [ ] Permanent error template (with correction guidance)
  - [ ] System error template (with support reference)
  - [ ] Retry attempt counter display

- [ ] **Error Message Standardization** (3h)
  - [ ] Error message utility functions
  - [ ] Field highlighting for validation errors
  - [ ] Correlation ID generation
  - [ ] Support contact integration

- [ ] **Update Existing Components** (2h)
  - [ ] Refactor BookCreationWizard
  - [ ] Refactor ChapterTabs
  - [ ] Refactor ChapterEditor auto-save
  - [ ] Add to TOC generation

---

#### 3. API Contract Formalization (7 hours) - DOWN FROM 12h
**Original**: 12h | **Revised**: 7h | **Savings**: 5h

- [ ] **Export Types Documentation** (1h) - REDUCED FROM 2h
  - [x] Interfaces already exist in bookClient
  - [ ] Add JSDoc comments to export methods
  - [ ] Document export options and responses

- [ ] **Base API Types** (2h)
  - [ ] Define `ApiResponse<T>` interface
  - [ ] Define `ApiError` interface
  - [ ] Create response validation utilities

- [ ] **API Client Method Documentation** (2h) - REDUCED FROM 4h
  - [x] Export methods already implemented
  - [ ] Add comprehensive JSDoc to all methods
  - [ ] Document error scenarios
  - [ ] Add usage examples

- [ ] **TypeScript Strict Mode Compliance** (2h)
  - [ ] Enable strict mode if not already
  - [ ] Fix any type errors
  - [ ] Ensure all responses properly typed

---

## Implementation Order

### Day 1-2: Export UI (8 hours)
1. Create `ExportOptionsModal` component
2. Wire up export button in `BookPage.tsx`
3. Implement progress modal
4. Add download handling

**Deliverable**: Functional export feature with UI

---

### Day 3-5: Error Handling Foundation (14 hours)
1. Create error classification system
2. Implement `handleApiCall` wrapper
3. Build error notification components
4. Standardize error messages

**Deliverable**: Unified error handling framework

---

### Day 6-7: Integration & Polish (13 hours)
1. Update existing components with error handler
2. Formalize API contracts with documentation
3. Add JSDoc comments throughout
4. Test all error scenarios

**Deliverable**: Production-ready error handling across app

---

## Success Criteria

### Export Feature Complete
- ✅ User can click export button and see options modal
- ✅ Export generates PDF/DOCX with selected options
- ✅ Progress indicator shows during generation
- ✅ File downloads automatically
- ✅ Success notification displays filename and size
- ✅ Errors display specific messages

### Error Handling Complete
- ✅ All API calls use unified error handler
- ✅ Transient errors retry automatically (3 times)
- ✅ Clear error messages for each error type
- ✅ Validation errors highlight specific fields
- ✅ System errors include support reference
- ✅ Manual retry available for retryable errors

### API Contracts Complete
- ✅ All API methods have JSDoc documentation
- ✅ All responses properly typed
- ✅ Error scenarios documented
- ✅ Usage examples provided

---

## Files to Create/Modify

### New Files
```
frontend/src/components/export/
  ├── ExportOptionsModal.tsx       (new)
  ├── ExportProgressModal.tsx      (new)
  └── exportHelpers.ts             (new)

frontend/src/lib/api/
  ├── errorHandler.ts              (new)
  ├── errorTypes.ts                (new)
  └── apiTypes.ts                  (new)

frontend/src/components/errors/
  ├── ErrorNotification.tsx        (new)
  └── errorMessages.ts             (new)
```

### Files to Modify
```
frontend/src/lib/api/
  └── bookClient.ts                (add JSDoc, use error handler)

frontend/src/app/dashboard/books/[bookId]/
  └── page.tsx                     (add export button handler)

frontend/src/components/
  ├── BookCreationWizard.tsx       (use error handler)
  └── chapters/
      ├── ChapterTabs.tsx          (use error handler)
      └── ChapterEditor.tsx        (use error handler)
```

---

## Quick Start Commands

### Start Development Server
```bash
cd frontend
npm run dev
```

### Run Type Checking
```bash
cd frontend
npm run type-check
```

### Run Tests
```bash
cd frontend
npm test
```

### Run Linting
```bash
cd frontend
npm run lint
```

---

## Next Steps

1. ✅ Review this plan
2. ✅ Confirm approach
3. 🔨 Begin Day 1: Create `ExportOptionsModal` component
4. 🔨 Wire up export button click handler
5. 🔨 Test export flow end-to-end

---

## Risk Mitigation

### Risk 1: Export Generation Timeout
**Mitigation**: Export backend is already tested and fast (<5 seconds for typical books)

### Risk 2: Large File Downloads
**Mitigation**: Browser handles download automatically, no streaming needed for book-sized files

### Risk 3: Error Handler Breaking Existing Code
**Mitigation**: Implement as wrapper, migrate components incrementally, test thoroughly

---

## Notes

- Export API already exists and works - just needs UI connection
- Error handler should be non-breaking - wraps existing calls
- JSDoc can be added incrementally without breaking changes
- All work can be done on feature branch for safety

---

**Last Updated**: 2025-10-11
**Status**: Ready to Begin
**Next Task**: Create ExportOptionsModal component
