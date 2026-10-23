# Export Feature Architecture

## Overview

The export feature allows users to export their books in four formats (PDF, DOCX, EPUB, Markdown) with customizable options. The system provides a modal-based workflow with real-time progress tracking and comprehensive error handling.

## Architecture Components

### 1. Type Definitions (`frontend/src/types/export.ts`)

Core TypeScript interfaces for type-safe export operations:

```typescript
export type ExportFormat = 'pdf' | 'docx' | 'epub' | 'markdown';
export type PageSize = 'letter' | 'A4';

export interface ExportOptions {
  format: ExportFormat;
  includeEmptyChapters: boolean;
  pageSize?: PageSize; // PDF only
  chapters?: string[]; // Optional: specific chapters
  templateId?: string; // PDF and DOCX
  customization?: TemplateCustomization; // with templateId
  markdownMultiFile?: boolean; // Markdown only: one file per chapter as a ZIP
}

export interface ExportProgressInfo {
  status: ExportStatus;
  progress: number; // 0-100
  estimatedTimeRemaining?: number; // seconds
  error?: ExportError;
}
```

### 2. API Client Integration (`frontend/src/lib/api/bookClient.ts`)

Export methods with proper error handling:

```typescript
// Export PDF with options
public async exportPDF(bookId: string, options?: {
  includeEmptyChapters?: boolean;
  pageSize?: 'letter' | 'A4';
  templateId?: string;
  customization?: TemplateCustomization;
}): Promise<Blob>

// Export DOCX with options
public async exportDOCX(bookId: string, options?: {
  includeEmptyChapters?: boolean;
  templateId?: string;
  customization?: TemplateCustomization;
}): Promise<Blob>

// Export EPUB and Markdown (multiFile returns a ZIP)
public async exportEPUB(bookId: string, options?: { includeEmptyChapters?: boolean }): Promise<Blob>
public async exportMarkdown(bookId: string, options?: {
  includeEmptyChapters?: boolean;
  multiFile?: boolean;
}): Promise<Blob>

// Get available formats and statistics
public async getExportFormats(bookId: string): Promise<{
  formats: ExportFormatInfo[];
  book_stats: BookExportStats;
}>
```

### 3. UI Components

#### ExportOptionsModal (`frontend/src/components/export/ExportOptionsModal.tsx`)

User-facing modal for export configuration:
- Format selection (PDF, DOCX, EPUB, Markdown)
- Page size selection (Letter/A4) for PDF exports
- Template selection for PDF and DOCX; one-file-per-chapter toggle for Markdown
- Defaults taken from the user's stored export preferences
- Toggle for including empty chapters
- Book statistics display (word count, chapters)
- Validation before export

**Props**:
```typescript
interface ExportOptionsModalProps {
  bookId: string;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onExport: (options: ExportOptions) => void;
  bookTitle?: string;
}
```

#### ExportProgressModal (`frontend/src/components/export/ExportProgressModal.tsx`)

Real-time progress tracking during export:
- Progress bar with percentage (0-100%)
- Elapsed time tracking
- Estimated time remaining
- Status messages (Pending, Processing, Completed, Failed)
- Cancel/retry buttons
- Error message display

**Props**:
```typescript
interface ExportProgressModalProps {
  isOpen: boolean;
  status: ExportStatus;
  progress?: number;
  estimatedTime?: number;
  error?: string;
  filename?: string;
  onCancel?: () => void;
  onClose: () => void;
}
```

### 4. Helper Utilities (`frontend/src/components/export/exportHelpers.ts`)

Utility functions for export operations:

```typescript
// Trigger browser download
downloadBlob(blob: Blob, filename: string): void

// Generate sanitized filename
generateFilename(bookTitle: string, format: ExportFormat): string

// Format file size for display
formatFileSize(bytes: number): string

// Validate export options
validateExportOptions(format: ExportFormat, bookTitle?: string)

// Estimate export time
estimateExportTime(wordCount: number, format: ExportFormat): number
```

## User Flow

### 1. Export Initiation
```
User clicks "Export Book" button
  ↓
ExportOptionsModal opens
  ↓
User selects:
  - Format (PDF, DOCX, EPUB or Markdown)
  - Page size (if PDF)
  - Include empty chapters toggle
  ↓
User clicks "Export"
```

### 2. Export Processing
```
ExportOptionsModal closes
  ↓
ExportProgressModal opens with status="processing"
  ↓
Progress bar updates (simulated: 0% → 90% in increments)
  ↓
API call via handleApiCall() wrapper:
  - Automatic retry on transient errors (3 attempts)
  - Exponential backoff (2s, 4s, 8s)
  - Error classification and handling
  ↓
Backend generates export file
```

