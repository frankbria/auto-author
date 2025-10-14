# AI Assistant Coding Guidelines

This project is a monorepo called `auto-author`. It contains:

## Project Structure
- `frontend/`: A Next.js (TypeScript) app used for the UI
- `backend/`: A FastAPI (Python) app used for API and AI logic
- `docs/`: Project documentation and guides
- `claudedocs/`: Claude-specific analysis reports and detailed plans
- `archive/`: Historical planning documents (read-only)
- MongoDB is the primary database used in the backend
- No shared libraries exist between frontend and backend
- The root of the backend application is `backend`, so no need to append `backend` to imports
- The root of the frontend application is `frontend`, so no need to append `frontend` to imports
- Do not hardcode URLs. If they are needed, they should be coming in from an .env or .env.local file.
- If changes are made to the .env or .env.local file, make similar changes to the .env.example file so that they stay in sync. Do not add secret keys or passwords to the .env.example file. Use mock values instead.

## File Header Convention

Each file should begin with a full path comment:
- TypeScript: `// frontend/app/components/Sidebar.tsx`
- Python: `# backend/app/api/routers/email.py`

This helps the AI contextually understand the file's location and purpose.

---

## Naming Conventions

- Backend routes go in `backend/app/api/routers/`
- Data models (MongoDB/Beanie) go in `backend/app/models/`
- Frontend UI components go in `frontend/app/components/`
- Pages are under `frontend/app/` using Next.js file routing

Use lowercase_with_underscores for Python files.
Use PascalCase for React components.

## MongoDB Guidelines

- We use Beanie ODM for MongoDB in the backend
- All models extend `Document`
- Use Pydantic `Field()` to define default values and metadata
- Models live in `backend/app/models/`

```python
# backend/app/models/email_message.py
from beanie import Document
from pydantic import Field

class EmailMessage(Document):
    subject: str = Field(...)
    sender: str
    body: str

```

## API Interaction

- Frontend uses `fetch` or `axios` to call the FastAPI backend
- Use environment variables in `.env.local` to store the API base URL
- API endpoints live under `/api/v1/` on the backend

