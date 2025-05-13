# ✍️ Auto Author

**Auto Author** is an AI-powered application designed to help users write long-form non-fiction books. It streamlines the writing process by guiding users from concept to draft using a unique combination of interactive interviews, voice/text input, and generative AI.

---

## 🚀 Features

* 🎯 AI-generated **Table of Contents** from summaries (text or voice)
* 🧠 **Interview-style questions** per chapter to gather detailed content
* ✍️ **Chapter-by-chapter editing** in a clean, tabbed interface
* \u🔁 Regeneration of TOC, prompts, and content at any stage
* 🔐 Secure **user authentication** and profile management
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
| Auth           | JWT-based auth or Clerk/Auth0     |
| AI Integration | OpenAI (or local LLM)             |
| Voice Input    | Web Speech API / Whisper API      |

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

Create `.env` files for both frontend and backend:

**`.env.local` (frontend)**

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**`.env` (backend)**

```
MONGODB_URI=mongodb://localhost:27017/auto_author
JWT_SECRET=your_secret
OPENAI_API_KEY=sk-...
```

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