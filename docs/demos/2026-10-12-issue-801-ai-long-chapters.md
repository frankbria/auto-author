# Transform, enhance and cleanup work on a chapter of ordinary length (#801)

*2026-10-12T07:36:04Z by Showboat 0.6.1*
<!-- showboat-id: 311c7b3a-72a0-44f2-a61b-9dd02db8f46e -->

The three rewrite flows ran on the default model class (gpt-4: an 8,192-token context shared by the prompt and the answer) with a fixed budget of 4,000 answer tokens, so a chapter over about 3,000 words could not come back whole. This demo sends the same chapters to two real backends, one running main and one running this branch. Both talk to a local stand-in provider that records the model asked for, the answer budget and the size of the prompt. A third backend runs this branch against a real model. Authentication is on, so the quota counts as it does for a real account.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo801/env.sh; echo "main:   $(git -C $MAIN log --oneline -1 | cut -c1-7)  $(curl -s localhost:8101/api/v1/health | cut -c1-60)"; echo "branch: $(git -C $WT rev-parse --abbrev-ref HEAD)  $(curl -s localhost:8100/api/v1/health | cut -c1-60)"
```

```output
main:   a58876a  {"status":"healthy","checks":{"mongodb":"ok","config":"ok"}}
branch: feature/issue-801-ai-long-chapters  {"status":"healthy","checks":{"mongodb":"ok","config":"ok"}}
```

The sample chapters are real English prose (this repository documentation with the markup removed), stored the way the editor stores a chapter: HTML paragraphs. They are words only, so they are lighter in tokens than prose with its punctuation; the next step measures real prose.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo801/env.sh; for n in 1000 2900 5000; do python3 -c "import re; h=open('$D/chapter-$n.html').read(); print('$n-word chapter:', len(re.sub('<[^>]+>', ' ', h).split()), 'words,', len(h), 'characters')"; done
```

```output
1000-word chapter: 1000 words, 6772 characters
2900-word chapter: 2900 words, 19539 characters
5000-word chapter: 5000 words, 31844 characters
```

How many tokens is a chapter? Measured with the gpt-4o tokenizer on English prose with its punctuation kept (three license texts, the longest prose on this machine, and this repository documentation as an example of technical text). The limits in this change come from these numbers: about 4.9 characters a token for prose and 4.4 for technical text, so 5,000 words of prose is about 31,000 characters and 6,200 tokens.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/m801 && uvx --quiet --with tiktoken python measure2.py /usr/share/common-licenses/GPL-3 /usr/share/common-licenses/LGPL-2.1 /usr/share/common-licenses/Apache-2.0 /home/frankbria/projects/auto-author/docs 2>&1 | tail -4
```

```output
GPL-3: 5000 words, 30769 characters, 6175 tokens, 4.98 characters per token, 1.24 tokens per word, 6.15 characters per word
LGPL-2.1: 4350 words, 26034 characters, 5323 tokens, 4.89 characters per token, 1.22 tokens per word, 5.98 characters per word
Apache-2.0: 1581 words, 10330 characters, 2070 tokens, 4.99 characters per token, 1.31 tokens per word, 6.53 characters per word
project docs, punctuation kept: 5000 words, 35970 characters, 8172 tokens, 4.40 characters per token, 1.63 tokens per word, 7.19 characters per word
```

Before. Main sends a 2,900-word chapter to gpt-4 with a 4,000-token budget, which just fits an 8,192-token context. A 5,000-word chapter is refused by the 20,000-character cap that #800 put where the old budget ended; before that cap it went to gpt-4 and failed there.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo801/env.sh; before 'transform 2,900 words' POST chapters/ch1/transform-style "{'content': chapter(2900), 'target_style': 'professional'}"; before 'transform 5,000 words' POST chapters/ch1/transform-style "{'content': chapter(5000), 'target_style': 'professional'}"
```

```output
transform 2,900 words                    HTTP 200 | provider received: gpt-4, max_tokens 4000, 20305 chars                  | charged today: 1
transform 5,000 words                    HTTP 422 | provider received: nothing                                              | charged today: 1
```

After. All three flows send the chapter to the long-output model (gpt-4o by default: a 128,000-token context) with a budget that follows the length of the text: a third of its characters, never less than the old 4,000, never more than the long-output cap of 8,000. The 5,000-word chapter is accepted and answered.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo801/env.sh; after 'transform 1,000 words' POST chapters/ch1/transform-style "{'content': chapter(1000), 'target_style': 'professional'}"; after 'transform 2,900 words' POST chapters/ch1/transform-style "{'content': chapter(2900), 'target_style': 'professional'}"; after 'transform 5,000 words' POST chapters/ch1/transform-style "{'content': chapter(5000), 'target_style': 'professional'}"; after 'enhance 5,000 words' POST chapters/ch1/enhance-text "{'content': chapter(5000), 'enhancement_type': 'clarity'}"; after 'clean up 5,000 dictated words' POST chapters/ch1/enhance-transcription "{'content': chapter(5000)}"; python3 -c "import json; print('  model the response names:', json.load(open('$D/last-body'))['metadata']['model_used'])"
```

```output
transform 1,000 words                    HTTP 200 | provider received: gpt-4o, max_tokens 4000, 7538 chars                  | charged today: 1
transform 2,900 words                    HTTP 200 | provider received: gpt-4o, max_tokens 6513, 20305 chars                 | charged today: 2
transform 5,000 words                    HTTP 200 | provider received: gpt-4o, max_tokens 8000, 32610 chars                 | charged today: 3
enhance 5,000 words                      HTTP 200 | provider received: gpt-4o, max_tokens 8000, 32597 chars                 | charged today: 4
clean up 5,000 dictated words            HTTP 200 | provider received: gpt-4o, max_tokens 8000, 32848 chars                 | charged today: 5
  model the response names: gpt-4o
