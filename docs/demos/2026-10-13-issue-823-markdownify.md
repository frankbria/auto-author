# Issue #823: exports no longer depend on a GPL library

*2026-10-13T07:21:43Z by Showboat 0.6.1*
<!-- showboat-id: 41abf420-bca8-4236-8a51-fa50781c824a -->

Three acceptance criteria: html2text is replaced with markdownify (`heading_style=ATX`), built on each call; the #61 image and heading tests pass; html2text is out of `pyproject.toml` and `uv.lock`.

## Before: main

The converter on every export path, and its licence as PyPI records it.

```bash
cd /home/frankbria/projects/auto-author && git log --oneline -1 | cut -c1-50; grep -n 'html2text' backend/pyproject.toml; grep -c 'html2text' backend/app/services/export_service.py | sed 's/^/mentions in the export service: /'; python3 -c 'import json, sys, urllib.request
for name in sys.argv[1:]:
    info = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json"))["info"]
    print(f"{name:16}", info.get("license_expression") or [c.split(" :: ")[-1] for c in info["classifiers"] if c.startswith("License")])' html2text
```

```output
dfed05f fix(security): stale backend transitives a
34:    "html2text==2025.4.15",
mentions in the export service: 8
html2text        GPL-3.0-or-later
```

## After: this branch

html2text is in neither file. What replaced it, and what that brings with it, are MIT.

```bash
cd /home/frankbria/projects/worktrees/issue-823-markdownify && grep -c 'html2text' backend/pyproject.toml backend/uv.lock backend/app/services/export_service.py; grep -n 'markdownify' backend/pyproject.toml; python3 -c 'import json, sys, urllib.request
for name in sys.argv[1:]:
    info = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json"))["info"]
    print(f"{name:16}", info.get("license_expression") or [c.split(" :: ")[-1] for c in info["classifiers"] if c.startswith("License")])' markdownify beautifulsoup4 soupsieve six
```

```output
backend/pyproject.toml:0
backend/uv.lock:0
backend/app/services/export_service.py:0
38:    "markdownify==1.2.3",
markdownify      ['MIT License']
beautifulsoup4   ['MIT License']
soupsieve        MIT
six              ['MIT License']
```

## The same chapters through both converters

`corpus.py` holds nineteen samples of the HTML the editor writes: paragraphs, headings, lists, nested lists, links, images, code, tables, text that only looks like markup. For each it records what the PDF, DOCX and EPUB builders are given, and what the Markdown export contains. It is run in main`s checkout and in this branch`s, and `compare.py` sets the two side by side.

```bash
cd /home/frankbria/projects/auto-author/backend && ENVIRONMENT=test PYTHONPATH=. uv run python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/corpus.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/before.json 2>&1 | tail -1 | sed 's|/tmp/.*/||'; cd /home/frankbria/projects/worktrees/issue-823-markdownify/backend && ENVIRONMENT=test PYTHONPATH=. uv run python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/corpus.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/after.json 2>&1 | tail -1 | sed 's|/tmp/.*/||'
```

```output
19 samples written to before.json
19 samples written to after.json
```

```bash
python3 /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/compare.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/before.json /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/after.json
```

```output
paragraphs               builders: same     markdown export: same
headings                 builders: same     markdown export: same
emphasis                 builders: CHANGED  markdown export: CHANGED
bullets                  builders: same     markdown export: CHANGED
numbered                 builders: same     markdown export: CHANGED
nested list              builders: same     markdown export: CHANGED
link                     builders: same     markdown export: same
image                    builders: same     markdown export: same
blockquote               builders: same     markdown export: same
code                     builders: CHANGED  markdown export: CHANGED
rule                     builders: CHANGED  markdown export: CHANGED
underscores and stars    builders: same     markdown export: CHANGED
markup-looking text      builders: CHANGED  markdown export: CHANGED
table                    builders: CHANGED  markdown export: CHANGED
script and style         builders: same     markdown export: same
entities and unicode     builders: same     markdown export: CHANGED
long line                builders: same     markdown export: same
heading with emphasis    builders: same     markdown export: same
empty and whitespace     builders: same     markdown export: same
19 samples; builders unchanged in 14, markdown export unchanged in 9
```