Example API call:
```ts
const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/api/v1/email`, {
  method: "POST",
  body: JSON.stringify(payload),
});
```
### 🧑‍🎨 UI Design Guidelines

- Use **modern, clean, accessible UI components**.
- Prefer **[shadcn/ui](https://ui.shadcn.com/)** for component design and styling.
- Use **[sonner](https://sonner.emilkowal.ski/)** for toast messages (shadcn `toast` is deprecated).
- Avoid legacy or custom-styled UI libraries unless specifically required.
- Ensure responsive layouts, keyboard accessibility, and semantic HTML.
- When building forms, modals, or tables, **leverage shadcn primitives** before custom coding.
- Apply Tailwind CSS for custom styling
- Aim for consistency between UI components

### Key UI Components (Production Ready)

**Loading States** (`frontend/src/components/loading/`):
- `LoadingStateManager` - Full-featured loading with progress, time estimates, and cancellation
- `ProgressIndicator` - Visual progress with percentage and count tracking
- Features: WCAG 2.1 compliant, time budgets, graceful transitions, inline/full-screen variants

**Book Management** (`frontend/src/components/books/`):
- `DeleteBookModal` - Type-to-confirm deletion with comprehensive data loss warnings
- Features: Prevention mechanisms, accessibility, loading states, statistics display

**Performance Monitoring** (`frontend/src/lib/performance/`):
- Comprehensive Core Web Vitals tracking with custom operation budgets
- 25+ operation budgets defined (TOC: 3000ms, Export: 5000ms, Auto-save: 1000ms)
- React hook: `usePerformanceTracking` for async operation monitoring
- Automatic budget validation with warnings


## Test-Driven Development (TDD) Notes

- Write the test as if you're going to refactor the code tomorrow. Minmize brittleness.
- Write the test around user behavior, not the code. For example:
    Bad test: Write a test that makes the `POST /api/email` route return 200.
    Good test: Write a test for creating an email task. It should simulate a user submitting valid form data, and assert that:
        1. The response returns 200,
        2. A new task is created in the DB,
        3. The task includes the email subject in its summary.
- Do not hardcode expected values. Assert based on real logic or use flexible matchers. If the value depends on logic, describe that logic first.
- When using mocks, layer them so the test focuses on just one layer at a time. For example:
    Bad test: Live API, function logic, and application settings
    Good test: Mock API and application settings, and only test function logic live.

## Frontend Testing Strategy

- Use `Vitest` for unit and integration tests
- Use `@testing-library/react` for UI and interaction
- **Coverage Requirement**: Minimum 85% code coverage for all new code (target: 80% overall project coverage)
- Each new component should be accompanied by at least one test
- Use test-first development when feasible: start with a minimal failing test, then create the component
- As with all testing, solve the problem, not just pass the test. Do not hardcode responses.
- E2E tests (Playwright) are used for multi-page or form validation flows
- **Test Helper Libraries**: Use condition-based waiting helpers from `__tests__/helpers/conditionWaiting.ts` instead of arbitrary timeouts
- **Test Data Setup**: Use API-based test data factories from `__tests__/helpers/testDataSetup.ts` for faster, more reliable E2E tests
- Prefer `screen.findByText()` with flexible matchers over `getbyTestId()` unless strictly necessary. think like a user would - what are they trying to see?
- Use `userEvent` to simulate real clicks, typing and navigation - don't just `render()` and call it done.
- **Comprehensive E2E Coverage**: Complete authoring journey, editing/auto-save flow, and error recovery flow tests implemented

### Testing conventions:
- `.test.tsx` files go in `__tests__/` folders alongside components
- Use `jest-dom` for assertions (e.g., `.toBeInTheDocument()`)
- Prefer functional behavior testing over snapshot tests

## Backend Testing Strategy (Python)

- We use `pytest` as the main test framework for the FastAPI backend. All tests should be **simple, focused**, and follow a **test-guided development** approach where possible.
- **Coverage Requirement**: Minimum 85% code coverage for all new code
- Just like in the frontend testing strategy, solve the problem, not just pass the test. Do not hardcode responses.
- Mock database tests by creating a *-test database and seeding it with test data
- **Test Quality Standards**: All tests must have 100% pass rate - no failing tests allowed
- Use condition-based waiting instead of arbitrary timeouts for reliable async testing


### General Guidelines

- All tests live in `backend/tests/`
- Create subdirectories for each module or feature `backend/tests/test_*`
- All test files should follow the pattern `test_*.py`
- Use `pytest` fixtures for shared setup (`conftest.py`)
- Use `TestClient` from `fastapi.testclient` to test routes
- Use `pytest.mark.asyncio` for async functions (when applicable)

### Test Organization

- `test_main.py`: health check or root route tests
- `test_routes/`: individual API endpoint tests
- `test_models/`: Pydantic/Beanie model behavior tests
- `test_services/`: logic layers (e.g., email parsing, classification)
- `test_utils/`: helpers or reusable utility functions

### Example: API Route Test

```python
# tests/test_main.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from FastAPI with Poetry!"}
```

### Example: Using Fixtures
```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)
```

```python
# tests/test_email.py
def test_send_email(client):
    response = client.post("/api/v1/send", json={"subject": "Hi", "body": "Test"})
    assert response.status_code == 200
