# Exports number chapters by their place in the outline (#805)

*2026-10-12T08:56:18Z by Showboat 0.6.1*
<!-- showboat-id: 93bae1b0-1d3c-4018-9537-437935fb2e6e -->

Every export format numbered the flattened list of chapters, so a subchapter came out as a chapter. This demo stores one book, with two chapters and two subchapters under the first, behind two real backends: one running main and one running this branch. Each exports it as PDF, Word, EPUB and Markdown, and each file is read back with a library that had no part in writing it (pypdf, python-docx, the EPUB zip itself).

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo805/env.sh; echo "main:   $(git -C $MAIN log --oneline -1 | cut -c1-7)  $(curl -s localhost:8101/api/v1/health | cut -c1-60)"; echo "branch: $(git -C $WT rev-parse --abbrev-ref HEAD)  $(curl -s localhost:8100/api/v1/health | cut -c1-60)"; mongosh --quiet mongodb://127.0.0.1:27017/aa_demo_805 --eval 'const show = (cs, d) => cs.forEach(c => { print("  ".repeat(d) + c.title); show(c.subchapters, d + 1) }); show(db.books.findOne().table_of_contents.chapters, 1)'
```

```output
main:   7abdefb  {"status":"healthy","checks":{"mongodb":"ok","config":"ok"}}
branch: feature/issue-805-export-numbering  {"status":"healthy","checks":{"mongodb":"ok","config":"ok"}}
  Planning
    Outlines
    Research
  Writing
```

Before. Main exports the four entries as Chapter 1 to Chapter 4 in every format, in the body and in the table of contents. In Word all four are top-level headings, and the EPUB navigation is one flat list.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo805/env.sh; fetch 8101 before; for f in before.pdf before.docx before.epub before.md; do echo "$f"; show $f; done
```

```output
before.pdf: HTTP 200, 4503 bytes
before.docx: HTTP 200, 36875 bytes
before.epub: HTTP 200, 3753 bytes
before.md: HTTP 200, 249 bytes
before.pdf
  page 2: 1. Planning
  page 2: 2. Outlines
  page 2: 3. Research
  page 2: 4. Writing
  page 3: Chapter 1: Planning
  page 4: Chapter 2: Outlines
  page 5: Chapter 3: Research
  page 6: Chapter 4: Writing
before.docx
  ---------- page break
  Heading 1  Table of Contents
  Normal     1. Planning
  Normal     2. Outlines
  Normal     3. Research
  Normal     4. Writing
  ---------- page break
  Heading 1  Chapter 1: Planning
  ---------- page break
  Heading 1  Chapter 2: Outlines
  ---------- page break
  Heading 1  Chapter 3: Research
  ---------- page break
  Heading 1  Chapter 4: Writing
before.epub
  navigation:
    Title Page
    Planning
    Outlines
    Research
    Writing
  chapter files:
    chap_1.xhtml: <h1> Chapter 1: Planning
    chap_2.xhtml: <h1> Chapter 2: Outlines
    chap_3.xhtml: <h1> Chapter 3: Research
    chap_4.xhtml: <h1> Chapter 4: Writing
before.md
  # Writing a First Book
  ## Chapter 1: Planning
  ### Chapter 2: Outlines
  ### Chapter 3: Research
  ## Chapter 4: Writing
```

After. The same book from this branch: Chapter 1, 1.1, 1.2, Chapter 2 in every format and in each table of contents. In Word the subchapters are second-level headings, and in the EPUB navigation they sit under their chapter.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo805/env.sh; fetch 8100 after; for f in after.pdf after.docx after.epub after.md; do echo "$f"; show $f; done
```

```output
after.pdf: HTTP 200, 4487 bytes
after.docx: HTTP 200, 36879 bytes
after.epub: HTTP 200, 3807 bytes
after.md: HTTP 200, 235 bytes
after.pdf
  page 2: 1. Planning
  page 2: 1.1 Outlines
  page 2: 1.2 Research
  page 2: 2. Writing
  page 3: Chapter 1: Planning
  page 4: 1.1 Outlines
  page 5: 1.2 Research
  page 6: Chapter 2: Writing
after.docx
  ---------- page break
  Heading 1  Table of Contents
  Normal     1. Planning
  Normal     1.1 Outlines
  Normal     1.2 Research
  Normal     2. Writing
  ---------- page break
  Heading 1  Chapter 1: Planning
  ---------- page break
  Heading 2  1.1 Outlines
  ---------- page break
  Heading 2  1.2 Research
  ---------- page break
  Heading 1  Chapter 2: Writing