The five samples where the builders are given something different, in full.

```bash
python3 /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/compare.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/before.json /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/after.json --show | grep -A2 'builders: CHANGED' | grep -v -e '^--' -e 'builders: CHANGED' | cut -c1-170
```

```output
    builders before: [('normal', 'Some **bold** , some _italic_ , and **_both_**.')]
    builders after:  [('normal', 'Some **bold**, some _italic_, and **_both_**.')]
    builders before: [('normal', 'Call `save_draft()` first.\n    \n    \n    def f(x):\n        return x * 2')]
    builders after:  [('normal', 'Call `save_draft()` first.'), ('normal', 'def f(x):\n    return x * 2')]
    builders before: [('normal', 'Above.'), ('normal', '* * *'), ('normal', 'Below.')]
    builders after:  [('normal', 'Above.'), ('normal', '---'), ('normal', 'Below.')]
    builders before: [('heading1', 'not a heading'), ('normal', '1\\. not a list'), ('normal', '\\- not a bullet'), ('normal', '<b>not bold</b> & so on')]
    builders after:  [('heading1', 'not a heading'), ('normal', '1. not a list'), ('normal', '- not a bullet'), ('normal', '<b>not bold</b> & so on')]
    builders before: [('normal', 'Name| Qty  \n---|---  \nApples| 3')]
    builders after:  [('normal', '| Name | Qty |\n| --- | --- |\n| Apples | 3 |')]
```

## The files themselves

One book, exported to all four formats by main`s export service and by this branch`s. The chapter has bold and italic text, a link, a nested list, a numbered list, inline code, a code block, a quotation, names with underscores, a line typed as `1.`, an image and a `<script>`.

```bash
cd /home/frankbria/projects/auto-author/backend && ENVIRONMENT=test PYTHONPATH=. uv run python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/exports.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/out-main 2>&1 | tail -1; cd /home/frankbria/projects/worktrees/issue-823-markdownify/backend && ENVIRONMENT=test PYTHONPATH=. uv run python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/exports.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/out-branch 2>&1 | tail -1
```

```output
wrote book.docx, book.epub, book.md, book.pdf
wrote book.docx, book.epub, book.md, book.pdf
```

The PDF, read back with a PDF library. main first, then this branch. Three lines differ: the stray spaces after bold and italic are gone, the code block no longer runs on from the sentence before it, and the line typed as `1.` has no backslash.

```bash
uvx -q --with pypdf --with python-docx python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/readback.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/out-main pdf
```

```output
--- pdf
  Getting started
  Some **bold** , some _italic_ , and a [link](https://example.com/guide).
  * First point
  * Second point
  * A detail
  1. Step one
  2. Step two
  Call `save_draft()` first. def f(x): return x * 2
  > Quoted words.
  snake_case_name, __init__ and 2 * 3.
  1\. typed by hand, not a list
  Kept.
  The end.
```

```bash
uvx -q --with pypdf --with python-docx python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/readback.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/out-branch pdf
```

```output
--- pdf
  Getting started
  Some **bold**, some _italic_, and a [link](https://example.com/guide).
  * First point
  * Second point
  * A detail
  1. Step one
  2. Step two
  Call `save_draft()` first.
  def f(x): return x * 2
  > Quoted words.
  snake_case_name, __init__ and 2 * 3.
  1. typed by hand, not a list
  Kept.
  The end.
```

```bash
diff <(uvx -q --with pypdf --with python-docx python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/readback.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/out-main pdf) <(uvx -q --with pypdf --with python-docx python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/readback.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/out-branch pdf); true
```

```output
3c3
<   Some **bold** , some _italic_ , and a [link](https://example.com/guide).
---
>   Some **bold**, some _italic_, and a [link](https://example.com/guide).
9c9,10
<   Call `save_draft()` first. def f(x): return x * 2
---
>   Call `save_draft()` first.
>   def f(x): return x * 2
12c13
<   1\. typed by hand, not a list
---
>   1. typed by hand, not a list
```

