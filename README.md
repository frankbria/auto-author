# ✍️ Auto Author

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
* 🔐 Secure **user authentication** with Clerk and profile management
* 📚 Full **CRUD functionality** for books, chapters, and metadata
* 🎤 **Voice input** support via Web Speech API (production ready)
* 💾 **Auto-save** with 3-second debounce and localStorage backup on network failure
* 📊 **Save status indicators** with visual feedback (Saving/Saved/Error)
* ⌨️ **Full keyboard accessibility** (WCAG 2.1 Level AA compliant)
* 📱 **Responsive design** supporting devices from 320px (iPhone SE) to desktop
* 🎯 **Touch target compliance** (100% WCAG 2.1 Level AAA - 44x44px minimum)

### Production Features
* 📤 **Export functionality** (PDF/DOCX with customizable options)
* 🔄 **Unified error handling** with automatic retry logic and user notifications
* ⚠️ **Book deletion protection** with type-to-confirm and data loss warnings
* 📈 **Performance monitoring** with Core Web Vitals tracking
* ⏳ **Loading state indicators** with progress bars and time estimates
* 🛡️ **Data preservation** with validation, TTL-based cleanup, and recovery UI
* 🧪 **Comprehensive test coverage** (86.2% overall, 100% pass rate)

---

## 🧱 Tech Stack

| Layer          | Technology                        |
| -------------- | --------------------------------- |
| Frontend       | Next.js (TypeScript), TailwindCSS |
| Backend API    | FastAPI                           |
| Database       | MongoDB (Atlas or self-hosted)    |
| Auth           | Clerk Authentication               |
| AI Integration | OpenAI (or local LLM)             |
| Voice Input    | Web Speech API / Whisper API      |

---

## 🔐 Authentication with Clerk

Auto Author uses Clerk for authentication, providing:

- Secure user registration and login
- Social login options (Google, GitHub, etc.)
- Multi-factor authentication
- Email verification
- Session management across devices
- Password reset functionality

While Clerk manages authentication, we maintain a local user table in our MongoDB database that maps Clerk user IDs to our application's user entities. This approach allows us to:

1. Associate user-generated content (books, chapters, etc.) with specific users
2. Store application-specific user preferences and metadata
3. Implement role-based permissions within our application
4. Maintain data relationships without exposing authentication details

The architecture separates authentication concerns (handled by Clerk) from application data management (handled by our backend), creating a more secure and maintainable system.

For detailed documentation about our Clerk integration:
- [Clerk Integration Guide](docs/clerk-integration-guide.md)
- [Authentication User Guide](docs/user-guide-auth.md)
- [Clerk Deployment Checklist](docs/clerk-deployment-checklist.md)
- [Profile Management Guide](docs/profile-management-guide.md)
- [API Profile Endpoints](docs/api-profile-endpoints.md)

## 📚 Table of Contents Generation

Auto Author uses AI to generate structured table of contents from book summaries:

- **AI-Powered Analysis**: Convert summaries into comprehensive chapter structures
- **Interactive Wizard**: Step-by-step guidance through the TOC creation process
- **Clarifying Questions**: Targeted questions to improve TOC quality
- **Visual Editing**: Intuitive interface for refining the generated structure
- **Hierarchical Organization**: Support for chapters and nested subchapters

For detailed documentation about TOC generation:
- [TOC Generation Requirements](docs/toc-generation-requirements.md)
- [TOC Generation User Guide](docs/user-guide-toc-generation.md)
- [API TOC Endpoints](docs/api-toc-endpoints.md)
- [Troubleshooting TOC Generation](docs/troubleshooting-toc-generation.md)

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

Create `.env` files for both frontend and backend:

**`.env.local` (frontend)**

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_*****
CLERK_SECRET_KEY=sk_*****
```

**`.env` (backend)**

```
MONGODB_URI=mongodb://localhost:27017/auto_author
CLERK_SECRET_KEY=sk_*****
CLERK_WEBHOOK_SECRET=whsec_*****
OPENAI_API_KEY=sk-...
```

---

## 📚 Documentation

Auto Author comes with comprehensive documentation to help you understand and use the system effectively:

### Documentation Indexes
- [Profile Documentation Index](docs/profile-documentation-index.md) - Complete index of profile-related docs

### Authentication & Profile Management
- [Clerk Integration Guide](docs/clerk-integration-guide.md) - How Clerk authentication is integrated
- [Authentication User Guide](docs/user-guide-auth.md) - User-facing authentication guide
- [Profile Management Guide](docs/profile-management-guide.md) - Features and usage of profile management
- [Frontend Profile Components](docs/frontend-profile-components.md) - Technical docs for profile UI components
- [Profile Testing Guide](docs/profile-testing-guide.md) - Testing and CI/CD for profile features
- [Auth Troubleshooting](docs/auth-troubleshooting.md) - Solutions for common authentication issues

### API References
- [API Authentication Endpoints](docs/api-auth-endpoints.md) - Authentication API documentation
- [API Profile Endpoints](docs/api-profile-endpoints.md) - Profile management API documentation

### Technical Guides
- [Clerk Deployment Checklist](docs/clerk-deployment-checklist.md) - Deployment considerations
- [Session Management](docs/session-management.md) - How user sessions are managed
- [Login/Logout Flows](docs/login-logout-flows.md) - Detailed authentication flows

---

## 🤪 Running Tests

### Frontend

```bash
npm run test
```

### Backend

```bash
pytest
```

---

## 📂 Project Structure

```
auto-author/
|
├── frontend/                # Next.js UI
│   ├── components/
│   ├── pages/
│   └── styles/
|
├── backend/                 # FastAPI backend
│   ├── app/
│   └── tests/
|
├── docs/                    # Project documentation
└── README.md
```

---

## 🌟 User Workflows Supported

### Book Creation & Management
* User authentication and profile management with Clerk
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
* Export to PDF/DOCX with customizable options
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
* ✅ Export functionality (PDF/DOCX) - **COMPLETE**
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
* Additional export formats (EPUB, Markdown)
* Analytics dashboard for writing insights
* AI research assistant for content development
* Chapter-level image generation
* Mobile companion app (iOS/Android)

---

## 🧑‍🤝🧑 Contributing

We're in the early MVP phase. Contributions, suggestions, and PRs are welcome! Please check the [CONTRIBUTING.md](CONTRIBUTING.md) guidelines before submitting.

---

## 📄 License

MIT License © 2025 Noatak Enterprises, LLC, dba Bria Strategy Group

---