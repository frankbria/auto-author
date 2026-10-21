# ✍️ Auto Author

[![Follow on X](https://img.shields.io/twitter/follow/FrankBria18044?style=social)](https://x.com/FrankBria18044)

**Auto Author** is an AI-powered application designed to help users write long-form non-fiction books. It streamlines the writing process by guiding users from concept to draft using a unique combination of interactive interviews, voice/text input, and generative AI.

---

## 🚀 Features

### Core Authoring Workflow
* 🎯 **AI-generated Table of Contents** from summaries (text or voice)
* 🧠 **Interview-style questions** per chapter to gather detailed content
* ✍️ **Rich text chapter editing** with TipTap editor and full formatting
* 📝 **AI draft generation** from Q&A responses with multiple writing styles
* 🔁 Regeneration of TOC, prompts, and content at any stage

### User Experience
* 🔐 Secure **user authentication** (better-auth) and profile management
* 📚 Full **CRUD functionality** for books, chapters, and metadata
* 🎤 **Voice input** support via Web Speech API (production ready)
* 💾 **Auto-save** with 3-second debounce and localStorage backup on network failure
* 📊 **Save status indicators** with visual feedback (Saving/Saved/Error)
* ⌨️ **Full keyboard accessibility** (WCAG 2.1 Level AA compliant)
* 📱 **Responsive design** supporting devices from 320px (iPhone SE) to desktop
* 🎯 **Touch target compliance** (100% WCAG 2.1 Level AAA - 44x44px minimum)

### Production Features
* 📤 **Export functionality** (PDF/DOCX/EPUB/Markdown with customizable options)
* 🔄 **Unified error handling** with automatic retry logic and user notifications
* ⚠️ **Book deletion protection** with type-to-confirm and data loss warnings
* 📈 **Performance monitoring** with Core Web Vitals tracking
* ⏳ **Loading state indicators** with progress bars and time estimates
* 🛡️ **Data preservation** with validation, TTL-based cleanup, and recovery UI
* 🧪 **Comprehensive test coverage** (CI-enforced ≥85% gate on both frontend and backend; ~92% backend, 100% pass rate)

---

## 🧱 Tech Stack

| Layer          | Technology                        |
| -------------- | --------------------------------- |
| Frontend       | Next.js (TypeScript), TailwindCSS |
| Backend API    | FastAPI                           |
| Database       | MongoDB (Atlas or self-hosted)    |
| Auth           | better-auth (cookie sessions)      |
| AI Integration | OpenAI (or local LLM)             |
| Voice Input    | Web Speech API / Whisper API      |

---

## 🔐 Authentication (better-auth)

Auto Author uses [better-auth](https://www.better-auth.com/) for authentication with cookie-based sessions:

- Email/password registration and login, email verification, password reset
- httpOnly session cookies (no JWT is sent to the backend)
- Sessions stored in MongoDB; the backend validates the session cookie on each request (see `backend/app/core/better_auth_session.py`)

We keep a local user record in MongoDB keyed by the better-auth user id (`auth_id`) so books, chapters, and preferences can be associated with a user. This separates authentication concerns from application data management:

1. Associate user-generated content (books, chapters, etc.) with specific users
2. Store application-specific user preferences and metadata
3. Implement role-based permissions within our application
4. Maintain data relationships without exposing authentication details

### Configuration

- Backend: `BETTER_AUTH_SECRET` (≥32 chars; ≥64 in production), `BETTER_AUTH_URL` — see `backend/.env.example`.
- Frontend: `BETTER_AUTH_SECRET` (must match the backend) and `NEXT_PUBLIC_BETTER_AUTH_URL` — see `frontend/.env.example`.
- `BYPASS_AUTH=true` enables auth bypass for local development and E2E tests only — and only when `E2E_ALLOW_BYPASS=1` is also set (required in every environment since #272; Playwright's webServer config sets it automatically). In production the middleware rejects it at request time unless the flag is set.

For detailed documentation:
- [Authentication User Guide](docs/user-guide/auth.md)
- [Profile Management Guide](docs/user-guide/profile-management.md)
- [API Profile Endpoints](docs/api/profile.md)

---

## 📚 Table of Contents Generation

Auto Author uses AI to generate structured table of contents from book summaries:

- **AI-Powered Analysis**: Convert summaries into comprehensive chapter structures
- **Interactive Wizard**: Step-by-step guidance through the TOC creation process
- **Clarifying Questions**: Targeted questions to improve TOC quality
- **Visual Editing**: Intuitive interface for refining the generated structure
- **Hierarchical Organization**: Support for chapters and nested subchapters

For detailed documentation about TOC generation:
- [TOC Generation User Guide](docs/user-guide/toc-generation.md)
- [API TOC Endpoints](docs/api/toc.md)
- [Troubleshooting TOC Generation](docs/user-guide/troubleshooting-toc-generation.md)

---

## 🧑‍💻 Getting Started (Development)

### Prerequisites

* Node.js (>=18)
* Python 3.10+
* MongoDB (local or Atlas)
* Docker (optional for local dev containers)

### Setup

#### 1. Clone the repository

```bash
git clone https://github.com/your-org/auto-author.git
cd auto-author
```

#### 2. Install Frontend

```bash
cd frontend
npm install
npm run dev
```

#### 3. Install Backend

```bash
cd backend
pip install
uvicorn app.main:app --reload
```

#### 4. Set Environment Variables

Copy the two examples. Unchanged, they give a working local setup against MongoDB on `localhost:27017`:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

- The two `DATABASE_NAME` values must stay the same: the backend reads the sessions better-auth writes there.
- The two `BETTER_AUTH_SECRET` values must stay the same. The example's value is refused in staging and production; generate one there with `python -c 'import secrets; print(secrets.token_urlsafe(64))'`.
- `NEXT_PUBLIC_API_URL` includes `/api/v1`.
- Set `OPENAI_API_KEY` in `backend/.env` for the AI features. Without email settings, the sign-up verification link is printed in the frontend's terminal.
- `BYPASS_AUTH` stays off. Turning it on also needs `E2E_ALLOW_BYPASS=1` (#272, #307), and production refuses it.

---

## 🤖 AI Service Error Handling

Auto Author's OpenAI integration retries transient failures and surfaces
structured errors to the client. (An earlier Redis response-cache was never
provisioned and was removed in #214; there is no cache to configure.)

**Automatic Retry with Exponential Backoff:**
- Failed AI requests retry up to `AI_MAX_RETRIES` times (default 3)
- Exponential backoff between retries (owned by a single retry layer, #188)
- Handles rate limits, timeouts, and transient API/connection errors

**Structured Failures:**
- On exhausted retries the endpoint returns a structured error (429/503/500
  with a user-facing message + retry hint), not a silent fallback
- `RateLimitError` → backoff + retry, then 429
- `APITimeoutError` / `APIConnectionError` → backoff + retry, then 503
- `InternalServerError` → backoff + retry

**Inspecting AI errors:**
```bash
# Development (local):
cd backend && uv run uvicorn app.main:app --reload 2>&1 | grep "AI Service"

# Containers (local compose or staging):
docker compose logs backend | grep "AI Service"
```

---

## 🧪 Running Tests

### Frontend Tests

```bash
cd frontend
npm run test              # Run all tests
npm run test:coverage     # Run with coverage report
npm run test:watch        # Run in watch mode
```

**Current Status:**
- **Pass Rate:** 100% (~2,180 tests across ~120 suites)
- **Coverage:** clears the CI-enforced 85% gate (statements/lines/functions ≥85%, branches ≥75%)

### Backend Tests

```bash
cd backend
uv run pytest                                           # Run all tests
uv run pytest --cov=app tests/ --cov-report=term-missing  # With coverage
```

**Current Status:**
- **Pass Rate:** 100% (~1,160 tests passing)
- **Coverage:** ~92% (CI-enforced ≥85% gate)

### E2E Tests (Playwright)

```bash
cd frontend
npx playwright test --ui    # Run with UI mode (recommended)
npx playwright test         # Run headless

# With auth bypass (for testing without real authentication)
# E2E_ALLOW_BYPASS=1 is set automatically by Playwright's webServer config
# (required alongside BYPASS_AUTH in every environment since #272).
BYPASS_AUTH=true npx playwright test
```

**Current Status:**
- Complete Playwright test suite with auth bypass support
- Test helpers for condition-based waiting (no arbitrary timeouts)
- Comprehensive page objects for all major workflows
- Test infrastructure and conventions: [docs/references/testing-infrastructure.md](docs/references/testing-infrastructure.md)

---

## 📚 Documentation

The full index is [docs/README.md](docs/README.md). The most-used entries:

- **Users:** [User manual](docs/user-guide/user-manual.md), plus per-feature guides in [docs/user-guide/](docs/user-guide/)
- **API:** [docs/api/](docs/api/) (books, chapter tabs, profile, questions, summary, TOC); the live reference is the backend's OpenAPI docs
- **Developers:** [docs/development/](docs/development/) (error handling, export, sessions, setup guides) and [CONTRIBUTING.md](CONTRIBUTING.md)
- **Deployment:** [DEPLOYMENT.md](DEPLOYMENT.md) (local setup) and [docs/STAGING-DEPLOYMENT.md](docs/STAGING-DEPLOYMENT.md) (staging)
- **Testing:** [docs/testing/](docs/testing/) and [docs/references/testing-infrastructure.md](docs/references/testing-infrastructure.md)
- **Change log:** [docs/CHANGELOG.md](docs/CHANGELOG.md)

---

## 📂 Project Structure

```
auto-author/
├── frontend/          # Next.js app
│   └── src/           # app/ (routes), components/, hooks/, lib/, types/, e2e/, __tests__/
├── backend/           # FastAPI app (uv-managed)
│   ├── app/           # api/, core/, db/, models/, schemas/, services/, utils/
│   └── tests/
├── docs/              # Documentation (index: docs/README.md)
├── scripts/           # Repo-level scripts and guard tests
└── docker-compose*.yml
```

---

## 🌟 User Workflows Supported

### Book Creation & Management
* User authentication and profile management with better-auth
* Create/update/delete books with metadata
* Book dashboard with progress tracking
* Type-to-confirm deletion with data loss warnings

### Content Development
* Summary input (text/voice) → AI-powered TOC generation
* Interactive TOC wizard with clarifying questions
* Editable TOC with hierarchical chapter structure
* Per-chapter question prompts for detailed content gathering
* Voice or text responses to prompts
* AI draft generation from Q&A responses (multiple writing styles)

### Editing & Export
* Rich text chapter editing with full formatting (TipTap)
* Auto-save with localStorage backup on network failure
* Save status indicators with visual feedback
* Chapter status workflow (draft → in-progress → completed → published)
* Export to PDF/DOCX/EPUB/Markdown with customizable options
* Progress tracking for long-running operations

### Quality & Accessibility
* Full keyboard navigation (WCAG 2.1 compliant)
* Responsive design (320px mobile to desktop)
* Screen reader support with ARIA labels
* Performance monitoring with Core Web Vitals
* Comprehensive error handling with retry logic
* Data preservation with validation and recovery

> See project documentation in `docs/` for detailed feature guides.

---

## 📦 Roadmap

### Current Sprint (Sprint 3-4 - Week 6)
* ✅ Export functionality (PDF/DOCX/EPUB/Markdown) - **COMPLETE**
* ✅ Unified error handling - **COMPLETE**
* ✅ API contract formalization - **COMPLETE**
* ✅ Book deletion UI - **COMPLETE**
* ✅ Performance monitoring - **COMPLETE**
* ✅ Loading state implementation - **COMPLETE**
* ✅ Data preservation verification - **COMPLETE**
* ✅ Responsive design validation - **COMPLETE**
* ✅ Accessibility audit preparation - **COMPLETE**
* 📋 Full accessibility audit (24h) - **NEXT**

### Sprint 5-6 (Planned)
* Collaborative editing with real-time sync
* Analytics dashboard for writing insights
* AI research assistant for content development
* Chapter-level image generation
* Mobile companion app (iOS/Android)

---

## 🔧 What's New

For the full, dated change history see [`CLAUDE.md`](CLAUDE.md). Recent highlights:

### Security & Authentication
- **better-auth**: Cookie-based session authentication (migrated from Clerk in 2025-12). httpOnly session cookies are validated on each backend request, with TOTP two-factor + backup codes and native session list/revoke.
- **Production fail-safes**: Auth bypass is hard-blocked in production and requires `E2E_ALLOW_BYPASS=1` alongside `BYPASS_AUTH` in every environment (#272/#307). Per-user AI quotas, rate limiting, and entitlement gating are enforced.

### Testing Infrastructure
- **Quality gates enforced**: CI fails builds below the 85% coverage gate, and `main` is branch-protected on the Frontend/Backend test checks (#118). Backend coverage is ~92%; frontend clears the 85% gate.
- **E2E**: Playwright suite with condition-based waiting and page objects across all major workflows.

### Export
- Four formats shipped: **PDF, DOCX, EPUB, Markdown** (single-file, plus per-chapter for EPUB/Markdown).

---

## 🧑‍🤝🧑 Contributing

We're in the early MVP phase. Contributions, suggestions, and PRs are welcome! Please check the [CONTRIBUTING.md](CONTRIBUTING.md) guidelines before submitting.

---

## 📄 License

MIT License © 2025 Noatak Enterprises, LLC, dba Bria Strategy Group

---
