# Auto-Author UI Flow Documentation

## Overview
Auto-Author is a web application for AI-assisted book writing. The application guides users through a structured process from book creation to content generation and export.

## User Journey

### 1. Landing Page (`/`)
**Purpose**: Entry point for all users
- **Unauthenticated**: Shows welcome message with Sign In/Sign Up buttons (Clerk auth)
- **Authenticated**: Shows welcome back message with "Go to Dashboard" button
- **Next Step**: Redirects to `/dashboard` after authentication

### 2. Dashboard (`/dashboard`)
**Purpose**: Central hub for managing books
- **Components**: 
  - Book grid showing all user's books
  - EmptyBookState when no books exist
  - "Create New Book" button
- **Actions**:
  - Click book card → Book detail page
  - Click "Create New Book" → Opens BookCreationWizard modal
- **Next Step**: Book creation or book editing

### 3. Book Creation Flow
**Component**: `BookCreationWizard` (modal)
- **Fields**:
  - Title (required)
  - Subtitle
  - Description  
  - Cover Image URL
  - Genre (dropdown)
  - Target Audience (dropdown)
- **Validation**: Zod schema validation
- **Next Step**: Redirects to `/dashboard/books/[bookId]` on success

### 4. Book Detail Page (`/dashboard/books/[bookId]`)
**Purpose**: Book management and chapter editing hub
- **Layout**:
  - Left: Book metadata and statistics
  - Center: Chapter tabs or wizard steps
  - Right: Book progress stats
- **Wizard Steps** (for new books):
  1. Write Book Summary → `/summary`
  2. Generate TOC → `/generate-toc`
  3. Write Content → Shows chapter tabs
- **Features**:
  - Editable book metadata
  - Chapter tab interface (vertical tabs)
  - Export button (PDF generation)

### 5. Book Summary (`/dashboard/books/[bookId]/summary`)
**Purpose**: Capture book overview for AI TOC generation
- **Features**:
  - Large textarea (30-2000 characters)
  - Voice input button (speech-to-text)
  - Auto-save to localStorage and remote
  - Revision history with revert
  - Real-time validation
- **Next Step**: Submit → `/generate-toc`

### 6. TOC Generation (`/dashboard/books/[bookId]/generate-toc`)
**Purpose**: AI-powered table of contents creation
- **Component**: `TocGenerationWizard`
- **Flow**:
  1. Analyze summary for readiness
  2. Generate clarifying questions (optional)
  3. Generate TOC structure
  4. Review and edit chapters
- **Features**:
  - Add/remove/reorder chapters
  - Edit chapter titles and descriptions
  - Regenerate with different parameters
- **Next Step**: Save → Book detail page with chapter tabs

### 6a. Edit TOC (`/dashboard/books/[bookId]/edit-toc`)
**Purpose**: Manual TOC editing after generation
- **Features**:
  - Add/delete chapters and subchapters
  - Drag-and-drop reordering
  - Edit titles and descriptions inline
  - Chapter status indicators
  - Nested structure support (2 levels)
- **Next Step**: Save → Book detail page with chapter tabs

### 7. Chapter Editing (Main Writing Interface)
**Components**:
- **ChapterTabs**: Vertical tab navigation
  - Keyboard shortcuts (Ctrl+1-9)
  - Drag-and-drop reordering
  - Status indicators
  - Context menu for status updates
- **ChapterEditor**: Rich text editor
  - TipTap editor with formatting toolbar
  - Auto-save (3-second delay)
  - Character/word count
  - AI draft generation button
  - Voice input integration

### 8. AI Content Generation
**Components**:
- **DraftGenerator**: AI-powered content creation
  - Uses question/answer approach
  - Generates draft based on chapter context
- **QuestionGenerator**: Interview-style questions
  - Generates relevant questions for chapter
  - Collects answers to guide AI

### 9. Export (`/dashboard/books/[bookId]/export`)
**Purpose**: Export book in various formats
- **Formats**: PDF, DOCX (others shown but not implemented)
- **Options**:
  - Include empty chapters
  - Page size selection
  - Chapter selection
- **Status**: Partially implemented (backend complete)

### Alternative Flow: Interview Questions (`/dashboard/books/[bookId]/chapters`)
**Purpose**: Alternative content creation approach using interview-style questions
- **Features**:
  - Pre-generated questions for each chapter
  - Mark questions as relevant/irrelevant
  - Regenerate questions with AI
  - Chapter navigation sidebar
- **Status**: Disconnected from main flow (appears to be an experimental feature)
- **Note**: Uses mock data, not integrated with backend

## Component Architecture

### Layout Components
- `layout.tsx` - Root layout with Clerk provider
- `dashboard/layout.tsx` - Dashboard wrapper with nav

### Page Components
- Landing page - Authentication gateway
- Dashboard - Book management
- Book pages - Summary, TOC, chapters, export

### Feature Components
- `BookCreationWizard` - New book form
- `TocGenerationWizard` - AI TOC creation
- `ChapterTabs` - Chapter navigation
- `ChapterEditor` - Rich text editing
- `VoiceTextInput` - Speech-to-text
- `DraftGenerator` - AI content generation

### UI Components (shadcn/ui)
- Extensive component library
- Consistent theming (dark mode default)
- Responsive design patterns

## Navigation Flow

```
Landing → Dashboard → Book Creation → Book Detail
                  ↓                         ↓
              Book List              Summary Input
                                           ↓
                                    TOC Generation
                                           ↓
                                    Chapter Editing
                                           ↓
                                        Export
```

## Current Issues & Gaps

### Missing/Broken Features
1. **~~Edit TOC Page~~** - ✅ Page exists and is fully functional at `/dashboard/books/[bookId]/edit-toc`
2. **PDF Generation** - Button exists but needs to be connected to backend export endpoints
3. **Question Flow** - `/chapters` page exists but is disconnected from main flow (appears to be an alternative content creation approach)
4. **Export Formats** - Only PDF/DOCX implemented in backend

### Integration Issues
1. **Voice Input** - Using browser API, not production service
2. **Mock Services** - Some features still using mocks
3. **Tab State** - Errors mentioned in comments

### UX Improvements Needed
1. **Book Deletion** - No UI for deleting books
2. **Settings/Help** - Placeholder pages
3. **Mobile Experience** - Needs refinement
4. **Progress Indicators** - Better feedback during long operations

### Missing Features
1. **Collaboration** - No multi-user editing
2. **Version Control** - No revision history for chapters
3. **Advanced Export** - Limited format support
4. **Offline Support** - No offline capabilities

## Recommendations

### Immediate Fixes
1. Implement missing edit-toc page
2. Connect PDF generation to backend
3. Fix tab state persistence issues
4. Complete export functionality

### UX Enhancements
1. Add book deletion UI
2. Implement proper settings page
3. Add help documentation
4. Improve mobile responsiveness

### Feature Completion
1. Replace mock services with production
2. Add revision history for chapters
3. Implement remaining export formats
4. Add progress tracking for long operations

## Technical Notes

- **Authentication**: Clerk (working well)
- **State Management**: React hooks + API calls
- **Styling**: Tailwind CSS + shadcn/ui
- **Editor**: TipTap (fully integrated)
- **AI Integration**: OpenAI GPT-4 (backend ready)
- **Export**: ReportLab (PDF), python-docx (DOCX)

The application has a solid foundation with a clear user flow from book creation through content generation. The main areas needing attention are completing partially implemented features and improving the overall polish of the user experience.