# Demo: Draft generation honors the UI's 5,000-word option (#232)

**Acceptance criterion:** The UI offers "5,000 words (Extended)" for chapter
drafts, but the backend's hardcoded `gpt-4` (8192-token shared context) capped
completions at `DRAFT_MAX_COMPLETION_TOKENS = 4000` (~2500–3000 words), so the
top option could never be satisfied. The fix must make that option serviceable.

## Method

The local OpenAI key is stale/401 in this environment, so a live 5,000-word
generation isn't runnable. Instead we observe the request **at the wire
boundary the fix changes**: what `model` and `max_tokens` the real
`AIService.generate_chapter_draft` sends to OpenAI for the 5,000-word option,
comparing a **pristine `main` worktree** against the **#232 branch**. The
completion cap is what physically bounds output length, so this is the decisive
evidence — a 4000-token cap on gpt-4 cannot produce 5,000 words; an 8000-token
budget on gpt-4o can.

The reproduction script below drives the real service against a fake
`chat.completions.create` that records the kwargs, for `target_length=5000`.
It also drives a non-draft flow (`analyze_summary_for_toc`) to prove the model
change is scoped to drafts. Run it from a `backend/` checkout with
`PYTHONPATH=. uv run python <script>` against each of the two versions.

<details>
<summary>Reproduction script</summary>

```python
import asyncio, types
from unittest.mock import MagicMock
from app.services.ai_service import AIService

async def main():
    svc = AIService(cache_service=MagicMock())
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        msg = types.SimpleNamespace(content="A complete draft. " * 50)
        choice = types.SimpleNamespace(message=msg, finish_reason="stop")
        return types.SimpleNamespace(choices=[choice])
    svc.client = MagicMock()
    svc.client.chat.completions.create = create

    await svc.generate_chapter_draft(
        chapter_title="Ch", chapter_description="d",
        question_responses=[], book_metadata={}, target_length=5000)
    draft = calls[-1]
    calls.clear()
    await svc.analyze_summary_for_toc("A book summary. " * 20)
    analyze = calls[-1]

    print(f"service default model (self.model):  {svc.model}\n")
    print("5,000-word draft request sent to OpenAI:")
    print(f"    model      = {draft['model']}")
    print(f"    max_tokens = {draft['max_tokens']}")
    servable = draft["max_tokens"] >= int(5000 * 1.6)
    print(f"    -> honors full 5,000-word budget (>= 8000 tokens)? {servable}")
    if not servable:
        print(f"    -> capped at ~{int(draft['max_tokens']/1.6)} words "
              f"on {draft['model']} (cannot reach 5,000)")
    print("\nNon-draft flow (analyze_summary_for_toc) request:")
    print(f"    model      = {analyze['model']}   (must stay gpt-4 — scoping)")

asyncio.run(main())
```

</details>

## Result

### `main` (before the fix)

```
service default model (self.model):  gpt-4

5,000-word draft request sent to OpenAI:
    model      = gpt-4
    max_tokens = 4000
    -> honors full 5,000-word budget (>= 8000 tokens)? False
    -> capped at ~2500 words on gpt-4 (cannot reach 5,000)

Non-draft flow (analyze_summary_for_toc) request:
    model      = gpt-4   (must stay gpt-4 — scoping)
```

The 5,000-word request is clamped to a 4000-token completion on gpt-4 — the UI
option is structurally unserviceable.

### `feature/232-draft-output-ceiling` (the fix)

```
service default model (self.model):  gpt-4

5,000-word draft request sent to OpenAI:
    model      = gpt-4o
    max_tokens = 8000
    -> honors full 5,000-word budget (>= 8000 tokens)? True

Non-draft flow (analyze_summary_for_toc) request:
    model      = gpt-4   (must stay gpt-4 — scoping)
```

The 5,000-word request now targets gpt-4o with the full 8000-token budget
(5000 words × 1.6) — the option is serviceable. The non-draft flow still uses
gpt-4, so the model change is scoped to draft generation only.

## The only variable is the diff

Both runs use the same demo script, same venv deps, same fake wire recorder —
only the checked-out `ai_service.py` differs. The service default (`self.model`)
stays gpt-4 in both; only the per-call draft override changed.