after.epub
  navigation:
    Title Page
    Chapter 1: Planning
        1.1 Outlines
        1.2 Research
    Chapter 2: Writing
  chapter files:
    chap_1.xhtml: <h1> Chapter 1: Planning
    chap_2.xhtml: <h2> 1.1 Outlines
    chap_3.xhtml: <h2> 1.2 Research
    chap_4.xhtml: <h1> Chapter 2: Writing
after.md
  # Writing a First Book
  ## Chapter 1: Planning
  ### 1.1 Outlines
  ### 1.2 Research
  ## Chapter 2: Writing
```

Numbers follow what is exported. Empty chapters are left out by default. In this second book Planning has no text of its own and only groups three subchapters, one of them empty; Notes is empty with nothing under it. Planning keeps its heading because its subchapters need it, with no placeholder line and no page of its own; the empty Research and Notes are left out, and nothing is skipped in the numbering. With empty chapters asked for, all six are numbered, and the ones with nothing under them say that they have no content yet.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo805/env.sh; new_book 8100 aa_demo_805 "[{id: 'c1', title: 'Planning', description: '', content: '', order: 1, level: 1, parent_id: null, status: 'completed', word_count: 3, subchapters: [{id: 'c1a', title: 'Outlines', description: '', content: '<p>Outline it.</p>', order: 1, level: 1, parent_id: null, status: 'completed', word_count: 3, subchapters: []}, {id: 'c1b', title: 'Research', description: '', content: '', order: 1, level: 1, parent_id: null, status: 'completed', word_count: 3, subchapters: []}, {id: 'c1c', title: 'Sources', description: '', content: '<p>Keep a list.</p>', order: 1, level: 1, parent_id: null, status: 'completed', word_count: 3, subchapters: []}]}, {id: 'c2', title: 'Notes', description: '', content: '', order: 1, level: 1, parent_id: null, status: 'completed', word_count: 3, subchapters: []}, {id: 'c3', title: 'Writing', description: '', content: '<p>Write every day.</p>', order: 1, level: 1, parent_id: null, status: 'completed', word_count: 3, subchapters: []}]" > $D/book-8100; mongosh --quiet mongodb://127.0.0.1:27017/aa_demo_805 --eval 'const show = (cs, d) => cs.forEach(c => { print("  ".repeat(d) + c.title + (c.content ? "" : "  (no text)")); show(c.subchapters, d + 1) }); show(db.books.findOne({_id: ObjectId("'$(cat $D/book-8100)'")}).table_of_contents.chapters, 1)'; curl -s -o $D/grouping.docx "localhost:8100/api/v1/books/$(cat $D/book-8100)/export/docx"; echo 'default export:'; show grouping.docx; curl -s -o $D/grouping-all.docx "localhost:8100/api/v1/books/$(cat $D/book-8100)/export/docx?include_empty_chapters=true"; echo 'with empty chapters:'; show grouping-all.docx
```

```output
  Planning  (no text)
    Outlines
    Research  (no text)
    Sources
  Notes  (no text)
  Writing
default export:
  ---------- page break
  Heading 1  Table of Contents
  Normal     1. Planning
  Normal     1.1 Outlines
  Normal     1.2 Sources
  Normal     2. Writing
  ---------- page break
  Heading 1  Chapter 1: Planning
  Heading 2  1.1 Outlines
  ---------- page break
  Heading 2  1.2 Sources
  ---------- page break
  Heading 1  Chapter 2: Writing
with empty chapters:
  ---------- page break
  Heading 1  Table of Contents
  Normal     1. Planning
  Normal     1.1 Outlines
  Normal     1.2 Research
  Normal     1.3 Sources
  Normal     2. Notes
  Normal     3. Writing
  ---------- page break
  Heading 1  Chapter 1: Planning
  Heading 2  1.1 Outlines
  ---------- page break
  Heading 2  1.2 Research
  Normal     (No content yet)
  ---------- page break
  Heading 2  1.3 Sources
  ---------- page break
  Heading 1  Chapter 2: Notes
  Normal     (No content yet)
  ---------- page break
  Heading 1  Chapter 3: Writing
```

The same behaviour as tests, which build each format through the export service and read the files back.

```bash
cd /home/frankbria/projects/worktrees/issue-805-export-numbering/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo805 uv run pytest tests/test_services/test_export_numbering.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1 | sed 's/ in [0-9.]*s//'
```

```output
============================== 12 passed ==============================
```
