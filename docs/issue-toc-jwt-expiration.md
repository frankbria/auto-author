### Bug Summary
Table of Contents (TOC) generation fails when the JWT token expires during the multi-step TOC generation workflow. Specifically, after analyze-summary completes, the subsequent toc-readiness call returns 401 with "Invalid authentication credentials: Signature has expired.", and the UI shows "Something Went Wrong".

### Steps to Reproduce
1. Navigate to a book's TOC generation page.
2. Start the TOC generation wizard.
3. Wait for the analyze-summary operation to complete (takes ~11 seconds).
4. Observe the failure on toc-readiness check with a 401 error.

### Expected Behavior
The TOC generation workflow should complete successfully even if operations take longer than the JWT token timeout period (e.g., via token refresh/renewal).

### Actual Behavior
- analyze-summary succeeds (≈11.6 seconds).
- toc-readiness fails with 401 after 119ms.
- Error message: "Invalid authentication credentials: Signature has expired."
- User sees "Something Went Wrong" message.

### Console Output
```
clerk.browser.js:19 Clerk: Clerk has been loaded with development keys. Development instances have strict usage limits and should not be used when deploying your application to production. Learn more: https://clerk.com/docs/deployments/overview
api.dev.autoauthor.a…4837a8601/summary:1 
 Failed to load resource: the server responded with a status of 400 ()
api.dev.autoauthor.a…4837a8601/summary:1 
 Failed to load resource: the server responded with a status of 400 ()
page-d3ecb3a80fd665ba.js:1 Analyzing summary with AI...
341-8ea9af451c5d571a.js:1 ⚠️ [Performance] analyze-summary exceeded budget: 11621ms (budget: 2500ms, overrun: +9121ms)
page-d3ecb3a80fd665ba.js:1 Summary analysis completed
api.dev.autoauthor.a…601/toc-readiness:1 
 Failed to load resource: the server responded with a status of 401 ()
error_handler.js:1 ❌ [Performance] toc-readiness failed after 119ms: Error: Failed to check TOC readiness: 401 {"detail":"Invalid authentication credentials: Signature has expired."}
    at s.checkTocReadiness (391-5da1344dceb766f7.js:1:1849)
    at async x.bookId (page-d3ecb3a80fd665ba.js:1:25240)
    at async 341-8ea9af451c5d571a.js:1:4405
    at async page-d3ecb3a80fd665ba.js:1:25207
error_handler.js:1 Error checking TOC readiness: Error: Failed to check TOC readiness: 401 {"detail":"Invalid authentication credentials: Signature has expired."}
    at s.checkTocReadiness (391-5da1344dceb766f7.js:1:1849)
    at async x.bookId (page-d3ecb3a80fd665ba.js:1:25240)
    at async 341-8ea9af451c5d571a.js:1:4405
    at async page-d3ecb3a80fd665ba.js:1:25207
2
content.js:10 Uncaught Error: Extension context invalidated.
    at o (content.js:10:5910)
    at content.js:10:5622
content.js:10 Uncaught Error: Extension context invalidated.
    at o (content.js:10:5711)
    at content.js:10:5622
```

### Technical Details
- **Affected file (frontend)**: `frontend/src/components/toc/TocGenerationWizard.tsx` (lines 55-101)
- **Affected endpoints (backend)**:
  - `POST /books/{book_id}/analyze-summary` (backend/app/api/endpoints/books.py line 689)
  - `GET /books/{book_id}/toc-readiness` (backend/app/api/endpoints/books.py line 919)
- **Token management**: Clerk JWT authentication
- **Issue occurs when**: analyze-summary takes longer than the token TTL, causing the next step to fail with 401.

### Proposed Solutions
1. **Implement token refresh mechanism** in the frontend API client before each step that may exceed token TTL.
2. **Increase JWT token TTL** for long-running operations (or issue short-lived, refreshable tokens).
3. **Add retry logic with token refresh** on 401 errors for TOC-related endpoints.
4. **Consider combining** analyze-summary and toc-readiness into a single atomic backend operation to avoid mid-flow token expiration.
5. **Add progress indicators** and warnings in the UI when operations are expected to take longer than the performance budget.

### Environment
- **Frontend**: Next.js with Clerk authentication
- **Backend**: FastAPI with JWT verification
- **Authentication**: Clerk with JWKS endpoint
- **Current working directory**: /home/frankbria/projects/auto-author

### Related Files
- `frontend/src/lib/api/bookClient.ts` (lines 435-453, 508-531)
- `frontend/src/components/toc/TocGenerationWizard.tsx` (lines 55-101)
- `backend/app/api/endpoints/books.py` (lines 689-746, 919-1016)

### Priority
**High** — Blocks users from completing the TOC generation workflow, a core feature of the application.
