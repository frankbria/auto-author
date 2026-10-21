# 010 — books.py Decomposition Map

Deliverable for issue #94 (P3.1). Catalogs every route handler in
`backend/app/api/endpoints/books.py` by concern cluster, so each remaining slice
can be extracted in its own follow-up plan using the same
characterization-then-extract discipline proven here.

**Snapshot**: `books.py` at extraction time = **3,496 lines, 43 handlers** (drift
re-derived from the plan's original 3,184). Line ranges below are from that
pre-extraction snapshot (`git show <pre-#94>:…/books.py`). The **chapters** slice
has since been extracted to `chapters.py` (this PR); its rows are marked ✅.

**Key structural fact**: `books.py` has **no module-level helper functions** —
every `def`/`async def` is a route handler. So a cluster's only cross-file
dependencies are module imports + shared services. The shared service used across
multiple clusters is `chapter_access_service` (chapters, content, questions);
`chapter_status_service` is chapters-only. This is why chapters extracted with
zero helper duplication.

## Handlers by cluster

### book-crud (7) — `/books/...`
| Method | Path | Handler | Line |
|---|---|---|---|
| POST | `/` | create_new_book | 109 |
| GET | `/` | get_user_books | 165 |
| GET | `/{book_id}` | get_book | 197 |
| PUT | `/{book_id}` | update_book_details | 259 |
| PATCH | `/{book_id}` | patch_book_details | 352 |
| DELETE | `/{book_id}` | delete_book_endpoint | 440 |
| POST | `/{book_id}/cover-image` | upload_book_cover_image | 508 |

### summaries (4)
| Method | Path | Handler | Line |
|---|---|---|---|
| GET | `/{book_id}/summary` | get_book_summary | 585 |
| PUT | `/{book_id}/summary` | update_book_summary | 606 |
| PATCH | `/{book_id}/summary` | patch_book_summary | 666 |
| POST | `/{book_id}/analyze-summary` | analyze_book_summary | 720 |

### pre-toc / book-level questions (3)
| Method | Path | Handler | Line |
|---|---|---|---|
| POST | `/{book_id}/generate-questions` | generate_clarifying_questions | 841 |
| GET | `/{book_id}/question-responses` | get_question_responses | 970 |
| PUT | `/{book_id}/question-responses` | save_question_responses | 1005 |

### toc (4)
| Method | Path | Handler | Line |
|---|---|---|---|
| GET | `/{book_id}/toc-readiness` | check_toc_generation_readiness | 1074 |
| POST | `/{book_id}/generate-toc` | generate_table_of_contents | 1174 |
| GET | `/{book_id}/toc` | get_book_toc | 1312 |
| PUT | `/{book_id}/toc` | update_book_toc | 1365 |

### chapters ✅ EXTRACTED → `chapters.py` (9)
| Method | Path | Handler | Line |
|---|---|---|---|
| POST | `/{book_id}/chapters` | create_chapter | 1442 |
| GET | `/{book_id}/chapters/metadata` | get_chapters_metadata | 1511 |
| GET | `/{book_id}/chapters/tab-state` | get_tab_state | 1588 |
| GET | `/{book_id}/chapters/{chapter_id}` | get_chapter | 1627 |
| PUT | `/{book_id}/chapters/{chapter_id}` | update_chapter | 1674 |
| DELETE | `/{book_id}/chapters/{chapter_id}` | delete_chapter | 1752 |
| GET | `/{book_id}/chapters` | list_chapters | 1802 |
| PATCH | `/{book_id}/chapters/bulk-status` | update_chapter_status_bulk | 1868 |
| POST | `/{book_id}/chapters/tab-state` | save_tab_state | 1962 |

### chapter-content / analytics (4) — *next suggested slice*
| Method | Path | Handler | Line |
|---|---|---|---|
| GET | `/{book_id}/chapters/{chapter_id}/content` | get_chapter_content | 2000 |
| PATCH | `/{book_id}/chapters/{chapter_id}/content` | update_chapter_content | 2086 |
| GET | `/{book_id}/chapters/{chapter_id}/analytics` | get_chapter_analytics | 2186 |
| POST | `/{book_id}/chapters/batch-content` | batch_get_chapter_content | 2236 |

### chapter-questions (7)
| Method | Path | Handler | Line |
|---|---|---|---|
| POST | `/{book_id}/chapters/{chapter_id}/generate-questions` | generate_chapter_questions | 2338 |
| GET | `/{book_id}/chapters/{chapter_id}/questions` | list_chapter_questions | 2440 |
| PUT | `/{book_id}/chapters/{chapter_id}/questions/{question_id}/response` | save_question_response | 2542 |
| GET | `/{book_id}/chapters/{chapter_id}/questions/{question_id}/response` | get_question_response | 2651 |
| POST | `/{book_id}/chapters/{chapter_id}/questions/{question_id}/rating` | rate_question | 2722 |
| GET | `/{book_id}/chapters/{chapter_id}/question-progress` | get_chapter_question_progress | 2826 |
| POST | `/{book_id}/chapters/{chapter_id}/regenerate-questions` | regenerate_chapter_questions | 2902 |

### chapter-drafts / style / enhance (5)
| Method | Path | Handler | Line |
|---|---|---|---|
| POST | `/{book_id}/chapters/{chapter_id}/generate-draft` | generate_chapter_draft | 3011 |
| POST | `/{book_id}/chapters/{chapter_id}/transform-style` | transform_chapter_style | 3147 |
| POST | `/{book_id}/chapters/{chapter_id}/enhance-text` | enhance_chapter_text | 3211 |
| POST | `/{book_id}/chapters/{chapter_id}/enhance-transcription` | enhance_chapter_transcription | 3292 |
| POST | `/{book_id}/chapters/{chapter_id}/questions/responses/batch` | save_question_responses_batch_endpoint | 3366 |

## Suggested extraction order (fewest shared deps first)
1. **chapters** ✅ done — self-contained, `chapter_status_service` only.
2. **chapter-content/analytics** — shares only `chapter_access_service` (imported, not duplicated).
3. **chapter-questions** — `question_generation_service` + question schemas cluster together.
4. **chapter-drafts/style/enhance** — `ai_service` + style/enhancement services.
5. **summaries**, **toc**, **pre-toc questions** — book-level AI; can fold into books or a `book_ai.py`.
   Leaves `books.py` = book-crud + cover only; fold `book_cover_upload.py` in then.

## Route-ordering caveat (must hold for every future slice)
Literal chapter sub-paths (`/chapters/metadata`, `/chapters/tab-state`,
`/chapters/bulk-status`, `/chapters/batch-content`) must be registered **before**
`/chapters/{chapter_id}` (and its sub-routes) or FastAPI matches them as
`chapter_id="metadata"` and 404s. Within a single extracted router, preserve the
original handler order. Across routers, mount order in `router.py` matters.
`test_chapters_characterization.py` locks this for the chapters slice.
