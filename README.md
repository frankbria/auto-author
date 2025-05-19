# ✍️ Auto Author

**Auto Author** is an AI-powered application designed to help users write long-form non-fiction books. It streamlines the writing process by guiding users from concept to draft using a unique combination of interactive interviews, voice/text input, and generative AI.

---

## 🚀 Features

* 🎯 AI-generated **Table of Contents** from summaries (text or voice)
* 🧠 **Interview-style questions** per chapter to gather detailed content
* ✍️ **Chapter-by-chapter editing** in a clean, tabbed interface
* \u🔁 Regeneration of TOC, prompts, and content at any stage
* 🔐 Secure **user authentication** with Clerk and profile management
* 📚 Full **CRUD functionality** for books, chapters, and metadata
* 🎤 Voice-to-text support across all input fields
* 💾 **Auto-saving** and persistent storage of user data
* 🧼 A distraction-free, responsive UI with TOC sidebar navigation

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

## 🌟 Core User Stories Covered

* User authentication (register, login, profile editing)
* Create/update book metadata
* Summary input (text/voice) → TOC generation
* Editable TOC with drag-and-drop and persistence
* Per-chapter question prompts and AI-generated draft content
* Voice or text responses to prompts
* Draft editing with autosave and versioning
* Regenerate any part of the process (TOC, prompts, content)

> See `user-stories.md` for full detail of all implemented and future-planned functionality.

---

## 📦 Planned Extensions

* Collaborative editing
* Book export (PDF, EPUB, DOCX)
* Analytics dashboard for writing insights
* AI research assistant
* Chapter-level image generation

---

## 🧑‍🤝🧑 Contributing

We're in the early MVP phase. Contributions, suggestions, and PRs are welcome! Please check the [CONTRIBUTING.md](CONTRIBUTING.md) guidelines before submitting.

---

## 📄 License

MIT License © 2025 Auto Author Team

---