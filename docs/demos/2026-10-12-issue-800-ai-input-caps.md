# AI requests are capped in size, and an oversize one costs nothing (#800)

*2026-10-12T06:24:21Z by Showboat 0.6.1*
<!-- showboat-id: 28e97205-643d-4dde-bdcf-49be7d4b5ed1 -->

The AI quota counts calls, not tokens, and the routes that send text to the model took text of any size. This demo sends the same requests to two real backends: one running main and one running this branch. Both talk to a local stand-in provider that answers every completion and writes down how many characters of prompt it was sent. Authentication is on (a seeded account and a signed session cookie), so the quota and the rate limits count as they do for a real account. Nothing here reaches a real service.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; echo "main:   $(git -C $MAIN log --oneline -1 | cut -c1-7)  $(curl -s localhost:8101/api/v1/health | cut -c1-60)"; echo "branch: $(git -C $WT rev-parse --abbrev-ref HEAD)  $(curl -s localhost:8100/api/v1/health | cut -c1-60)"
```

```output
main:   8abfd43  {"status":"healthy","checks":{"mongodb":"ok","config":"ok"}}
branch: feature/issue-800-ai-input-caps  {"status":"healthy","checks":{"mongodb":"ok","config":"ok"}}
```

Before. On main, a chapter of 400,000 characters goes to the provider whole, and so do 101 answers of 10,000 characters each: a prompt of over a million characters. Each costs the account one generation, the same as a one-line request.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; before 'transform 400,000 characters' POST chapters/ch1/transform-style "{'content': 'x' * 400000, 'target_style': 'professional'}"; before 'draft from 101 answers of 10,000' POST chapters/ch1/generate-draft "{'question_responses': pairs(101, 10000)}"
```

```output
transform 400,000 characters                 HTTP 200 | provider received: 400766                 | charged today: 1
draft from 101 answers of 10,000             HTTP 200 | provider received: 1017030                | charged today: 2
```

After. The same two requests are answered 422. The provider receives nothing and the account is charged nothing.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; after 'transform 400,000 characters' POST chapters/ch1/transform-style "{'content': 'x' * 400000, 'target_style': 'professional'}"; after 'draft from 101 answers of 10,000' POST chapters/ch1/generate-draft "{'question_responses': pairs(101, 10000)}"
```

```output
transform 400,000 characters                 HTTP 422 | provider received: nothing                | charged today: 0
draft from 101 answers of 10,000             HTTP 422 | provider received: nothing                | charged today: 0
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
backend log: 4640 bytes, lines containing the text: 0
ERROR:app.main:Validation error: body -> content: String should have at most 20000 characters
```

Every cap, one request each: the length of the text for the two enhance routes, and for a list of answers the count, the length of one answer, the total, and the writing style.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; after 'enhance 20,001 characters' POST chapters/ch1/enhance-text "{'content': 'x' * 20001, 'enhancement_type': 'clarity'}"; after 'clean up 20,001 dictated characters' POST chapters/ch1/enhance-transcription "{'content': 'x' * 20001}"; after 'draft: one answer of 10,001' POST chapters/ch1/generate-draft "{'question_responses': pairs(1, 10001)}"; after 'draft: writing style of 101' POST chapters/ch1/generate-draft "{'question_responses': pairs(1), 'writing_style': 's' * 101}"; after 'contents: 101 answers' POST generate-toc "{'question_responses': pairs(101)}"; after 'save: 11 answers of 10,000 (total)' PUT question-responses "{'responses': pairs(11, 10000)}"
```

```output
enhance 20,001 characters                    HTTP 422 | provider received: nothing                | charged today: 0
clean up 20,001 dictated characters          HTTP 422 | provider received: nothing                | charged today: 0
draft: one answer of 10,001                  HTTP 422 | provider received: nothing                | charged today: 0
draft: writing style of 101                  HTTP 422 | provider received: nothing                | charged today: 0
contents: 101 answers                        HTTP 422 | provider received: nothing                | charged today: 0
save: 11 answers of 10,000 (total)           HTTP 422 | provider received: nothing                | charged today: 0
```

