# Issue #835: the questions asked about a chapter are for a non-fiction book

*2026-10-13T23:50:30Z by Showboat 0.6.1*
<!-- showboat-id: 66fd8aee-b193-44e2-ae13-5e7a0e2cad71 -->

Three acceptance criteria: the template questions are for non-fiction, and none contains protagonist, characters or plot; a generated question with a null `help_text` is kept; the fallback `order` values are unique and increasing.

`test_demo_835.py` is copied into `backend/tests/` of the checkout it is run in. It asks for a chapter's questions through the API, three times, against a real database. Only the model is stood in for, at the one call the service makes to it: it returns nothing, then three questions whose `help_text` is null, then one question when five were asked for. The chapter is "Why Habits Stick", in a self-help book.

## Before: main

With nothing from the model, the writer of a self-help book is asked about main characters, the overall story and sensory details, and the ten questions are five questions twice. The three questions the model did write are thrown away, for a null field, and three templates take their place. And the numbering starts again at 1 where the templates begin.

```bash
cp /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo835/test_demo_835.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main835/backend/tests/ && cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main835/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo835 uv run pytest -p no:cacheprovider --no-cov tests/test_demo_835.py -s -q 2>&1 | grep -E '^  |^=+ [0-9]+ (passed|failed)|^[0-9]+ (passed|failed)' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'; rm -f /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main835/backend/tests/test_demo_835.py
```

```output
 The model returns nothing usable; ten questions are asked for:
  1. [character] Who are the main characters in this chapter and what are their key traits?
  2. [plot] How does this chapter advance the overall story?
  3. [setting] What sensory details (sights, sounds, smells) bring the setting to life?
  4. [theme] What moral dilemmas or philosophical questions arise in this chapter?
  5. [research] What expert knowledge would enhance the realism of this chapter?
  6. [character] Who are the main characters in this chapter and what are their key traits?
  7. [plot] How does this chapter advance the overall story?
  8. [setting] What sensory details (sights, sounds, smells) bring the setting to life?
  9. [theme] What moral dilemmas or philosophical questions arise in this chapter?
 10. [research] What expert knowledge would enhance the realism of this chapter?
 different questions among the ten: 5
 help shown with the first: Consider physical traits, psychological aspects, backstory, and character development.
 The model returns three questions, each with a null help_text:
  1. template: Who are the main characters in this chapter and what are their key traits?
  2. template: How does this chapter advance the overall story?
  3. template: What sensory details (sights, sounds, smells) bring the setting to life?
 The model returns one question; five are asked for:
 numbered: 1 (the model), 1 (template), 2 (template), 3 (template), 4 (template)
1 passed
```

## After: this branch

Ten different questions about the chapter's reader, point, context, message and evidence, one of them naming the chapter. The model's three questions are the ones asked. One to five, once each.

```bash
cp /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo835/test_demo_835.py /home/frankbria/projects/worktrees/issue-835-nonfiction-question-fallbacks/backend/tests/ && cd /home/frankbria/projects/worktrees/issue-835-nonfiction-question-fallbacks/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo835 uv run pytest -p no:cacheprovider --no-cov tests/test_demo_835.py -s -q 2>&1 | grep -E '^  |^=+ [0-9]+ (passed|failed)|^[0-9]+ (passed|failed)' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'; rm -f /home/frankbria/projects/worktrees/issue-835-nonfiction-question-fallbacks/backend/tests/test_demo_835.py
```

```output
 The model returns nothing usable; ten questions are asked for:
  1. [character] Who is this chapter written for, and what do they already know about its subject?
  2. [plot] What is the main point of Why Habits Stick, in one or two sentences?
  3. [setting] In what situation would a reader use what this chapter teaches?
  4. [theme] What is the one idea a reader should still remember from this chapter a month later?
  5. [research] What evidence supports the main claim of this chapter?
  6. [character] Whose experience, yours or someone else's, best shows why this chapter matters?
  7. [plot] What are the steps a reader has to follow to get from the start of this chapter to its conclusion?
  8. [setting] What background does a reader need before this chapter makes sense?
  9. [theme] What common belief does this chapter challenge?
 10. [research] Which facts, figures or quotations in this chapter need a source?
 different questions among the ten: 10
 help shown with the first: Think of one real reader, and of the people whose experience makes the point.
 The model returns three questions, each with a null help_text:
  1. the model: What does the reader gain from part 1 of this chapter?
  2. the model: What does the reader gain from part 2 of this chapter?
  3. the model: What does the reader gain from part 3 of this chapter?
 The model returns one question; five are asked for:
 numbered: 1 (the model), 2 (template), 3 (template), 4 (template), 5 (template)
1 passed
```

