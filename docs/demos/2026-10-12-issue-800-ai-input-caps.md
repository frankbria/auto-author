# AI requests are capped in size, and an oversize one costs nothing (#800)

*2026-10-12T05:46:35Z by Showboat 0.6.1*
<!-- showboat-id: 3449f64b-1939-4e85-8fb1-ba64fc758aa0 -->

The AI quota counts calls, not tokens, and the routes that send text to the model took text of any size. This demo sends the same requests to two real backends: one running main (2560a69) and one running this branch. Both talk to a local stand-in provider that answers every completion and writes down how many characters of prompt it was sent. Authentication is on (a seeded account and a signed session cookie), so the quota and the rate limits count as they do for a real account. Nothing here reaches a real service.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; git -C $MAIN log --oneline -1 | cut -c1-60; git -C $WT diff --stat HEAD -- backend/app | tail -1; curl -s localhost:8101/api/v1/health | cut -c1-60; curl -s localhost:8100/api/v1/health | cut -c1-60
```

```output
2560a69 fix(ai): AI requests have a time budget, and a rejec
 3 files changed, 48 insertions(+), 43 deletions(-)
{"status":"healthy","checks":{"mongodb":"ok","config":"ok"}}
{"status":"healthy","checks":{"mongodb":"ok","config":"ok"}}
```

Before. On main, a chapter of 400,000 characters goes to the provider whole, and so do fifty-one answers of 10,000 characters each. Each costs the account one generation, the same as a one-line request.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; before 'transform 400,000 characters' POST chapters/ch1/transform-style "{'content': 'x' * 400000, 'target_style': 'professional'}"; before 'draft from 51 answers of 10,000' POST chapters/ch1/generate-draft "{'question_responses': pairs(51, 10000)}"
```

```output
transform 400,000 characters                 HTTP 200 | provider received: 400766                 | charged today: 1
draft from 51 answers of 10,000              HTTP 200 | provider received: 514080                 | charged today: 2
```

After. The same two requests are answered 422. The provider receives nothing and the account is charged nothing.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; after 'transform 400,000 characters' POST chapters/ch1/transform-style "{'content': 'x' * 400000, 'target_style': 'professional'}"; after 'draft from 51 answers of 10,000' POST chapters/ch1/generate-draft "{'question_responses': pairs(51, 10000)}"
```

```output
transform 400,000 characters                 HTTP 422 | provider received: nothing                | charged today: 0
draft from 51 answers of 10,000              HTTP 422 | provider received: nothing                | charged today: 0
```

The refusal says which field is over and by what limit. It does not send the text back, and the backend log does not contain it either: the whole log for this backend is a few kilobytes after a 400,000-character request.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; after 'transform 20,001 characters' POST chapters/ch1/transform-style "{'content': 'x' * 20001, 'target_style': 'professional'}"; python3 -m json.tool $D/last-body; echo "backend log: $(wc -c < $D/backend-8100.log) bytes, lines containing the text: $(grep -c xxxxxxxxxx $D/backend-8100.log)"; grep 'Validation error' $D/backend-8100.log | tail -1 | cut -c1-140
```

```output
transform 20,001 characters                  HTTP 422 | provider received: nothing                | charged today: 0
{
    "detail": "Validation error",
    "errors": [
        {
            "type": "string_too_long",
            "loc": [
                "body",
                "content"
            ],
            "msg": "String should have at most 20000 characters",
            "ctx": {
                "max_length": 20000
            }
        }
    ],
    "error_summary": "body -> content: String should have at most 20000 characters"
}
backend log: 4637 bytes, lines containing the text: 0
ERROR:app.main:Validation error: body -> content: String should have at most 20000 characters
```

Every cap, one request each: the length of the text for the two enhance routes, and for a list of answers the count, the length of one answer, the total, and the writing style.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; after 'enhance 20,001 characters' POST chapters/ch1/enhance-text "{'content': 'x' * 20001, 'enhancement_type': 'clarity'}"; after 'clean up 20,001 dictated characters' POST chapters/ch1/enhance-transcription "{'content': 'x' * 20001}"; after 'draft: one answer of 10,001' POST chapters/ch1/generate-draft "{'question_responses': pairs(1, 10001)}"; after 'draft: 11 answers of 10,000 (total)' POST chapters/ch1/generate-draft "{'question_responses': pairs(11, 10000)}"; after 'draft: writing style of 101' POST chapters/ch1/generate-draft "{'question_responses': pairs(1), 'writing_style': 's' * 101}"; after 'contents: 51 answers' POST generate-toc "{'question_responses': pairs(51)}"; after 'contents: 11 answers of 10,000 (total)' POST generate-toc "{'question_responses': pairs(11, 10000)}"
```

```output
enhance 20,001 characters                    HTTP 422 | provider received: nothing                | charged today: 0
clean up 20,001 dictated characters          HTTP 422 | provider received: nothing                | charged today: 0
draft: one answer of 10,001                  HTTP 422 | provider received: nothing                | charged today: 0
draft: 11 answers of 10,000 (total)          HTTP 422 | provider received: nothing                | charged today: 0
draft: writing style of 101                  HTTP 422 | provider received: nothing                | charged today: 0
contents: 51 answers                         HTTP 422 | provider received: nothing                | charged today: 0
contents: 11 answers of 10,000 (total)       HTTP 422 | provider received: nothing                | charged today: 0
```

A request exactly at the caps still works: the provider receives it and the account is charged one generation for each.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; after 'transform exactly 20,000 characters' POST chapters/ch1/transform-style "{'content': 'x' * 20000, 'target_style': 'professional'}"; after 'draft: 50 answers, 100,000 in total' POST chapters/ch1/generate-draft "{'question_responses': pairs(50, 1973)}"
```

```output
transform exactly 20,000 characters          HTTP 200 | provider received: 20766                  | charged today: 1
draft: 50 answers, 100,000 in total          HTTP 200 | provider received: 102671                 | charged today: 2
```

Answers are capped where they are saved too, because a saved answer comes back later as model input. The contents wizard refuses fifty-one answers and keeps nothing; one answer of exactly 10,000 characters is saved.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; after 'save 51 answers' PUT question-responses "{'responses': pairs(51)}"; curl -s -b "$(cat $D/cookie-aa_demo_800)" localhost:8100/api/v1/books/$(cat $D/book-8100)/question-responses | python3 -c 'import sys,json; d=json.load(sys.stdin); print("  saved answers:", len(d["responses"]))'; after 'save one answer of 10,000' PUT question-responses "{'responses': pairs(1, 10000)}"; curl -s -b "$(cat $D/cookie-aa_demo_800)" localhost:8100/api/v1/books/$(cat $D/book-8100)/question-responses | python3 -c 'import sys,json; d=json.load(sys.stdin); print("  saved answers:", len(d["responses"]), "of", len(d["responses"][0]["answer"]), "characters")'
```

```output
save 51 answers                              HTTP 422 | provider received: nothing                | charged today: 2
  saved answers: 0
save one answer of 10,000                    HTTP 200 | provider received: nothing                | charged today: 2
  saved answers: 1 of 10000 characters
```

The same behaviour as tests: real routes and real MongoDB counters, with the provider stubbed at the wire. Each oversize case asserts the 422, that no model call was made, and that nothing was charged.

```bash
cd /home/frankbria/projects/worktrees/issue-800-ai-input-caps/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo800 uv run pytest tests/test_api/test_ai_input_caps.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1 | sed 's/ in [0-9.]*s//'
```

```output
============================== 22 passed ==============================
```
