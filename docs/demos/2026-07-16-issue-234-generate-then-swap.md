# Bulk question regeneration: generate-then-swap avoids empty-chapter window on AI outage (#234)

*2026-07-16T21:28:00Z by Showboat 0.6.1*
<!-- showboat-id: 7ccdd963-7288-440d-8d8c-7551da7aa646 -->

Issue #234: bulk question regeneration deleted a chapter's existing questions BEFORE generating the replacements. Since #182 a genuine OpenAI outage correctly surfaces as a structured 503 — but the delete already ran, so the chapter is left with **zero questions** until the user retries. User-authored answers were never lost (answered questions are preserved), but reproducible machine-generated questions vanished. The fix reorders to **generate-then-swap**: persist the new batch first, then delete the old set excluding the new ids. On an outage the delete is never reached.

The change is purely an ordering of side-effects in `regenerate_chapter_questions`. Here is the core reorder (delete now happens AFTER a successful generate):

```bash
git -C /home/frankbria/projects/auto-author show HEAD -- backend/app/services/question_generation_service.py | sed -n "/Generate AND persist the new batch FIRST/,/exclude_ids=new_ids,/p"
```

```output
+        # Generate AND persist the new batch FIRST. On an AI outage this raises before
+        # any delete, so the chapter keeps its existing questions until the user retries
+        # (no empty-chapter window). User-authored answers are untouched either way.
+        result = await self.generate_questions_for_chapter(
             book_id=book_id,
             chapter_id=chapter_id,
+            count=new_count,
+            difficulty=difficulty,
+            focus=focus,
             user_id=user_id,
-            preserve_with_responses=preserve_responses
+            current_user=current_user,
+            previous_questions=regen_context["previous_questions"],
+            feedback_guidance=regen_context["feedback_guidance"]
         )
 
-        # Generate new questions to replace deleted ones
-        new_count = count if not preserve_responses else deleted_count
-        if new_count > 0:
-            result = await self.generate_questions_for_chapter(
-                book_id=book_id,
-                chapter_id=chapter_id,
-                count=new_count,
-                difficulty=difficulty,
-                focus=focus,
-                user_id=user_id,
-                current_user=current_user,
-                previous_questions=regen_context["previous_questions"],
-                feedback_guidance=regen_context["feedback_guidance"]
-            )
+        # Swap out the old questions now that the replacements are safely persisted,
+        # excluding the ids we just created (they have no responses, so a preserve
+        # delete would otherwise sweep them up).
+        new_ids = {q.id for q in result.questions}
+        deleted_count = await delete_questions_for_chapter(
+            book_id=book_id,
+            chapter_id=chapter_id,
+            user_id=user_id,
+            preserve_with_responses=preserve_responses,
+            exclude_ids=new_ids,
```

Setup: a real local MongoDB and two copies of the service — a pristine `main` worktree (delete-first) at `/tmp/aa-main-234` and this branch (generate-then-swap). A small harness (`demo_234.py`) seeds a chapter with 4 unanswered questions, drives `regenerate_chapter_questions` with an AI stub that raises `AIServiceError` (the outage), and then reads the questions still in Mongo. Both worktrees hit the SAME outage — the only variable is the delete ordering.

=== main (delete-first): the bug. Chapter starts with 4 questions; the AI outage raises AI_UNAVAILABLE; the chapter is left EMPTY. ===

```bash
cd /tmp/aa-main-234/backend && PYTHONPATH=$PWD BYPASS_AUTH=true uv run python /tmp/claude-1002/-home-frankbria-projects-auto-author/6f19cf12-6ed9-4159-bff7-130f47bfd28b/scratchpad/demo_234.py outage aa_demo234_main 2>/dev/null
```

```output
questions_before=4
ai_outage_raised=AI_UNAVAILABLE
questions_after_outage=0
outcome=EMPTY-CHAPTER WINDOW (data lost)
```

=== this branch (generate-then-swap): the fix. Same outage, same AI_UNAVAILABLE — but the delete is never reached, so all 4 questions survive for the retry. ===

```bash
cd /home/frankbria/projects/auto-author/backend && PYTHONPATH=$PWD BYPASS_AUTH=true uv run python /tmp/claude-1002/-home-frankbria-projects-auto-author/6f19cf12-6ed9-4159-bff7-130f47bfd28b/scratchpad/demo_234.py outage aa_demo234_branch 2>/dev/null
```

```output
questions_before=4
ai_outage_raised=AI_UNAVAILABLE
questions_after_outage=4
outcome=INTACT (chapter survives outage)
```

The happy path is unchanged: with the AI healthy, answered questions and their answers are preserved and only the unanswered ones are swapped. (Seeded 2 answered + 2 unanswered; the service floors a regenerate batch at 3, so the final set is 2 preserved + 3 fresh = 5 — a pre-existing clamp, not from this change. The point: no answer is lost.)

```bash
cd /home/frankbria/projects/auto-author/backend && PYTHONPATH=$PWD BYPASS_AUTH=true uv run python /tmp/claude-1002/-home-frankbria-projects-auto-author/6f19cf12-6ed9-4159-bff7-130f47bfd28b/scratchpad/demo_234.py happy aa_demo234_branch 2>/dev/null
```

```output
questions_before=4
new_count=2 preserved_count=2
questions_after=5
kept_answers:
  - 'Pre-existing question 0' -> answer 'My hard-won answer 0'
  - 'Pre-existing question 1' -> answer 'My hard-won answer 1'
```

N5 (folded in from the #233 review): the PLOT fallback template hardcoded "Chapter" instead of the real chapter title. With the chapter titled "The Midnight Heist" and the AI returning nothing usable (template fallback), main renders the placeholder, branch renders the real title.

```bash
cd /tmp/aa-main-234/backend && PYTHONPATH=$PWD BYPASS_AUTH=true uv run python /tmp/claude-1002/-home-frankbria-projects-auto-author/6f19cf12-6ed9-4159-bff7-130f47bfd28b/scratchpad/demo_234.py title aa_demo234_main 2>/dev/null | grep -E 'conflict|renders_real|hardcoded'
```

```output
  plot_q: What is the main event or conflict in Chapter?
renders_real_title=False
has_hardcoded_Chapter_placeholder=True
```

```bash
cd /home/frankbria/projects/auto-author/backend && PYTHONPATH=$PWD BYPASS_AUTH=true uv run python /tmp/claude-1002/-home-frankbria-projects-auto-author/6f19cf12-6ed9-4159-bff7-130f47bfd28b/scratchpad/demo_234.py title aa_demo234_branch 2>/dev/null | grep -E 'conflict|renders_real|hardcoded'
```

```output
  plot_q: What is the main event or conflict in The Midnight Heist?
renders_real_title=True
has_hardcoded_Chapter_placeholder=False
```

Tests: 5 new-behavior service pins + 4 real-Mongo DAO pins, all mutation-verified — reintroducing delete-before-generate fails the outage/ordering pins; dropping exclude_ids fails the swap pins; reverting the title threading fails the fallback pin.

```bash
cd /home/frankbria/projects/auto-author/backend && uv run pytest tests/test_services/test_question_generation_service.py::TestRegenerate tests/test_services/test_question_generation_service.py::TestProcessGeneratedQuestions::test_fallback_renders_real_chapter_title tests/test_db/test_question_regeneration_swap.py -q -p no:cacheprovider 2>&1 | grep -E 'passed|failed' | sed -E 's/ in [0-9.]+s.*//'
```

```output
============================== 9 passed
```
