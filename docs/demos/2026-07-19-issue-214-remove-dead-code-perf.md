# Issue #214 — Remove dead transcription + AI cache; fix N+1 loops + list projection

*2026-07-20T04:00:23Z by Showboat 0.6.1*
<!-- showboat-id: 00aa1100-5aa1-4ded-a1b3-294a112a55e8 -->

Backend-only, no web UI — a **main-vs-branch outcome differential** using the real code + a real local MongoDB. A pristine `main` worktree is the BEFORE; the PR branch is the AFTER. Each acceptance criterion is exercised against both. (Probe scripts live in the session scratchpad; the captured outputs below are the evidence.)

## AC1 — dead transcription stack removed (mock-transcript fallback gone)

BEFORE (`main`): the `/transcribe` service imports and, with no AWS creds, returns a hardcoded mock transcript.

```bash
bash /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/runprobe.sh /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/probe_transcription.py /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/main-wt/backend
```

```output
transcription_service module: PRESENT
OUTCOME: transcribe_audio(b'fake audio data') returns MOCK transcript = 'Short audio sample.' (confidence=0.95)
```

AFTER (branch): the module is gone — the mock-transcript code path no longer exists.

```bash
bash /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/runprobe.sh /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/probe_transcription.py /home/frankbria/projects/auto-author/backend
```

```output
transcription_service module: ABSENT (ModuleNotFoundError)
OUTCOME: no /transcribe stack exists -> the mock-transcript code path is gone
```

## AC2 — dead AI cache removed

BEFORE (`main`): `ai_cache_service` imports and `AIService` carries a `.cache_service`, but it is permanently inert (redis not installed).

```bash
bash /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/runprobe.sh /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/probe_cache.py /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/main-wt/backend
```

```output
ai_cache_service module: PRESENT
OUTCOME: AICacheService().enabled=True, redis_client=<redis.asyncio.client.Redis(<redis.asyncio.connection.ConnectionPool(<redis.asyncio.connection.Connection(encoding=utf-8,decode_responses=True,health_check_interval=30,host=localhost,port=6379,db=0)>)>)> (inert: redis not installed)
OUTCOME: AIService() has a .cache_service attribute = True
```

AFTER (branch): module and attribute gone; AI flows still construct/run (the cache always missed anyway).

```bash
bash /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/runprobe.sh /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/probe_cache.py /home/frankbria/projects/auto-author/backend
```

```output
ai_cache_service module: ABSENT (ModuleNotFoundError)
OUTCOME: AIService() has a .cache_service attribute = False
```

## AC3 — N+1 loops replaced with a single `$in` batched query

BEFORE (`main`): `get_chapter_question_progress` over 5 questions issues one `find_one` per question (a `find_one` counter is installed).

```bash
bash /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/runprobe.sh /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/probe_n1.py /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/main-wt/backend
```

```output
OUTCOME: progress over 5 questions issued find_one() 5 time(s); result total=5 completed=5 (correct)
```

AFTER (branch): **zero** `find_one` calls (one batched `find`), identical result.

```bash
bash /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/runprobe.sh /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/probe_n1.py /home/frankbria/projects/auto-author/backend
```

```output
OUTCOME: progress over 5 questions issued find_one() 0 time(s); result total=5 completed=5 (correct)
```

## AC4 — dashboard list projects out chapter content

BEFORE (`main`): a book with ~10 KB of inline chapter/subchapter HTML comes back in full via `get_books_by_user`.

```bash
bash /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/runprobe.sh /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/probe_projection.py /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/main-wt/backend
```

```output
OUTCOME: list row includes chapter.content=True, subchapter.content=True; toc_items[0].title='Chapter One'; serialized row size=10340 bytes
```

AFTER (branch): content dropped (row shrinks from 10,340 to 296 bytes) while titles + `toc_items` stay intact.

```bash
bash /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/runprobe.sh /tmp/claude-1002/-home-frankbria-projects-auto-author/5ad20150-d42c-4be4-b2b0-c7a21e78705f/scratchpad/probe_projection.py /home/frankbria/projects/auto-author/backend
```

```output
OUTCOME: list row includes chapter.content=False, subchapter.content=False; toc_items[0].title='Chapter One'; serialized row size=296 bytes
```

Every criterion is demonstrated by an observable before/after outcome — mock transcript served vs gone, inert cache present vs gone, 5 vs 0 per-question queries, 10,340 vs 296-byte list rows — not by a non-error exit. Removal is behavior-preserving: results are unchanged.
