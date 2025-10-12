# Export Feature Architecture

**Status**: ✅ Production Ready
**Version**: 1.0.0
**Last Updated**: 2025-10-12

## Overview

The export feature allows users to export their books in multiple formats (PDF, DOCX) with customizable options. The system provides a modal-based workflow with real-time progress tracking and comprehensive error handling.

## Architecture Components

### 1. Type Definitions (`frontend/src/types/export.ts`)

Core TypeScript interfaces for type-safe export operations:

```typescript
export type ExportFormat = 'pdf' | 'docx';
export type PageSize = 'letter' | 'A4';

export interface ExportOptions {
  format: ExportFormat;
  includeEmptyChapters: boolean;
  pageSize?: PageSize; // PDF only
  chapters?: string[]; // Optional: specific chapters
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
}): Promise<Blob>

// Export DOCX with options
public async exportDOCX(bookId: string, options?: {
  includeEmptyChapters?: boolean;
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
- Format selection (PDF/DOCX) with visual indicators
- Page size selection (Letter/A4) for PDF exports
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
  - Format (PDF or DOCX)
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
  Error classified (Transient/Permanent/System)
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
    if (options.format === 'pdf') {
      return await bookClient.exportPDF(bookId, options);
    } else {
      return await bookClient.exportDOCX(bookId, options);
    }
  },
  {
    context: 'Export PDF/DOCX',
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

**Future Enhancement**: Implement backend polling for real progress updates.

## File Structure

```
frontend/src/
├── types/
│   └── export.ts                      # TypeScript interfaces
├── components/
│   └── export/
│       ├── ExportOptionsModal.tsx     # Options selection UI
│       ├── ExportProgressModal.tsx    # Progress tracking UI
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

## API Contracts

### PDF Export Request
```typescript
POST /api/books/{bookId}/export/pdf
Body: {
  includeEmptyChapters?: boolean;
  pageSize?: 'letter' | 'A4';
}
Response: Blob (application/pdf)
```

### DOCX Export Request
```typescript
POST /api/books/{bookId}/export/docx
Body: {
  includeEmptyChapters?: boolean;
}
Response: Blob (application/vnd.openxmlformats-officedocument.wordprocessingml.document)
```

### Export Formats Query
```typescript
GET /api/books/{bookId}/export/formats
Response: {
  formats: Array<{
    format: string;
    available: boolean;
    estimated_size: number;
  }>;
  book_stats: {
    total_chapters: number;
    completed_chapters: number;
    total_words: number;
    estimated_pages: number;
  };
}
```

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

## Performance Considerations

### Optimization
- Modal lazy loading
- Progress updates throttled to 500ms
- Blob cleanup after download
- State reset on modal close

### Scalability
- Export operations are async
- No blocking UI during export
- Memory management for large files
- Automatic cleanup of object URLs

## Security Considerations

### Input Validation
- Book ID validation
- Option constraints (page size, format)
- User permissions check

### File Handling
- Secure blob creation
- Automatic URL revocation
- No persistent storage of exports

## Future Enhancements

### Short-term
1. Backend real-time progress polling
2. Email notification for long exports
3. Export queue management
4. Export history tracking

### Long-term
1. Additional formats (EPUB, Markdown)
2. Custom styling options
3. Batch export multiple books
4. Export templates
5. Scheduled exports

## References

- [UI Improvements TODO](../UI_IMPROVEMENTS_TODO.md)
- [Error Handling Architecture](./ERROR_HANDLING_ARCHITECTURE.md)
- [Implementation Plan](../IMPLEMENTATION_PLAN.md)