```

When the model cannot finish a rewrite inside its budget, the answer is a 413 with a fixed code. It used to be a 503, which tells a client to wait and try again, and the retry would be cut off at the same place. The provider was called, so the generation stays charged.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo801/env.sh; echo cut > $D/provider-mode; after 'transform, answer cut off' POST chapters/ch1/transform-style "{'content': chapter(1000), 'target_style': 'professional'}"; python3 -m json.tool $D/last-body; echo whole > $D/provider-mode
```

```output
transform, answer cut off                HTTP 413 | provider received: gpt-4o, max_tokens 4000, 7538 chars                  | charged today: 6
{
    "detail": {
        "message": "This chapter is too long to transform in one pass. Try transforming a shorter section.",
        "error_code": "REWRITE_TRUNCATED",
        "retryable": false
    }
}
```

The cap on the text moved with the budget, from 20,000 to 32,000 characters: at 4.9 characters a token that is about 6,500 tokens, which leaves a rewrite a fifth more room than its source inside the 8,000-token budget. One character over is still refused before anything is sent or charged.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo801/env.sh; after 'transform 32,000 characters' POST chapters/ch1/transform-style "{'content': 'x' * 32000, 'target_style': 'professional'}"; after 'transform 32,001 characters' POST chapters/ch1/transform-style "{'content': 'x' * 32001, 'target_style': 'professional'}"; python3 -c "import json; print(' ', json.load(open('$D/last-body'))['error_summary'])"
```

```output
transform 32,000 characters              HTTP 200 | provider received: gpt-4o, max_tokens 8000, 32766 chars                 | charged today: 7
transform 32,001 characters              HTTP 422 | provider received: nothing                                              | charged today: 7
  body -> content: String should have at most 32000 characters
```

This branch also fixes a regression that #800 put on main an hour earlier, found by the review bot after that merge. A chapter can be stored with a null description, and #800 cut the description to length without checking for one, so a draft for such a chapter failed. Main fails; this branch drafts.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo801/env.sh; for db in aa_demo_801_before aa_demo_801; do mongosh --quiet mongodb://127.0.0.1:27017/$db --eval 'db.books.updateMany({}, {$set: {"table_of_contents.chapters.0.description": null}}).modifiedCount' | sed "s/^/$db chapters given a null description: /"; done; before 'main: draft' POST chapters/ch1/generate-draft "{'question_responses': pairs(1)}"; python3 -c "import json; print(' ', json.load(open('$D/last-body'))['detail'])"; after 'branch: draft' POST chapters/ch1/generate-draft "{'question_responses': pairs(1)}"
```

```output
aa_demo_801_before chapters given a null description: 1
aa_demo_801 chapters given a null description: 1
main: draft                              HTTP 503 | provider received: nothing                                              | charged today: 1
  Failed to generate draft: 'NoneType' object is not subscriptable
branch: draft                            HTTP 200 | provider received: gpt-4o, max_tokens 3200, 1131 chars                  | charged today: 8
```

A real model. The third backend runs this branch against gpt-oss:120b through the local Ollama endpoint, with that model set as the long-output model. The stand-in above only shows what is sent; this shows what comes back. Each chapter is sent three times, because a real model does not answer the same way twice.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo801/env.sh; live() { send 8102 aa_demo_801_live "$1" POST chapters/ch1/transform-style "{'content': chapter($2), 'target_style': 'conversational'}" | sed 's/ | provider received.*//' | tr '\n' ' '; python3 -c "import json; d=json.load(open('$D/last-body')); m=d.get('metadata'); print('| words in:', m['original_word_count'], '| words out:', m['transformed_word_count']) if m else print('|', d['detail']['error_code'])"; }; for i in 1 2 3; do live "live $i: transform 1,000 words" 1000; done; for i in 1 2 3; do live "live $i: transform 5,000 words" 5000; done
```

```output
live 1: transform 1,000 words            HTTP 200 | words in: 989 | words out: 1079
live 2: transform 1,000 words            HTTP 200 | words in: 989 | words out: 967
live 3: transform 1,000 words            HTTP 413 | REWRITE_TRUNCATED
live 1: transform 5,000 words            HTTP 200 | words in: 4945 | words out: 1682
live 2: transform 5,000 words            HTTP 200 | words in: 4945 | words out: 1365
live 3: transform 5,000 words            HTTP 200 | words in: 4945 | words out: 1655
```

What the live runs show. The 1,000-word chapter came back at about its own length twice. The third time the model stopped at the 4,000-token budget and the route answered the 413: it is a reasoning model, and its hidden reasoning counts against the budget (#925 covers budgets for such models). The 5,000-word chapter was accepted and answered all three times, which main cannot do, but each answer has about a third of the words of the chapter, and the model reported a normal finish, so the backend passed it on as a success. A shortened chapter offered as a finished rewrite is a different defect from the one in this issue; it is filed as #983 with these numbers.

The same behaviour as tests: real routes and real MongoDB counters, with the provider stubbed at the wire.

```bash
cd /home/frankbria/projects/worktrees/issue-801-ai-long-chapters/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo801 uv run pytest tests/test_api/test_ai_rewrite_long_chapters.py tests/test_api/test_ai_input_caps.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1 | sed 's/ in [0-9.]*s//'
```

```output
============================== 42 passed ==============================
```