### 3. Export Completion
```
Success Path:
  Progress → 100%
  ↓
  downloadBlob() triggers browser download
  ↓
  Success toast notification
  ↓
  ExportProgressModal shows completion
  ↓
  User clicks "Done"

Failure Path:
  Error classified (see error-handling.md)
  ↓
  ExportProgressModal shows error
  ↓
  Error notification with retry button
  ↓
  User can retry or close
```

## Error Handling Integration

The export feature integrates with the unified error handling framework:

### Error Classification
- **Transient Errors**: Network issues, timeouts → Automatic retry
- **Permanent Errors**: Validation, permissions → User action required
- **System Errors**: Server failures → Support reference

### Retry Logic
```typescript
const result = await handleApiCall(
  async () => {
    // BookPage picks exportPDF / exportEPUB / exportMarkdown / exportDOCX by options.format
    return await bookClient.exportPDF(bookId, options);
  },
  {
    context: `Export ${options.format.toUpperCase()}`,
    onRetry: (attempt, error) => {
      setExportProgress(0);
      toast.info(`Retrying export (attempt ${attempt})...`);
    },
    onSuccess: (attempts) => {
      if (attempts > 1) {
        showRecoveryNotification('Export completed', attempts);
      }
    },
  }
);
```

## Implementation Details

### State Management (BookPage.tsx)

```typescript
const [showExportOptions, setShowExportOptions] = useState(false);
const [showExportProgress, setShowExportProgress] = useState(false);
const [exportStatus, setExportStatus] = useState<ExportStatus>('pending');
const [exportProgress, setExportProgress] = useState(0);
const [exportError, setExportError] = useState<string | undefined>();
const [exportFilename, setExportFilename] = useState<string | undefined>();
```

### Progress Simulation

Currently using client-side progress simulation (backend doesn't provide real-time progress):

```typescript
const progressInterval = setInterval(() => {
  setExportProgress((prev) => {
    if (prev >= 90) return prev; // Cap at 90% until completion
    return prev + 10;
  });
}, 500);
```


## File Structure

```
frontend/src/
├── types/
│   └── export.ts                      # TypeScript interfaces
├── components/
│   └── export/
│       ├── ExportOptionsModal.tsx     # Options selection UI
│       ├── ExportProgressModal.tsx    # Progress tracking UI
│       ├── TemplateSelector.tsx       # Template selection
│       └── exportHelpers.ts           # Utility functions
├── lib/
│   ├── api/
│   │   └── bookClient.ts              # API methods (existing)
│   └── errors/                        # Error handling framework
│       ├── types.ts
│       ├── classifier.ts
│       ├── handler.ts
│       └── utils.ts
└── app/
    └── dashboard/
        └── books/
            └── [bookId]/
                └── page.tsx           # Integration point
```

## Supported Formats and API

All routes are `GET /api/v1/books/{book_id}/export/...`, owner-only (403 otherwise), implemented in `backend/app/api/endpoints/export.py`. Options are query parameters. Each download route is rate limited to 10 requests per hour per format, across all books.

| Route | Format and use | Query options |
|-------|----------------|---------------|
| `/pdf` | PDF: final publishing and printing | `include_empty_chapters`, `page_size` (`letter` or `A4`), `template_id`, `custom_options` |
| `/docx` | Word: further editing, manuscript submission | `include_empty_chapters`, `template_id`, `custom_options` |
| `/epub` | EPUB: e-readers and e-book platforms | `include_empty_chapters` |
| `/markdown` | Markdown: version control, plain-text workflows | `include_empty_chapters`, `multi_file` (one file per chapter, returned as a ZIP) |
| `/formats` | JSON: each format with its `available` flag, options, `book_stats` and `templates` | none |
| `/templates` | JSON: the professional templates (`classic_fiction`, `modern_nonfiction`, `academic`) | none |

- `custom_options` is a JSON object string of template overrides; malformed JSON returns 400.
- The author name and bio on the export come from the owner's profile.
- Downloads are named after the book title (`Content-Disposition`, RFC 6266 encoded).
- Status codes: 400 invalid options or unknown template, 503 export library unavailable, 504 export timed out, 500 other failures.

## Testing Considerations

### Unit Tests
- Export helpers (filename generation, validation)
- Progress calculation
- State management

### Integration Tests
- Modal interactions (open, configure, submit)
- API client methods
- Error handling scenarios

### E2E Tests
- Complete export workflow
- Retry scenarios
- Download verification

## Security Considerations

- The backend checks ownership (403 otherwise) and validates `page_size`, template id and `custom_options`.
- The browser holds the file as a blob; the object URL is revoked after the download. Nothing is stored client-side.

## References

- [Error Handling Architecture](error-handling.md)
