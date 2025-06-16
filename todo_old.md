# Auto Author - Todo List

> ⚠️ **DEPRECATED**: This document has been superseded by `TODO_CONSOLIDATED.md`
> Please refer to TODO_CONSOLIDATED.md for the current, accurate project status.

## 🚨 MVP BLOCKERS - HIGH PRIORITY

These features are ESSENTIAL for a functional MVP. Without them, authors cannot create, edit, or export their books.

### User Story 4.5: Rich Text Editor Integration 🎯 **CRITICAL MVP BLOCKER**
**Status: ~40% Complete** - TipTap exists but NOT integrated with chapter editing workflow

#### Immediate Tasks
- [ ] Connect TipTap editor to chapter content editing in ChapterEditor component
- [ ] Enable saving and loading of chapter content
- [ ] Add basic formatting toolbar (bold, italic, headings, lists)
- [ ] Implement auto-save functionality (3-second intervals)
- [ ] Add unsaved changes indicator
- [ ] Create loading and error states for content operations

#### Future Enhancements (Post-MVP)
- [ ] Add revision tracking and version history
- [ ] Implement draft/edited/final version states
- [ ] Add advanced formatting (tables, images, links)
- [ ] Create undo/redo functionality
- [ ] Add collaborative editing features

### User Story 4.4: AI Draft Generation 🎯 **CRITICAL MVP BLOCKER**
**Status: ~30% Complete** - API exists but uses MOCK AI service

#### Immediate Tasks
- [ ] Replace mock AI service with real OpenAI/Claude API integration
- [ ] Implement proper AI prompt engineering for Q&A to narrative transformation
- [ ] Add API key configuration and environment variables
- [ ] Create progress indicators during generation
- [ ] Implement error handling and retry logic
- [ ] Add basic content validation and safety checks

#### Backend Implementation
- [X] API endpoint created (/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft)
- [ ] AI service integration (currently mocked)
- [ ] Context aggregation from questions and answers
- [ ] Rate limiting and cost management

### Production Services Integration 🎯 **CRITICAL MVP BLOCKER**
**Status: 0% Complete** - All external services are mocked

#### Voice Transcription Service
- [ ] Replace mock transcription with Azure Speech/Google Cloud Speech/AWS Transcribe
- [ ] Integrate VoiceTextInput component with chapter forms
- [ ] Add API key configuration
- [ ] Implement audio upload and processing
- [ ] Add language selection support

#### Cloud Storage Service
- [ ] Replace local file storage with S3/Cloudinary
- [ ] Migrate book cover uploads to cloud storage
- [ ] Implement secure file URLs and access control
- [ ] Add file size limits and validation
- [ ] Create cleanup policies for unused files

### Navigation & UX Fixes 🎯 **CRITICAL MVP BLOCKER**
**Status: Partially broken** - Confusing user flow

#### Immediate Tasks
- [ ] Fix book page to redirect to chapter tabs interface instead of individual chapters
- [ ] Update routing logic in /books/[bookId]/page.tsx
- [ ] Ensure breadcrumb navigation works correctly
- [ ] Fix wizard step logic to show correct progress
- [ ] Add clear CTAs for next steps in workflow

### Export Functionality 🎯 **MVP FEATURE**
**Status: ~10% Complete** - Only UI mockup exists

#### Immediate Tasks
- [ ] Implement backend PDF generation using libraries like ReportLab or WeasyPrint
- [ ] Create DOCX export using python-docx
- [ ] Build API endpoints for export requests
- [ ] Add progress tracking for export operations
- [ ] Implement basic formatting preservation
- [ ] Create download functionality

#### Frontend Implementation
- [X] Export page UI created (/export/page.tsx)
- [ ] Connect UI to backend API
- [ ] Add loading states during export
- [ ] Implement error handling

## ✅ COMPLETED FEATURES

### Epic 1: User Management ✅ **COMPLETE**
- [X] User authentication with Clerk
- [X] Profile management
- [X] Session handling
- [X] Protected routes

### Epic 2: Book Creation & Metadata ✅ **COMPLETE**
- [X] Book CRUD operations
- [X] Metadata management
- [X] Cover image uploads
- [X] Genre and audience selection

### Epic 3: TOC Generation ✅ **COMPLETE**
- [X] AI-powered TOC generation from summary
- [X] Clarifying questions workflow
- [X] TOC editing with drag-and-drop
- [X] Hierarchical chapter structure

