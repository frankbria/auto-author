# Export Functionality

This document describes the book export functionality in Auto Author, including supported formats, options, and current implementation status.

## Overview

The export feature allows users to generate downloadable versions of their books in various formats for publishing, sharing, or further editing. The export functionality includes format selection, customization options, and chapter selection.

## Supported Export Formats

### PDF Format
- **Description**: Portable Document Format with fixed layout
- **Use Case**: Final publishing, printing, professional presentation
- **Features**: Page numbers, headers, consistent formatting
- **File Extension**: `.pdf`

### EPUB Format
- **Description**: Electronic publication format optimized for e-readers
- **Use Case**: Digital publishing, e-book stores, mobile reading
- **Features**: Reflowable text, responsive design, metadata support
- **File Extension**: `.epub`

### Word Document (DOCX)
- **Description**: Microsoft Word format for further editing
- **Use Case**: Collaborative editing, manuscript submission, publisher requirements
- **Features**: Editable text, formatting preservation, track changes compatibility
- **File Extension**: `.docx`

### HTML Format
- **Description**: Web-compatible format for online publishing
- **Use Case**: Website integration, blog publishing, online reading
- **Features**: Web-optimized styling, hyperlinks, responsive design
- **File Extension**: `.html`

### Markdown Format
- **Description**: Plain text format with simple formatting syntax
- **Use Case**: Version control, technical documentation, plain text workflows
- **Features**: Lightweight markup, cross-platform compatibility
- **File Extension**: `.md`

## Export Options

### Standard Options
- **Include Cover Page**: Adds a cover page with book title and author information
- **Include Table of Contents**: Generates a structured TOC with page/section references
- **Include Page Numbers**: Adds page numbers to the document (PDF format)
- **Include Headers**: Adds chapter titles as page headers
- **Convert Links to Footnotes**: Converts hyperlinks to numbered footnotes for print formats

### Chapter Selection
- Users can select specific chapters to include in the export
- Chapters display their current status (Draft, Edited, Final)
- "Select All" and "Deselect All" options for bulk selection
- Visual status indicators help identify chapter completion status

## Export Process

### 1. Format Selection
- Choose from available export formats
- View format descriptions and use cases
- Format-specific icons for easy identification

### 2. Option Configuration
- Toggle export options on/off
- Preview selected options in export summary
- Options adapt based on selected format capabilities

### 3. Chapter Selection
- Select which chapters to include
- View chapter status and completion level
- Validate that at least one chapter is selected

### 4. Export Generation
- Progress indicator shows export status
- Real-time progress updates (0-100%)
- Export processing typically takes 15-60 seconds

### 5. Download
- Download link provided upon completion
- File named automatically with book title and format extension
- Option to export additional formats without re-configuration

## Current Implementation Status

⚠️ **Frontend Complete, Backend Pending**

### ✅ Implemented Features
- Complete export interface with format selection
- Export options configuration
- Chapter selection with status indicators
- Progress tracking and visual feedback
- Export summary and download interface
- Responsive design for mobile devices
- Export completion confirmation

### 🔴 Missing Backend Implementation
- Export generation APIs are not yet implemented
- Current interface uses mock data and simulated export process
- No actual file generation or download functionality
- No integration with book content or TOC data

### Required Backend APIs
```typescript
// Export operations
POST   /api/v1/books/{book_id}/export
GET    /api/v1/books/{book_id}/export/{export_id}/status
GET    /api/v1/books/{book_id}/export/{export_id}/download
GET    /api/v1/export/formats
POST   /api/v1/books/{book_id}/export/preview
```

## Usage Instructions

### Accessing Export
1. Navigate to your book dashboard
2. Click "Export Book" or similar navigation option
3. You'll be taken to the export configuration interface

### Configuring Export
1. **Choose Format**: Select your desired export format from the available options
2. **Set Options**: Toggle export options based on your needs
3. **Select Chapters**: Choose which chapters to include in the export
4. **Review Summary**: Verify your selections in the export summary panel

### Generating Export
1. Click "Export Book" to begin the process
2. Monitor progress via the progress indicator
3. Wait for export completion (typically 15-60 seconds)
4. Download your file when ready

### Troubleshooting Export Issues

#### Export Button Disabled
- **Cause**: No format selected or no chapters selected
- **Solution**: Ensure both a format and at least one chapter are selected

#### Slow Export Process
- **Cause**: Large book size or complex formatting
- **Solution**: Consider exporting fewer chapters or simpler formats first

#### Download Issues
- **Cause**: Browser download restrictions or network issues
- **Solution**: Check browser download settings and network connectivity

## Planned Enhancements (Future Releases)

### v2.0+ Features
- **Custom Styling**: Font selection, spacing, and layout options
- **Batch Export**: Export multiple formats simultaneously
- **Export Templates**: Predefined styling templates for different use cases
- **Preview Mode**: Preview export formatting before generation
- **Export History**: Track and manage previous exports
- **Metadata Inclusion**: Author, copyright, and publication metadata
- **Advanced TOC**: Customizable table of contents formatting

### Integration Features
- **Publishing Platform Integration**: Direct export to publishing platforms
- **Cloud Storage**: Export directly to Google Drive, Dropbox, etc.
- **Email Delivery**: Send exports via email
- **Version Comparison**: Compare exports from different book versions

## API Integration

### Current Mock Implementation
The frontend currently simulates the export process using mock data and progress indicators. Real implementation will require:

1. **Format Validation**: Ensure selected format is supported
2. **Content Processing**: Convert book content to target format
3. **Option Application**: Apply selected export options
4. **File Generation**: Create downloadable file
5. **Storage Management**: Temporary file storage and cleanup

### Error Handling
- Format compatibility validation
- Chapter content availability checks
- File size limitations
- Export timeout handling
- Network connectivity issues

## Related Documentation

- [User Stories - Export Book Content](../user-stories.md#user-story-81-export-book-content)
- [API Gaps Analysis](../frontend-backend-api-gaps-analysis.md)
- [TOC Generation User Guide](user-guide-toc-generation.md)
- [Publishing Integration Documentation](publishing-integration.md) (Future)

## Support

For export-related issues:
1. Check that your book has content to export
2. Verify browser compatibility for downloads
3. Ensure adequate network connectivity
4. Contact support with specific error messages if issues persist
