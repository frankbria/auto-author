# Summary Input Requirements and Best Practices

This document outlines the requirements, validation rules, and best practices for the summary input functionality in Auto Author.

## Overview

The summary input feature allows users to provide a book summary or synopsis through either text input or voice-to-text functionality. This summary is used by the AI to generate a draft Table of Contents (TOC) for the book.

## Technical Requirements

### Input Methods
- **Text Input**: Traditional textarea with rich validation and feedback
- **Voice Input**: Speech-to-text using Web Speech API
- **Auto-save**: Automatic saving to both local storage and backend
- **Revision History**: Track and restore previous versions

### Validation Rules

| Requirement | Value | Enforcement |
|-------------|-------|-------------|
| Minimum Length | 30 words | Frontend warning, backend validation |
| Maximum Characters | 2,000 | Hard limit enforced |
| Required Content | Non-empty summary | Generate TOC button disabled until met |
| Character Encoding | UTF-8 | Automatic |
| Special Characters | Allowed | Basic sanitization |

### Performance Requirements
- **Auto-save Delay**: 600ms debounce after typing stops
- **Voice Recognition**: Real-time transcription display
- **Character Count**: Real-time updates as user types
- **Error Recovery**: Graceful handling of speech recognition failures

## Best Practices for Users

### Writing Effective Summaries

1. **Include Essential Elements**:
   - Main concept or premise
   - Target genre (fiction/non-fiction)
   - Key themes or topics
   - Target audience

2. **Structure Guidelines**:
   - Aim for 1-3 coherent paragraphs
   - Use clear, descriptive language
   - Avoid excessive jargon or technical terms
   - Include the book's primary purpose or goal

3. **Length Recommendations**:
   - **Minimum**: 30 words (required for TOC generation)
   - **Optimal**: 100-300 words
   - **Maximum**: 2,000 characters

### Voice Input Best Practices

1. **Environment Setup**:
   - Use in a quiet environment
   - Speak clearly and at normal pace
   - Position microphone appropriately

2. **Speaking Techniques**:
   - Pause naturally between sentences
   - Say punctuation when needed ("period", "comma")
   - Speak in complete thoughts
   - Review transcription for accuracy

3. **Error Handling**:
   - Always review voice transcriptions
   - Edit transcribed text as needed
   - Use retry option for failed recordings

## Example Summaries

### Good Example
```
"A comprehensive guide to sustainable gardening practices for urban environments. This book teaches readers how to create productive gardens in small spaces using organic methods, composting, and water conservation techniques. Topics include container gardening, vertical growing systems, and seasonal planning. Targeted at beginning to intermediate gardeners who want to grow their own food while minimizing environmental impact."
```

### What Makes This Good:
- Clear subject matter (sustainable urban gardening)
- Target audience (beginning to intermediate gardeners)
- Specific topics covered
- Purpose and benefits clearly stated
- Appropriate length and detail

### Poor Example
```
"Gardening book."
```

### Why This is Poor:
- Too brief (only 2 words, minimum 30 required)
- No specific focus or audience
- No indication of unique value
- Insufficient detail for AI to generate meaningful TOC

## Technical Implementation

### Frontend Validation
- Real-time character and word counting
- Visual feedback for minimum requirements
- Auto-save indication
- Error state handling

### Backend Validation
- Content sanitization
- Length validation (min/max)
- Offensive content filtering
- Revision history storage

### Voice Recognition
- Browser compatibility checking
- Permission handling
- Error recovery mechanisms
- Transcription accuracy optimization

## Integration Points

### TOC Generation
- Summary content drives AI TOC generation
- Minimum word count required to enable generation
- Quality affects output relevance

### Auto-save System
- Local storage for offline capability
- Backend persistence for data security
- Conflict resolution for concurrent edits

### Revision History
- Track significant changes
- Allow restoration of previous versions
- Maintain audit trail

## Accessibility Considerations

- Screen reader compatibility
- Keyboard navigation support
- High contrast mode support
- Voice input as accessibility aid
- Clear error messaging

## Related Documentation

- [User Guide: Summary Input and Voice-to-Text](user-guide-summary-input.md)
- [API Endpoints: Summary Operations](api-summary-endpoints.md)
- [Troubleshooting: Summary Input Issues](troubleshooting-summary-input.md)
- [Book Metadata Documentation](book-metadata-fields.md)

---

Last updated: May 17, 2025