### User Story 4.1: Chapter Tabs ✅ **COMPLETE**
- [X] Vertical tabs interface
- [X] Drag-and-drop reordering
- [X] Status indicators
- [X] Mobile responsive design
- [X] Keyboard shortcuts

### User Story 4.2: Question System ✅ **COMPLETE**
- [X] 6 React components for question workflow
- [X] 9 API endpoints with full CRUD
- [X] AI-powered question generation
- [X] Response collection and rating
- [X] Progress tracking

### User Story 4.3: Voice Input Component ✅ **COMPLETE**
- [X] VoiceTextInput component created
- [X] Recording interface with controls
- [X] Real-time transcription display
- [X] Error handling and recovery
- [⚠️] Still using mock transcription service (see Production Services above)

## 🔧 TECHNICAL DEBT & IMPROVEMENTS

### High Priority
- [ ] Fix broken test suites
- [ ] Improve test coverage to 80%+
- [ ] Standardize error handling across the application
- [ ] Add comprehensive logging

### Medium Priority
- [ ] Standardize UI components (replace inline styles)
- [ ] Improve mobile responsiveness on all pages
- [ ] Add loading skeletons instead of spinners
- [ ] Implement proper caching strategies

### Low Priority
- [ ] Update documentation to reflect actual state
- [ ] Create developer onboarding guide
- [ ] Add performance monitoring
- [ ] Implement analytics tracking

## 🔮 FUTURE ENHANCEMENTS (Post-MVP)

### Epic 5: Regeneration & Flexibility
- [ ] Regenerate TOC with different parameters
- [ ] Regenerate questions for chapters
- [ ] Regenerate draft content with style options

### Epic 6: Advanced Editing
- [ ] Full rich text editor with all formatting options
- [ ] Revision history and version control
- [ ] Collaborative editing with multiple users
- [ ] Grammar and style checking

### Epic 7: Analytics & Insights
- [ ] Writing progress statistics
- [ ] Content quality metrics
- [ ] Reading level analysis
- [ ] Time tracking for chapters

### Epic 8: Publishing & Distribution
- [ ] Publishing platform integration
- [ ] ISBN generation
- [ ] Marketing material generation
- [ ] Distribution channel setup

### Epic 9: Mobile & Offline
- [ ] Mobile companion app
- [ ] Offline editing capability
- [ ] Cross-device synchronization
- [ ] Voice dictation on mobile

## 📋 SPRINT PLANNING

### Sprint 1 (Current) - Core MVP Completion
**Goal: Make the app functional for basic book creation**
1. Complete Rich Text Editor integration (2 days)
2. Fix navigation to use chapter tabs (1 day)
3. Replace mock AI service (2 days)

### Sprint 2 - Production Services
**Goal: Replace all mock services with real implementations**
1. Integrate production speech-to-text (2 days)
2. Implement cloud storage (2 days)
3. Add error handling and recovery (1 day)

### Sprint 3 - Export & Polish
**Goal: Enable users to export their work**
1. Implement PDF/DOCX export (3 days)
2. Fix UI inconsistencies (1 day)
3. Improve test coverage (1 day)

### Sprint 4 - Production Readiness
**Goal: Prepare for launch**
1. Security audit and fixes
2. Performance optimization
3. Documentation updates
4. Beta testing feedback

## 📝 NOTES

### Current State Summary
- **Authentication**: ✅ Complete
- **Book Management**: ✅ Complete
- **TOC Generation**: ✅ Complete
- **Chapter Organization**: ✅ Complete
- **Question System**: ✅ Complete
- **Rich Text Editing**: ❌ Not integrated
- **AI Draft Generation**: ❌ Using mock service
- **Voice Transcription**: ❌ Using mock service
- **File Storage**: ❌ Using local storage
- **Export**: ❌ No backend implementation

### Critical Path to MVP
1. **Rich Text Editor** - Without this, users can't edit content
2. **AI Integration** - Without this, draft generation doesn't work
3. **Navigation Fix** - Without this, UX is confusing
4. **Export** - Without this, users can't use their content

### Removed Features (Not MVP)
- Auto-save with version history
- Collaborative editing
- Advanced formatting options
- Analytics dashboard
- Mobile app
- Publishing integration

---
*Last Updated: January 2025*
*MVP Target: Complete core authoring workflow*