The DOCX and the EPUB differ from main`s in the same three places and nowhere else.

```bash
for f in docx epub; do echo "== $f"; diff <(uvx -q --with pypdf --with python-docx python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/readback.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/out-main $f) <(uvx -q --with pypdf --with python-docx python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/readback.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/out-branch $f); done; true
```

```output
== docx
3c3
<   Some **bold** , some _italic_ , and a [link](https://example.com/guide).
---
>   Some **bold**, some _italic_, and a [link](https://example.com/guide).
10,13c10,11
<     
<     
<     def f(x):
<         return x * 2
---
>   def f(x):
>     return x * 2
16c14
<   1\. typed by hand, not a list
---
>   1. typed by hand, not a list
== epub
3c3
<       Some **bold** , some _italic_ , and a [link](https://example.com/guide).
---
>       Some **bold**, some _italic_, and a [link](https://example.com/guide).
11c11
<           return x * 2
---
>       return x * 2
14c14
<       1\. typed by hand, not a list
---
>       1. typed by hand, not a list
```

The Markdown file from this branch. The image is there with its path, the chapter`s own heading sits below the chapter heading, the lists are tight, the code is fenced, and `__init__` is escaped so that a Markdown reader shows it as typed.

```bash
uvx -q --with pypdf --with python-docx python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/readback.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo823/out-branch md
```

```output
--- md
  #### Getting started
  Some **bold**, some _italic_, and a [link](https://example.com/guide).
  * First point
  * Second point
    * A detail
  1. Step one
  2. Step two
  Call `save_draft()` first.
  ```
  def f(x):
      return x * 2
  ```
  > Quoted words.
  snake\_case\_name, \_\_init\_\_ and 2 \* 3\.
  1\. typed by hand, not a list
  ![A chart](/uploads/owner_abc.png)
  Kept.
  The end.
```

## Tests

The #61 tests the issue names, and the ones added here for each thing markdownify had to be told.

```bash
cd /home/frankbria/projects/worktrees/issue-823-markdownify/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo823 uv run pytest tests/test_services/test_export_service.py -p no:cacheprovider --no-cov -v -k 'markdown_single_file or preserves_images or WithoutHtml2text' 2>&1 | grep -E 'PASSED|FAILED|passed|failed' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^tests.test_services.test_export_service.py:://' -e 's/^=* //' -e 's/ =*$//'
```

```output
TestExportService::test_generate_markdown_single_file PASSED
TestExportService::test_generate_markdown_preserves_images PASSED
TestHtmlBecomesMarkdownWithoutHtml2text::test_html2text_is_gone_from_the_code_the_manifest_and_the_lock PASSED
TestHtmlBecomesMarkdownWithoutHtml2text::test_headings_keep_their_level PASSED
TestHtmlBecomesMarkdownWithoutHtml2text::test_each_list_item_is_its_own_paragraph_for_the_builders PASSED
TestHtmlBecomesMarkdownWithoutHtml2text::test_a_nested_list_keeps_every_item PASSED
TestHtmlBecomesMarkdownWithoutHtml2text::test_a_script_or_a_style_block_contributes_nothing PASSED
TestHtmlBecomesMarkdownWithoutHtml2text::test_the_builders_get_the_text_as_it_was_typed PASSED
TestHtmlBecomesMarkdownWithoutHtml2text::test_the_markdown_export_escapes_text_that_only_looks_like_markup PASSED
TestHtmlBecomesMarkdownWithoutHtml2text::test_a_code_block_is_fenced_in_the_export_and_plain_for_the_builders PASSED
TestHtmlBecomesMarkdownWithoutHtml2text::test_an_image_is_in_the_export_and_not_in_the_builders_text PASSED
TestHtmlBecomesMarkdownWithoutHtml2text::test_a_non_breaking_space_is_an_ordinary_space PASSED
TestHtmlBecomesMarkdownWithoutHtml2text::test_emphasis_is_marked_as_it_always_was PASSED
TestHtmlBecomesMarkdownWithoutHtml2text::test_a_link_keeps_its_address PASSED
14 passed, 40 deselected in 0.06s
```

```bash
cd /home/frankbria/projects/worktrees/issue-823-markdownify/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo823 uv run pytest tests/test_services/test_export_service.py tests/test_api/test_export_endpoints.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1
```

```output
============================== 90 passed in 9.17s ==============================
```
