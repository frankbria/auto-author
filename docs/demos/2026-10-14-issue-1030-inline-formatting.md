# Issue #1030: bold and italic in the PDF, DOCX and EPUB

*2026-10-14T19:41:15Z by Showboat 0.6.1*
<!-- showboat-id: 986419ad-c55b-4c00-bd30-7cf853d84865 -->

One chapter, '<p>Some <strong>bold</strong> and <em>italic</em> text, and __init__ as typed.</p>', exported as DOCX, EPUB and PDF by the export service of each checkout, and each file read back: the DOCX paragraph's runs, the EPUB's XHTML, and the font the PDF sets each piece of text in.

main:

```bash
cd "$MAIN/backend" && PYTHONPATH=. ENVIRONMENT=test uv run python "$DEMO/readback.py" 2>&1 | grep -E "^(DOCX|EPUB|PDF)"
```

```output
DOCX text : Some **bold** and _italic_ text, and __init__ as typed.
DOCX runs : [('Some **bold** and _italic_ text, and __init__ as typed.', 'plain')]
EPUB      : <p>Some **bold** and _italic_ text, and __init__ as typed.</p>
PDF runs  : [('Some **bold** and _italic_ text, and __init__ as typed.', 'Helvetica')]
```

this branch:

```bash
cd backend && PYTHONPATH=. ENVIRONMENT=test uv run python "$DEMO/readback.py" 2>&1 | grep -E "^(DOCX|EPUB|PDF)"
```

```output
DOCX text : Some bold and italic text, and __init__ as typed.
DOCX runs : [('Some ', 'plain'), ('bold', 'bold'), (' and ', 'plain'), ('italic', 'italic'), (' text, and __init__ as typed.', 'plain')]
EPUB      : <p>Some <strong>bold</strong> and <em>italic</em> text, and __init__ as typed.</p>
PDF runs  : [('Some ', 'Helvetica'), ('bold', 'Helvetica-Bold'), (' and ', 'Helvetica'), ('italic', 'Helvetica-Oblique'), (' text, and __init__ as typed.', 'Helvetica')]
```

Mutation check (scratch script, each reverted and asserted clean), each caught by name: bold back to '**'; marks typed into a chapter kept (caught only after a test was added for it: it survived the first run); the PDF dropping the formatting; DOCX runs plain; a DOCX heading plain; unbalanced marks kept.