## Every template, help text, example and hint, searched

The fiction words the issue names, and three more, in every string the fallback can show a writer or send to the model.

```bash
cd /home/frankbria/projects/worktrees/issue-835-nonfiction-question-fallbacks/backend && PYTHONPATH=. ENVIRONMENT=test uv run python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo835/words.py 2>&1 | tail -5
```

```output
25 template questions, 0 with one of those words
 5 help texts, 0 with one of those words
 5 examples, 0 with one of those words
 5 focus hints, 0 with one of those words
types with templates, help and a hint: 5 of 5
```

## Tests

The new tests, then the two suites that were already there for generating and regenerating questions, two of whose tests held the old wording.

```bash
cd /home/frankbria/projects/worktrees/issue-835-nonfiction-question-fallbacks/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo835 uv run pytest -p no:cacheprovider --no-cov tests/test_services/test_question_fallbacks_nonfiction.py -v 2>&1 | grep -E 'PASSED|FAILED|passed|failed' | sed 's/^tests.test_services.test_question_fallbacks_nonfiction.py:://' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
TestTheTemplateQuestionsAreForNonFiction::test_none_of_them_speaks_of_a_protagonist_characters_or_a_plot PASSED
TestTheTemplateQuestionsAreForNonFiction::test_each_type_still_has_its_own_questions PASSED
TestTheTemplateQuestionsAreForNonFiction::test_one_of_them_names_the_chapter PASSED
TestTheTemplateQuestionsAreForNonFiction::test_the_patterns_test_itself PASSED
TestTheFocusHintsAreForNonFiction::test_no_focus_hint_asks_the_model_for_fiction PASSED
TestTheFocusHintsAreForNonFiction::test_the_prompt_says_the_book_is_non_fiction PASSED
TestAGeneratedQuestionWithoutHelpTextIsKept::test_it_is_kept_and_not_replaced_by_a_template[missing0] PASSED
TestAGeneratedQuestionWithoutHelpTextIsKept::test_it_is_kept_and_not_replaced_by_a_template[missing1] PASSED
TestAGeneratedQuestionWithoutHelpTextIsKept::test_it_is_kept_and_not_replaced_by_a_template[missing2] PASSED
TestAGeneratedQuestionWithoutHelpTextIsKept::test_help_text_that_is_there_is_still_used PASSED
TestQuestionsAreNumberedOnceEach::test_templates_alone_are_numbered_from_one PASSED
TestQuestionsAreNumberedOnceEach::test_templates_added_after_generated_questions_carry_on_the_numbering PASSED
TestQuestionsAreNumberedOnceEach::test_a_generated_question_that_is_dropped_leaves_no_gap PASSED
13 passed
```

```bash
cd /home/frankbria/projects/worktrees/issue-835-nonfiction-question-fallbacks/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo835 uv run pytest -p no:cacheprovider --no-cov tests/test_services/test_question_generation_service.py tests/test_api/test_question_regeneration.py -q 2>&1 | tail -1 | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
58 passed
```

## Added in review: a focus that names a type twice

The review pointed out that the API takes the focus as a list and does not remove duplicates, so a focus of plot and plot gave both slots the same plot question. Each type now counts the templates it has used. The file has 15 tests where the run above shows 13; these are the two that were added, and then all of it.

```bash
cd /home/frankbria/projects/worktrees/issue-835-nonfiction-question-fallbacks/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo835 uv run pytest -p no:cacheprovider --no-cov tests/test_services/test_question_fallbacks_nonfiction.py -v -k named_twice 2>&1 | grep -E 'PASSED|FAILED' | sed -e 's/^tests.test_services.test_question_fallbacks_nonfiction.py:://' -e 's/ *\[ *[0-9]*%\]//'
```

```output
TestTheTemplateQuestionsAreForNonFiction::test_a_type_named_twice_in_the_focus_does_not_get_the_same_question_twice[focus0] PASSED
TestTheTemplateQuestionsAreForNonFiction::test_a_type_named_twice_in_the_focus_does_not_get_the_same_question_twice[focus1] PASSED
```

```bash
cd /home/frankbria/projects/worktrees/issue-835-nonfiction-question-fallbacks/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo835 uv run pytest -p no:cacheprovider --no-cov tests/test_services/test_question_fallbacks_nonfiction.py tests/test_services/test_question_generation_service.py tests/test_api/test_question_regeneration.py -q 2>&1 | tail -1 | sed -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
73 passed
```
