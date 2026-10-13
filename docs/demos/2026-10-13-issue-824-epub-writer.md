# Issue #824: EPUB export is written with the standard library, not an AGPL one

*2026-10-13T16:58:52Z by Showboat 0.6.1*
<!-- showboat-id: 0802a901-0ed8-4a9b-b8d6-5259c138b34d -->

Three acceptance criteria: a standard-library `zipfile` writer for EPUB 3 (the media type first and not compressed, `container.xml`, the package document, the contents page, the older `toc.ncx`); the EPUB tests that were there pass and epubcheck reports no errors; a licence scan over what `uv export --no-dev` lists shows nothing under the GPL or the AGPL.

Two helpers are used below. `make_epub.py` exports one book with the export service of the checkout it is run from: a chapter with text, a chapter that only heads its subchapters, subchapters two deep, and a title that needs escaping. `epub_text.py` prints what a reader gets from an EPUB (metadata, reading order, both tables of contents, the text of each document), whichever library wrote it.

## Before: main

`ebooklib` is among the packages the image installs, and it says it is under the AGPL. The licence scan this branch adds, run against main, fails and names it.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main824/backend && uv export --frozen --no-dev --no-emit-project --no-hashes 2>/dev/null | grep -i '^ebooklib'
```

```output
ebooklib==0.20
```

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main824/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo824 uv run pytest -p no:cacheprovider --no-cov tests/test_runtime_licenses.py -q 2>&1 | grep -E '^E   Assert|passed|failed' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
E   AssertionError: {'ebooklib': 'GNU Affero General Public License | License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)'}
1 failed, 1 passed
```

## After: this branch

### No GPL or AGPL among the runtime packages

`ebooklib` is in neither the manifest nor the lock, and the scan passes over the same list, which is what the image installs.

```bash
cd /home/frankbria/projects/worktrees/issue-824-epub-writer/backend && grep -ci ebooklib pyproject.toml uv.lock; uv export --frozen --no-dev --no-emit-project --no-hashes 2>/dev/null | grep -c '^[a-z0-9]' | sed 's/$/ runtime packages/'
```

```output
pyproject.toml:0
uv.lock:0
47 runtime packages
```

```bash
cd /home/frankbria/projects/worktrees/issue-824-epub-writer/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo824 uv run pytest -p no:cacheprovider --no-cov tests/test_runtime_licenses.py -v 2>&1 | grep -E 'PASSED|FAILED|passed|failed' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
tests/test_runtime_licenses.py::test_the_pattern_tells_the_gpl_from_the_lgpl PASSED
tests/test_runtime_licenses.py::test_no_runtime_dependency_is_under_the_gpl_or_the_agpl PASSED
2 passed
```

### The writer uses the standard library only

Everything it imports. `zipfile` writes the file; the rest is escaping and a date.

```bash
cd /home/frankbria/projects/worktrees/issue-824-epub-writer/backend && grep -E '^(import|from) ' app/services/epub_writer.py
```

```output
import io
import re
import zipfile
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from xml.sax.saxutils import escape, quoteattr
```

### The file it writes

The same book exported from main (ebooklib) and from this branch. In the new file the media type is the first entry and is stored, not compressed; the other four are there.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main824/backend && PYTHONPATH=. ENVIRONMENT=test uv run python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/make_epub.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/main.epub 2>&1 | tail -1
```

```output
wrote main.epub 4458 bytes
```

```bash
cd /home/frankbria/projects/worktrees/issue-824-epub-writer/backend && PYTHONPATH=. ENVIRONMENT=test uv run python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/make_epub.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/branch.epub 2>&1 | tail -1
```

```output
wrote branch.epub 3829 bytes
```

```bash
unzip -v /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/branch.epub | awk 'NR>3 && $8 {print $2, $8}' | column -t
```

```output
Stored  mimetype
Defl:N  META-INF/container.xml
Defl:N  EPUB/content.opf
Defl:N  EPUB/nav.xhtml
Defl:N  EPUB/toc.ncx
Defl:N  EPUB/title.xhtml
Defl:N  EPUB/chap_1.xhtml
Defl:N  EPUB/chap_3.xhtml
Defl:N  EPUB/chap_4.xhtml
Defl:N  EPUB/chap_5.xhtml
Defl:N  EPUB/chap_6.xhtml
```

### epubcheck

The format's own validator, 5.4.0, on each. No errors on either, so the new writer is as valid as the library it replaces.

```bash
java -jar /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/../epubcheck/epubcheck-5.4.0/epubcheck.jar /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/main.epub 2>&1 | grep -E 'Messages|ERROR|WARNING|FATAL'
```

```output
Messages: 0 fatals / 0 errors / 0 warnings / 0 infos
```

```bash
java -jar /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/../epubcheck/epubcheck-5.4.0/epubcheck.jar /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/branch.epub 2>&1 | grep -E 'Messages|ERROR|WARNING|FATAL'
```

```output
Messages: 0 fatals / 0 errors / 0 warnings / 0 infos
```

### Found by comparing: a character XML does not allow

`control_chars.py` exports a book with a form feed, a vertical tab and a backspace in its title, its author and a chapter, as text pasted from a PDF or from Word can carry, and tries to parse every file in the result. On main the export fails. On this branch the characters are left out and every file parses.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main824/backend && PYTHONPATH=. ENVIRONMENT=test uv run python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/control_chars.py 2>&1 | tail -6
```

```output
export raised ValueError All strings must be XML compatible: Unicode or ASCII, no NULL bytes or control characters
```

```bash
cd /home/frankbria/projects/worktrees/issue-824-epub-writer/backend && PYTHONPATH=. ENVIRONMENT=test uv run python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/control_chars.py 2>&1 | tail -6
```

