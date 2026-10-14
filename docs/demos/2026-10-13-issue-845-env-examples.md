# Issue #845: the env examples, copied unchanged, give a working local setup

*2026-10-14T05:26:34Z by Showboat 0.6.1*
<!-- showboat-id: 044f9a84-d962-4a26-8338-ab8649117483 -->

Three acceptance criteria: copying both examples unchanged gives a working local sign-in and book list; current variable names are used and `ENVIRONMENT` is present; `docker compose config` validates.

`journey.sh` copies a checkout's `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env.local`, unchanged, and starts the backend on 8000 and the frontend on 3000 with them, against the MongoDB on this machine. It signs up through the frontend, opens the verification link the dev server prints (no email provider is set, as in the examples), and then calls the API where the browser would, at `NEXT_PUBLIC_API_URL`, with the session cookie. Afterwards it stops both, restores any env files that were there and deletes the account. Main's files come from a scratch checkout of main.

## Before: main's examples

The backend reads `auto_author_test`, the frontend writes sessions to `auto_author`, and `NEXT_PUBLIC_API_URL` has no `/api/v1`. Every call the browser makes is a 404. With the prefix put in by hand, the session is not found: 401.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo845/journey.sh /home/frankbria/projects/worktrees/main845 main
```

```output
copied unchanged: yes
backend database: auto_author_test, frontend database: auto_author, the browser calls the API at: http://localhost:8000
sign up: 200
open the emailed link: 302
session cookie in the jar: 1
GET  $NEXT_PUBLIC_API_URL/users/me: 404
GET  http://localhost:8000/api/v1/users/me, the prefix put in by hand: 401
POST $NEXT_PUBLIC_API_URL/books/: 404
GET  $NEXT_PUBLIC_API_URL/books/: 404 (no list)
the demo account is removed (3 documents)
```

## After: this branch's examples

One database name, the prefix included: signed in, the user is found, a book is created and listed.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo845/journey.sh /home/frankbria/projects/worktrees/issue-845-env-examples branch
```

```output
copied unchanged: yes
backend database: auto_author, frontend database: auto_author, the browser calls the API at: http://localhost:8000/api/v1
sign up: 200
open the emailed link: 302
session cookie in the jar: 1
GET  $NEXT_PUBLIC_API_URL/users/me: 200
GET  http://localhost:8000/api/v1/users/me, the prefix put in by hand: 200
POST $NEXT_PUBLIC_API_URL/books/: 201
GET  $NEXT_PUBLIC_API_URL/books/: 200 (Small Changes)
the demo account is removed (5 documents)
```

## Variable names

The backend example uses `MONGODB_URI` and `OPENAI_API_KEY`, the names the settings read first and the compose file requires, where it had `DATABASE_URL` and `OPENAI_AUTOAUTHOR_API_KEY`. `ENVIRONMENT` was already there.

```bash
cd /home/frankbria/projects/worktrees/issue-845-env-examples && grep -E '^(ENVIRONMENT|MONGODB_URI|DATABASE_URL|DATABASE_NAME|OPENAI_API_KEY|OPENAI_AUTOAUTHOR_API_KEY)=' backend/.env.example; echo '--- main:'; grep -E '^(ENVIRONMENT|MONGODB_URI|DATABASE_URL|DATABASE_NAME|OPENAI_API_KEY|OPENAI_AUTOAUTHOR_API_KEY)=' /home/frankbria/projects/worktrees/main845/backend/.env.example
```

```output
ENVIRONMENT=development
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=auto_author
OPENAI_API_KEY=sk-your-openai-api-key-here
--- main:
ENVIRONMENT=development
DATABASE_URL=mongodb://localhost:27017
DATABASE_NAME=auto_author_test
OPENAI_AUTOAUTHOR_API_KEY=sk-your-openai-api-key-here
```

## docker compose config

The compose file with the backend example as its `.env`, unchanged. Main's fails on the two names it requires and the example did not have.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo845/compose.sh /home/frankbria/projects/worktrees/main845 main; bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo845/compose.sh /home/frankbria/projects/worktrees/issue-845-env-examples branch
```

```output
main: docker compose config exited 1
error while interpolating services.backend.environment.MONGODB_URI: required variable MONGODB_URI is missing a value: MONGODB_URI is required
error while interpolating services.backend.environment.OPENAI_API_KEY: required variable OPENAI_API_KEY is missing a value: OPENAI_API_KEY is required
error while interpolating services.frontend.environment.DATABASE_URL: required variable MONGODB_URI is missing a value: MONGODB_URI is required
branch: docker compose config exited 0
  DATABASE_NAME: auto_author
  DATABASE_URL: mongodb://localhost:27017
  ENVIRONMENT: development
  MONGODB_URI: mongodb://localhost:27017
  OPENAI_API_KEY: sk-your-openai-api-key-here
```
