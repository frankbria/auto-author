# Issue #804: exports work for any title and are logged

*2026-10-12T04:10:38Z by Showboat 0.6.1*
<!-- showboat-id: 4beb7c1c-5437-4489-8a05-8a610fad9c12 -->

A book whose title was outside latin-1 returned 500 on every export format, after the whole file had been built, because the title went into a response header as written. And no export was ever logged: the logging call failed validation every time and the failure was swallowed. This demo runs the branch's real backend on $API with a throwaway local MongoDB database. `new_book <title>` creates a book with one short chapter and prints its id. Nothing here touches staging.

**Criterion: CJK, Cyrillic and emoji titles return 200 in all four formats.** Three books, each exported as PDF, Word, EPUB and Markdown. The header carries an ASCII fallback in `filename` and the real name in `filename*`.

```bash
for title in "書名" "Война и мир" "📚 Field Guide"; do
  book=$(new_book "$title"); echo "$title"
  for fmt in pdf docx epub markdown; do
    curl -s -o "$D/out.$fmt" -D "$D/headers" "$API/books/$book/export/$fmt"
    echo "  $fmt: $(head -1 "$D/headers" | tr -d "\r" | cut -d" " -f2), $(wc -c < "$D/out.$fmt") bytes, $(grep -i "^content-disposition" "$D/headers" | tr -d "\r" | cut -d" " -f2-)"
  done
done
```

```output
書名
  pdf: 200, 3148 bytes, attachment; filename="book.pdf"; filename*=UTF-8''%E6%9B%B8%E5%90%8D.pdf
  docx: 200, 36815 bytes, attachment; filename="book.docx"; filename*=UTF-8''%E6%9B%B8%E5%90%8D.docx
  epub: 200, 2630 bytes, attachment; filename="book.epub"; filename*=UTF-8''%E6%9B%B8%E5%90%8D.epub
  markdown: 200, 146 bytes, attachment; filename="book.md"; filename*=UTF-8''%E6%9B%B8%E5%90%8D.md
Война и мир
  pdf: 200, 3164 bytes, attachment; filename="book.pdf"; filename*=UTF-8''%D0%92%D0%BE%D0%B9%D0%BD%D0%B0%20%D0%B8%20%D0%BC%D0%B8%D1%80.pdf
  docx: 200, 36832 bytes, attachment; filename="book.docx"; filename*=UTF-8''%D0%92%D0%BE%D0%B9%D0%BD%D0%B0%20%D0%B8%20%D0%BC%D0%B8%D1%80.docx
  epub: 200, 2687 bytes, attachment; filename="book.epub"; filename*=UTF-8''%D0%92%D0%BE%D0%B9%D0%BD%D0%B0%20%D0%B8%20%D0%BC%D0%B8%D1%80.epub
  markdown: 200, 160 bytes, attachment; filename="book.md"; filename*=UTF-8''%D0%92%D0%BE%D0%B9%D0%BD%D0%B0%20%D0%B8%20%D0%BC%D0%B8%D1%80.md
📚 Field Guide
  pdf: 200, 3158 bytes, attachment; filename="Field Guide.pdf"; filename*=UTF-8''Field%20Guide.pdf
  docx: 200, 36820 bytes, attachment; filename="Field Guide.docx"; filename*=UTF-8''Field%20Guide.docx
  epub: 200, 2648 bytes, attachment; filename="Field Guide.epub"; filename*=UTF-8''Field%20Guide.epub
  markdown: 200, 156 bytes, attachment; filename="Field Guide.md"; filename*=UTF-8''Field%20Guide.md
```

**Criterion: an export inserts an access-log row.** The twelve exports above, as the access log recorded them, and how many times the backend logged a failure to record one.

```bash
mongosh --quiet "$MONGO" --eval "db.chapter_access_logs.aggregate([{\$group:{_id:\"\$access_type\", rows:{\$sum:1}, chapter_ids:{\$addToSet:\"\$chapter_id\"}}},{\$sort:{_id:1}}]).forEach(d => print(d._id + \":\", d.rows, \"rows, chapter_id\", JSON.stringify(d.chapter_ids)))"
echo "log lines saying an export could not be recorded: $(grep -c "Failed to log export access" "$D/backend.log")"
```

```output
export_docx: 3 rows, chapter_id [null]
export_epub: 3 rows, chapter_id [null]
export_markdown: 3 rows, chapter_id [null]
export_pdf: 3 rows, chapter_id [null]
log lines saying an export could not be recorded: 0
```

**Criterion: the blob revoke is deferred.** This is browser-side: the download helper revoked the blob URL in the same tick as the click. The tests that pin the new behaviour, with the backend tests for the two criteria above:

```bash
cd "$WT/frontend" && npx jest src/components/export/__tests__/exportHelpers.test.ts "src/app/dashboard/books/\[bookId\]/export" -t "revoke|keeps the blob URL" --verbose --reporters=default 2>&1 | grep -E "✓|✕" | sed "s/ ([0-9]* ms)//" | sort
cd "$WT/backend" && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-s804demo uv run pytest -p no:cacheprovider --no-cov -o addopts="" -q tests/test_api/test_export_headers.py 2>&1 | tail -1 | sed "s/ in [0-9.]*s//"
```

```output
    ✓ does not revoke the blob URL in the same tick as the click (#804)
    ✓ revokes the URL later, not in the same tick as the click
25 passed
```

Not shown: a browser saving the file (no browser was driven here). The app names a download in the page, not from this header, and that name used an ASCII-only filter too, which turned a CJK title into underscores or into no name at all. Both name builders now keep letters and digits of any script; unit tests cover them.