```

### Coverage and CI (Planned)
We will eventually add pytest-cov to track test coverage and enforce thresholds during CI/CD pipelines.

### Running Tests
Run all tests:
```bash
pytest
```
With coverage:
```bash
pytest --cov=app
```
Or with file path filtering:
```bash
pytest tests/test_routes/test_email.py
```

### Tone and Style

- Prefer **functional test names** (`test_rejects_invalid_email`) over implementation-based ones
- Focus on **behavioral testing** — what the app *does*, not how it's implemented
- Avoid mocking until necessary — test real FastAPI flows first

### AI Instructions for Test Writing

#### INSTRUCTIONS:
1. Start by writing a failing test that clearly validates the intended behavior described above.
   - Place it in the appropriate test module (e.g., `test_services/`, `test_routes/`, `test_models/`, etc.)
   - Include a descriptive test name and inline comments explaining what it is validating and why.
   - Please follow these test-writing rules:
        - Focus on user behavior, not implementation
        - Avoid hardcoding return values — derive them from inputs
        - Simulate real usage (e.g., user typing, clicking)
        - Use flexible assertions (e.g., `toMatchText`, `includes`)
        - Favor `screen.getByText` over `data-testid` unless it's reusable
   
2. Then write the minimal amount of code needed to make the test pass.
   - Isolate the logic in a new or existing service/module.
   - Prefer small, well-named functions that express intent.
   
3. If the test passes for the right reason, expand coverage with at least 2 more test cases:
   - One common or edge case
   - One negative or invalid case (if applicable)

4. Refactor the implementation only after the test passes.
   - Improve clarity, eliminate duplication, but keep behavior unchanged.

5. Return a summary that includes:
   - What logic you implemented and where
   - Which tests were added and what they verify
   - Whether all tests pass, and what could break in future changes

### CONSTRAINTS:
- DO NOT hardcode expected values just to make the test pass.
- DO NOT change the test to fit your logic — fix the logic to match the test’s intent.
- DO isolate logic into a proper domain layer (not in route handlers).
- DO name functions and tests descriptively and behaviorally.
- DO look for existing code and leverage it first before creating new code.

## To Do List
### INSTRUCTIONS:
- A running list of to dos are stored in todo.md
- To dos will start with a markdown checkbox '[ ]'
- To dos are created for each user story
- To dos should include the appropriate models, API routes, frontend interaction, and unit testing
- When executing a to do, mark them done when finished.
- If there are a lot of to dos, break them into categories

### EXAMPLE:
```md
## User Story 7

### 🛠 Direct Action on Task Cards
- [X] Add `onAction` prop to `TaskCard` (frontend/src/components/TaskCard.tsx)
  - Accepts a callback for when an action is triggered
  - Pass action name/type to callback
- [X] Implement action selection click handling in `TaskCard`
  - On click, call `onAction` with the action string
  - Display confirmation dialogue
  - Show a visual feedback (e.g., loading spinner, checkmark, or toast)
  - Disable the action dropdown while the action is pending to prevent double clicks
- [ ] Wire up `onAction` in `TaskList` (frontend/src/app/page.tsx)
  - Pass a handler that calls the backend API to update the task (e.g., mark as done, archive, etc.)
  - Optimistically update UI on success
  - Catch and handle backend errors gracefully (show error toast or retry option)
- [ ] Add backend PATCH endpoint for task actions (if not already present)
  - Route: `PATCH /api/v1/tasks/{id}`
  - Accepts action/status update payload (e.g., { status: "done" })
  - Updates the task in the database
  - Tasks marked done do not appear on the screen anymore but are available for the History page (Sprint 2)
  - Return proper error responses (400/404/500) with clear error messages
  - Updates the action_taken field in the database with the action chosen from the TaskCard
- [ ] Add unit tests for action handling in TaskCard (frontend/src/__tests__/TaskCard.test.tsx)
  - Simulate clicking each action
  - Assert the callback is called with the correct action
  - Assert UI feedback (spinner, checkmark) is triggered
  - Assert action disables during pending state
- [ ] Add integration test for action flow (frontend/src/__tests__/page.test.tsx)
  - Simulate user selecting action from the dropdown list
  - Simulate user confirming on the confirmation dialog
  - Assert the backend PATCH is called
  - Assert optomistic UI update occurs
  - Simulate backend failure and assert error feedback is shown
- [ ] Manual QA: Verify direct action works on both desktop and mobile
  - Verify clicking an action button updates the UI without page reload
  - Verify buttons are responsive to *keyboard navigation* (tab to button + enter/space triggers action)
  - Verify visual feedback is immediate and clear (loading spinner, success confifmation, or error)
  - Verify buttons are disabled after click until action is complete
  - Verify responsive behavior and functionality on both desktop and mobile
```