```output
ok        META-INF/container.xml
ok        EPUB/content.opf
ok        EPUB/nav.xhtml
ok        EPUB/toc.ncx
ok        EPUB/title.xhtml
ok        EPUB/chap_1.xhtml
```

### Found in review: the older contents file says where each entry comes in the order

`toc.ncx` requires it of every entry, and `ebooklib` did not write it. Entries that open the same document share a number, which epubcheck insists on: the run above is of this file.

```bash
python3 /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/play_order.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/branch.epub
```

```output
1 Title Page -> title.xhtml
2 Chapter 1: Introduction -> chap_1.xhtml
3 Chapter 2: Part <Two> -> chap_3.xhtml
3 2.1 First section -> chap_3.xhtml
4 2.1.1 A detail -> chap_4.xhtml
5 2.2 Second section -> chap_5.xhtml
6 Chapter 3: Conclusion -> chap_6.xhtml
```

```bash
python3 /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/play_order.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/main.epub
```

```output
(none) Title Page -> title.xhtml
(none) Chapter 1: Introduction -> chap_1.xhtml
(none) Chapter 2: Part <Two> -> chap_3.xhtml
(none) 2.1 First section -> chap_3.xhtml
(none) 2.1.1 A detail -> chap_4.xhtml
(none) 2.2 Second section -> chap_5.xhtml
(none) Chapter 3: Conclusion -> chap_6.xhtml
```

### A reader gets the same book

What a reading system finds in the new file, and then the same reading of main's file compared with it. The comparison prints nothing but its last line: metadata, reading order, both tables of contents and every document's text are the same.

```bash
python3 /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/epub_text.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/branch.epub | tee /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/branch.txt
```

```output
first entry: mimetype stored
identifier: book-824
title: Tom & Jerry: A <Study>
language: en
creator: A. Writer
description: About cats & mice.
subject: Non-fiction
reading order: title.xhtml, nav.xhtml, chap_1.xhtml, chap_3.xhtml, chap_4.xhtml, chap_5.xhtml, chap_6.xhtml
contents (EPUB 3):
  Title Page -> title.xhtml
  Chapter 1: Introduction -> chap_1.xhtml
  Chapter 2: Part <Two> -> chap_3.xhtml
    2.1 First section -> chap_3.xhtml
      2.1.1 A detail -> chap_4.xhtml
    2.2 Second section -> chap_5.xhtml
  Chapter 3: Conclusion -> chap_6.xhtml
contents (NCX):
  Title Page -> title.xhtml
  Chapter 1: Introduction -> chap_1.xhtml
  Chapter 2: Part <Two> -> chap_3.xhtml
    2.1 First section -> chap_3.xhtml
      2.1.1 A detail -> chap_4.xhtml
    2.2 Second section -> chap_5.xhtml
  Chapter 3: Conclusion -> chap_6.xhtml
title.xhtml: <h1> Tom & Jerry: A <Study> / <h2> With an "appendix" / <p> by A. Writer / <p> Genre: Non-fiction / <p> Target Audience: Everyone / <p> About cats & mice.
chap_1.xhtml: <h1> Chapter 1: Introduction / <p> Where it starts / <h2> Welcome / <p> Some **bold** text & an ampersand. / <p> * One / <p> * Two
chap_3.xhtml: <h1> Chapter 2: Part <Two> / <h2> 2.1 First section / <p> Section text.
chap_4.xhtml: <h3> 2.1.1 A detail / <p> Deeper.
chap_5.xhtml: <h2> 2.2 Second section / <p> More text.
chap_6.xhtml: <h1> Chapter 3: Conclusion / <p> The end.
```

```bash
python3 /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/epub_text.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/main.epub > /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/main.txt; diff /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/main.txt /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo824/branch.txt && echo 'no difference'
```

```output
no difference
```

### Tests

The new ones for the writer, then every test in the export service and the export endpoints that touches EPUB, which were there before and were not changed apart from the two that asked whether ebooklib was installed.

```bash
cd /home/frankbria/projects/worktrees/issue-824-epub-writer/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo824 uv run pytest -p no:cacheprovider --no-cov tests/test_services/test_epub_writer.py -v 2>&1 | grep -E 'PASSED|FAILED|passed|failed' | sed 's/^tests.test_services.test_epub_writer.py:://' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
test_the_first_entry_is_the_media_type_and_is_not_compressed PASSED
test_everything_the_package_names_is_in_the_file_and_everything_in_the_file_is_named PASSED
test_the_reading_order_is_the_documents_in_the_order_given_with_the_contents_page_after_the_first PASSED
test_the_manifest_says_which_document_is_the_contents_page PASSED
test_the_metadata_is_what_was_given PASSED
test_what_was_not_given_is_left_out_not_written_empty PASSED
test_the_contents_page_nests_as_the_book_does PASSED
test_the_older_contents_file_nests_the_same_way PASSED
test_every_file_in_it_is_well_formed_whatever_the_title PASSED
test_characters_xml_does_not_allow_are_left_out_and_the_rest_is_kept PASSED
test_the_documents_are_stored_as_they_were_given PASSED
test_ebooklib_is_gone_from_the_code_the_manifest_and_the_lock PASSED
test_the_export_service_writes_a_book_through_it PASSED
13 passed
```

```bash
cd /home/frankbria/projects/worktrees/issue-824-epub-writer/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo824 uv run pytest -p no:cacheprovider --no-cov tests/test_services tests/test_api/test_export_endpoints.py -q -k 'epub or Epub or EPUB' 2>&1 | tail -1 | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
21 passed, 438 deselected
```