A request exactly at the caps still works: the provider receives it and the account is charged one generation for each.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; after 'transform exactly 20,000 characters' POST chapters/ch1/transform-style "{'content': 'x' * 20000, 'target_style': 'professional'}"; after 'draft: 100 answers, 100,000 in total' POST chapters/ch1/generate-draft "{'question_responses': pairs(100, 973)}"
```

```output
transform exactly 20,000 characters          HTTP 200 | provider received: 20766                  | charged today: 1
draft: 100 answers, 100,000 in total         HTTP 200 | provider received: 104271                 | charged today: 2
```

Answers are capped where they are saved too, because a saved answer comes back later as model input. The contents wizard refuses 101 answers and keeps nothing; one answer of exactly 10,000 characters is saved.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; saved() { curl -s -b "$(cat $D/cookie-aa_demo_800)" localhost:8100/api/v1/books/$(cat $D/book-8100)/question-responses | python3 -c 'import sys,json; r=json.load(sys.stdin)["responses"]; print("  saved answers:", len(r), "of", [len(p["answer"]) for p in r], "characters")'; }; after 'save 101 answers' PUT question-responses "{'responses': pairs(101)}"; saved; after 'save one answer of 10,000' PUT question-responses "{'responses': pairs(1, 10000)}"; saved
```

```output
save 101 answers                             HTTP 422 | provider received: nothing                | charged today: 2
  saved answers: 0 of [] characters
save one answer of 10,000                    HTTP 200 | provider received: nothing                | charged today: 2
  saved answers: 1 of [10000] characters
```

A request body is not the only road to the model. The book stores text that goes into prompts, and some of it was stored without a limit. Here the chapter is given a 5,000-character title and a 300,000-character description directly in the database, as an older save could have left them. On main a one-line draft request then carries all of it to the provider. On this branch the prompt uses the first 500 characters of the title and the first 2,000 of the description.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; for db in aa_demo_800_before aa_demo_800; do mongosh --quiet mongodb://127.0.0.1:27017/$db --eval 'db.books.updateMany({}, {$set: {"table_of_contents.chapters.0.title": "t".repeat(5000), "table_of_contents.chapters.0.description": "d".repeat(300000)}}).modifiedCount' | sed "s/^/$db chapters changed: /"; done; before 'main: draft from one short answer' POST chapters/ch1/generate-draft "{'question_responses': pairs(1)}"; after 'branch: draft from one short answer' POST chapters/ch1/generate-draft "{'question_responses': pairs(1)}"
```

```output
aa_demo_800_before chapters changed: 1
aa_demo_800 chapters changed: 1
main: draft from one short answer            HTTP 200 | provider received: 306119                 | charged today: 3
branch: draft from one short answer          HTTP 200 | provider received: 3619                   | charged today: 3
```

Answers saved before the caps are checked when the contents generator falls back to them. Sixty answers of 10,000 characters are written to the book directly, and a contents request with an empty body is refused instead of sending 600,000 characters.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo800/env.sh; mongosh --quiet mongodb://127.0.0.1:27017/aa_demo_800 --eval 'db.books.updateMany({}, {$set: {question_responses: {responses: Array.from({length: 60}, () => ({question: "What is this chapter about?", answer: "a".repeat(10000)}))}}}).modifiedCount' | sed 's/^/books given 60 saved answers: /'; after 'contents from the saved answers' POST generate-toc '{}'; python3 -m json.tool $D/last-body
```

```output
books given 60 saved answers: 1
contents from the saved answers              HTTP 422 | provider received: nothing                | charged today: 3
{
    "detail": "The saved answers are over the size limit. Save them again, shorter."
}
```

The same behaviour as tests: real routes and real MongoDB counters, with the provider stubbed at the wire. Each oversize case asserts the 422, that no model call was made, and that nothing was charged. One test calls the shared request method with a prompt over the 150,000-character ceiling and checks that nothing is sent.

```bash
cd /home/frankbria/projects/worktrees/issue-800-ai-input-caps/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo800 uv run pytest tests/test_api/test_ai_input_caps.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1 | sed 's/ in [0-9.]*s//'
```

```output
============================= 28 passed ==============================
```
