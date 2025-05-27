# Auto Author - Todo List

# Epic 1: User Management
## User Story 1.1: Account Registration (with Clerk)

### Frontend Tasks
- [X] Install Clerk SDK and dependencies in the frontend
- [X] Set up Clerk provider in### Documentation Tasks
- [X]  Document summary input requirements and best practices
- [X]  Create user guide for summary input and voice-to-text
- [X]  Document API endpoints for summary saving/retrieval
- [X]  Add troubleshooting for common summary input issuesNext.js app
- [X] Implement Clerk SignUp component in registration page
- [X] Customize Clerk UI to match application design
- [X] Configure allowed authentication methods (email/password, social logins)
- [X] Add optional fields for name and profile picture using Clerk's profile fields
- [X] Configure redirect to dashboard after successful registration
- [X] Add loading states and error handling for Clerk components
- [X] Implement protected routes using Clerk authentication state
- [X] Fixed client-side auth utility implementation
- [X] Added server-side helper functions in clerk-helpers.ts

### Backend Tasks
- [X] Set up Clerk environment variables and API keys
- [X] Create user mapping model to associate Clerk users with application data
- [X] Set up API endpoints to fetch current user data from Clerk
- [X] Configure JWT verification with Clerk for API authentication
- [X] Set up role-based permissions using Clerk metadata
- [X] Fix authentication issue with utils.ts getAuth() function

### Testing Tasks
- [X] Test Clerk SignUp component integration
- [X] Test authentication state persistence
- [X] Validate protected routes are functioning correctly
- [X] Verify API authentication with Clerk tokens

### Documentation Tasks
- [X] Created usage examples for different contexts
- [X] Document Clerk integration configuration
- [X] Create user guide for registration and authentication options
- [X] Create deployment checklist for Clerk-related environment variables

## User Story 1.2: Login / Logout (with Clerk)

### Frontend Tasks
- [x] Implement Clerk SignIn component in login page
- [X] Create "Remember me" functionality using Clerk's session options
- [x] Design and implement navbar with login/logout state awareness
- [x] Implement session recovery for returning users
- [x] Add loading states for authentication processes
- [x] Create error message displays for authentication failures
- [x] Set up appropriate redirects after login/logout
- [x] Implement automatic session refresh
- [x] Add visual indicators for current authentication state

### Backend Tasks
- [x] Configure Clerk session management in FastAPI
- [x] Set up API endpoints for session validation
- [x] Implement session middleware for protected routes
- [x] Create webhook handlers for login/logout events
- [X] Configure session timeout settings
- [X] Implement "remember me" session persistence
- [X] Set up multi-device session management
- [X] Add session monitoring for security purposes

### Testing Tasks
- [X] Test login functionality with various credentials
- [X] Verify logout properly terminates sessions
- [X] Validate error handling for invalid login attempts
- [X] Test session timeout and renewal flows
- [X] Verify security measures against common attacks
- [X] Test multi-device login scenario behaviors
- [X] Validate login state preservation during navigation

### Documentation Tasks
- [X] Document login/logout flows and configuration
- [X] Create troubleshooting guide for authentication issues
- [X] Document session management strategies
- [X] Update API documentation for authentication endpoints


## User Story 1.3: User Profile CRUD

### Frontend Tasks
- [X] Edit user profile page (`/frontend/src/app/profile/page.tsx`) with editable fields
- [X] Implement form validation for profile information
- [X] Add avatar/profile picture upload functionality
- [X] Integrate into Clerk profile change (login, password, etc.)
- [X] Implement user preferences section (theme, notifications)
- [X] Add success/error notifications for profile updates
- [X] Create account deletion confirmation modal
- [X] Add form field validation with real-time feedback
- [X] Implement auto-save for profile changes

### Backend Tasks
- [X] Create API endpoints for profile data retrieval
- [X] Implement API endpoints for profile data updates
- [X] Create user preferences storage in database
- [X] Implement account deletion process with data cleanup
- [X] Add validation middleware for profile update requests
- [X] Create rate limiting for sensitive operations
- [X] Set up audit logging for profile changes
- [X] Implement data sanitization for profile fields

### Testing Tasks
- [X] Test profile data retrieval and display
- [X] Verify all editable fields update correctly
- [X] Test account deletion process and data handling
- [X] Verify user preferences are saved and applied correctly
- [X] Validate form validation for all profile fields
- [X] Test file upload for profile pictures
- [X] Verify error handling for all edge cases

### Documentation Tasks
- [X] Document profile management features and options
- [X] Create user guide for profile editing
- [X] Document API endpoints for profile operations
- [X] Create troubleshooting guide for common profile issues
- [X] Document security considerations for profile changes
- [X] Update API documentation with profile endpoints

# Epic 2: Book Creation & Metadata
## User Story 2.1: Create a New Book

### Frontend Tasks
- [X] Create "New Book" button on dashboard/home page
- [X] Build book creation form or wizard interface
- [X] Implement form validation for required book fields
- [X] Add loading states and success indicators
- [X] Design empty book state with guided next steps
- [X] Create redirect to appropriate page after book creation
- [X] Implement book project card in user's dashboard
- [X] Add empty TOC placeholder for new books
- [X] Create initial book setup workflow UI
- [X] Add helpful tooltips for first-time book creators

### Backend Tasks
- [X] Define book schema and data model (change Books field in user schema to connect with new data model)
- [X] Create API endpoint for new book creation
- [X] Implement data validation for book creation requests
- [X] Set up database queries for book creation
- [X] Add user-book relationship in database
- [X] Create empty TOC structure for new books
- [X] Implement auto-save for draft book information
- [X] Set up book visibility/privacy controls
- [X] Add rate limiting for book creation
- [X] Create book import functionality (optional)

### Testing Tasks
- [X] Test book creation from dashboard
- [X] Verify form validation for required fields
- [X] Test API endpoint for book creation
- [X] Validate book appears in user's dashboard
- [X] Test empty TOC structure creation
- [X] Verify redirects after successful book creation
- [X] Test book creation with minimum required fields
- [X] Validate error handling for failed book creation
- [X] Test book creation limits if applicable
- [X] Verify book data persistence between sessions

### Documentation Tasks
- [X] Document book creation process and options
- [X] Create user guide for starting a new book
- [X] Document API endpoints for book creation
- [X] Update database schema documentation
- [X] Document book data model and relationships
- [X] Create troubleshooting guide for common book creation issues

## User Story 2.2: Book Info CRUD

### Frontend Tasks
- [X] Create book settings/info page with editable metadata fields (title, subtitle, synopsis, audience, genre, cover image, etc.)
- [X] Implement form validation for all book metadata fields (length, required, allowed values)
- [X] Add cover image upload UI with preview and format/size validation
- [X] Implement genre and target audience selection (dropdowns, etc.)
- [X] Add auto-save functionality for metadata changes
- [X] Provide real-time feedback and success/error indicators for saves
- [X] Handle edge cases (very long fields, special characters, invalid images)
- [X] Ensure UI uses shadcn/ui form components and matches design system

### Backend Tasks
- [X] Extend book schema/model to support all metadata fields (title, subtitle, synopsis, audience, genre, cover image, etc.)
- [X] Implement API endpoints for retrieving and updating book metadata (GET, PATCH/PUT)
- [X] Add backend validation for all metadata fields
- [ ] Implement file upload endpoint for cover images with validation and storage
- [X] Add authorization checks for book metadata updates
- [X] Implement rate limiting and error handling for metadata endpoints

### Testing Tasks
- [X] Test retrieval and update of book metadata via API
- [X] Test frontend metadata editing and validation
- [X] Test cover image upload (valid/invalid formats, size limits)
- [X] Test auto-save and real-time feedback
- [X] Test edge cases (long fields, special characters, concurrent edits)
- [X] Verify metadata changes persist between sessions and reloads

### Documentation Tasks
- [X] Document all book metadata fields and their requirements
- [X] Update API documentation for book metadata endpoints
- [X] Create user guide for editing book info and uploading cover images
- [X] Add troubleshooting section for common metadata issues
- [X] Document validation rules and error messages

# Epic 3: TOC Generation & Editing
## User Story 3.1: Provide Summary Input
### Frontend Tasks
- [X]  Create summary input interface (text area) with clear labeling and helpful prompts/examples
- [X]  Implement voice-to-text functionality for spoken summary input
- [X]  Build real-time character/word count and display input guidelines
- [X]  Add auto-save for in-progress summaries (local and remote)
- [X]  Show summary revision history and allow reverting to previous versions
- [X]  Enable "Generate TOC" button only when summary meets minimum requirements
- [X]  Handle edge cases: very short/long summaries, failed voice transcription, multilingual input, offensive content, offline input
### Backend Tasks
- [X]  Implement API endpoint for saving/retrieving summary (/api/v1/books/{id}/summary)
- [X]  Store summary text and revision history in database
- [X]  Add validation for summary length/content (min/max, offensive content filter)
- [X]  Support auto-save and offline sync for summary drafts
### Testing Tasks
- [X]  Test summary input (typing and voice) and real-time feedback
- [X]  Test auto-save and revision history functionality
- [X]  Test API endpoints for summary saving and retrieval
- [X]  Test edge cases: short/long summaries, failed transcription, offline mode
- [X]  Verify "Generate TOC" button enables/disables correctly
### Documentation Tasks
- [X]  Document summary input requirements and best practices
- [X]  Create user guide for summary input and voice-to-text
- [X]  Document API endpoints for summary saving/retrieval
- [X]  Add troubleshooting for common summary input issues

## User Story 3.2: Generate TOC from Summary
### Frontend Tasks
- [X]  Create TOC generation wizard component with multi-step interface
- [X]  Build AI-generated clarifying questions display component <!-- Implemented: ClarifyingQuestions component displays questions, collects answers, and shows progress. -->
- [X]  Implement user responses collection form for clarifying questions <!-- Implemented: ClarifyingQuestions includes a form for user answers, navigation, and validation. -->
- [X]  Create progress indicator for TOC generation process <!-- Implemented: TocGenerationWizard and TocGenerating show step progress bars and percentage indicators. -->
- [X]  Build hierarchical TOC preview component with chapters and subchapters <!-- Implemented: TocReview displays a hierarchical, expandable/collapsible TOC preview. -->
- [X]  Add "Generate TOC" button integration from summary page <!-- Implemented: Summary page enables the button when requirements are met, linking to the wizard. -->
- [X]  Implement loading states and generation status indicators <!-- Implemented: All steps/components show loading spinners, disabled buttons, and status messages. -->
- [X]  Create TOC generation results page with accept/regenerate options <!-- Implemented: TocReview provides Accept/Regenerate buttons and displays the generated TOC. -->
- [X]  Add tooltips explaining AI's TOC structure decisions <!-- Implemented: Tooltips and info sections (e.g., "AI Structure Notes", "Tips for better answers") are present. -->
- [X]  Build responsive design for TOC wizard on mobile devices <!-- Implemented: All wizard components use responsive Tailwind classes for mobile compatibility. -->

### Backend Tasks
- [x]  Implement AI service integration for summary analysis
- [x]  Create TOC generation algorithm based on summary content
- [x]  Build clarifying questions generation logic (3-5 questions)
- [x]  Implement API endpoint for TOC generation requests (/api/v1/books/{id}/generate-toc)
- [x]  Create API endpoint for clarifying questions (/api/v1/books/{id}/generate-questions)
- [x]  Build API endpoint for processing user responses to questions (/api/v1/books/{id}/question-responses)
- [x]  Create API endpoint to check TOC generation readiness (/api/v1/books/{id}/toc-readiness)
- [x]  Implement TOC data model with hierarchical structure support
- [x]  Add validation for generated TOC structure and content
- [x]  Create TOC storage and retrieval in book records
- [x]  Implement error handling for AI service failures and timeouts
- [x]  Add retry mechanism for failed TOC generation attempts

### Testing Tasks
- [X]  Write unit tests for TOC generation wizard components <!-- Covered by TocGenerationWizard.test.tsx: unit tests for wizard, clarifying questions, generating, and review components. -->
- [X]  Test clarifying questions generation and user response handling <!-- Covered by TocGenerationWizard.test.tsx: 'renders ClarifyingQuestions and handles answers' test. -->
- [X]  Create integration tests for TOC generation API endpoints <!-- Covered by backend/tests/test_api/test_routes/test_toc_generation.py: tests /api/v1/books/{book_id}/generate-toc endpoint end-to-end. -->
- [X]  Test TOC preview component with various hierarchical structures <!-- Covered by frontend/src/__tests__/TocGenerationWizard.test.tsx: 'renders TocReview with deeply nested and empty chapters' test. -->
- [X]  Verify progress indicators and loading states work correctly
- [X]  Test edge cases: very brief summaries, complex summaries, ambiguous content
- [X]  Test AI service timeout and error recovery mechanisms <!-- Covered by backend tests for error handling and retry logic. -->
- [X]  Verify TOC generation works with different book genres and audiences
- [X]  Test mobile responsiveness of TOC generation wizard
- [X]  Create end-to-end tests for complete TOC generation workflow

### Documentation Tasks
- [X]  Document TOC generation requirements and AI integration
- [X]  Create user guide for TOC generation wizard workflow
- [X]  Document API endpoints for TOC generation and clarifying questions
- [X]  Add troubleshooting guide for TOC generation issues and failures


## User Story 3.3: Edit and Save TOC

### Frontend Tasks
- [X] Create interactive TOC editor interface with chapter/subchapter list <!-- Implemented: edit-toc page displays chapters hierarchically with nested structure -->
- [X] Implement drag-and-drop functionality for reordering chapters and subchapters <!-- COMPLETED: Full drag-and-drop implementation with state management, event handlers, reordering logic, and visual feedback - Tested and verified May 26, 2025 -->
- [X] Add inline editing for chapter titles and descriptions <!-- Implemented: input fields and textarea allow direct editing of titles and descriptions -->
- [X] Build chapter/subchapter addition and deletion controls <!-- Implemented: add chapter/subchapter buttons and delete buttons with icons -->
- [X] Implement chapter hierarchy visualization (indentation, connecting lines) <!-- Implemented: visual hierarchy through depth-based indentation (marginLeft) -->
- [ ] Create hierarchy manipulation controls (promote/demote chapters) <!-- Not implemented: no promote/demote functionality found -->
- [ ] Add validation for chapter titles (required, length limits) <!-- Not implemented: no client-side validation found -->
- [ ] Implement confirmation dialogs for destructive actions (delete) <!-- Not implemented: delete actions happen immediately without confirmation -->
- [X] Create responsive layout for TOC editor on mobile devices <!-- Implemented: uses responsive Tailwind classes and container max-width -->
- [ ] Add keyboard navigation and accessibility features <!-- Not implemented: no keyboard shortcuts or accessibility features found -->
- [ ] Implement undo/redo functionality for TOC edits <!-- Not implemented: no undo/redo functionality found -->
- [X] Add visual feedback for successful saves and error states <!-- Implemented: loading states with spinners, error display with red backgrounds, save button shows "Saving..." state -->

### Backend Tasks
- [X] Create API endpoint for updating TOC structure (/api/v1/books/{id}/toc) <!-- Implemented: PUT /books/{book_id}/toc endpoint in books.py -->
- [X] Implement validation for TOC update requests <!-- Implemented: comprehensive validation for TOC data structure, chapter objects, and required titles -->
- [X] Build chapter order and hierarchy maintenance logic <!-- Implemented: TOC data structure supports hierarchical chapters with level and order fields -->
- [X] Add data integrity checks for TOC updates <!-- Implemented: validates chapter structure, required fields, and data types before updates -->
- [X] Implement versioning for TOC changes <!-- Implemented: version field incremented on each update, preserves generated_at timestamps -->
- [X] Create API endpoints for individual chapter CRUD operations <!-- Implemented: POST /books/{book_id}/chapters (create), GET /books/{book_id}/chapters/{chapter_id} (read), PUT /books/{book_id}/chapters/{chapter_id} (update), DELETE /books/{book_id}/chapters/{chapter_id} (delete), GET /books/{book_id}/chapters (list all) with hierarchical and flat structure support -->
- [X] Add authorization checks for TOC edit operations <!-- Implemented: ownership verification using current_user.clerk_id vs book.owner_id -->
- [ ] Implement rate limiting for TOC update requests <!-- Not implemented: no specific rate limiting for TOC updates -->
- [ ] Create efficient batch update mechanism for multiple changes <!-- Not implemented: current implementation replaces entire TOC structure -->

### Testing Tasks
- [ ] Test drag-and-drop reordering functionality
- [ ] Verify inline editing for chapter titles and descriptions
- [ ] Test chapter/subchapter addition and deletion
- [ ] Validate hierarchy manipulation (promoting/demoting chapters)
- [ ] Test undo/redo functionality for multiple operations
- [ ] Verify API endpoints for TOC updating
- [ ] Test validation and error handling for invalid TOC structures
- [ ] Verify mobile responsiveness of TOC editor
- [ ] Test keyboard navigation and accessibility
- [ ] Create integration tests for complete TOC editing workflow
- [ ] Test performance with large TOC structures (many chapters/subchapters)

### Documentation Tasks
- [ ] Document TOC editing interface features and capabilities
- [ ] Create user guide for TOC editing workflow
- [ ] Document API endpoints for TOC updating
- [ ] Add troubleshooting guide for TOC editing issues
- [ ] Create guidance for effective TOC organization
- [ ] Document keyboard shortcuts and accessibility features
- [ ] Update API documentation with TOC editing endpoints


## User Story 3.4: TOC Persistence

### Frontend Tasks
- [ ] Implement auto-save functionality for TOC changes with appropriate timing
- [ ] Create manual save button with loading and success/error states
- [ ] Build version history interface to view and restore previous TOC versions
- [ ] Implement conflict resolution UI for simultaneous edits
- [ ] Add offline mode detection and synchronization when reconnected
- [ ] Create local storage backup for unsaved changes
- [ ] Implement session recovery after browser/tab crashes
- [ ] Add visual indicators for save status (saved, saving, offline)
- [ ] Create export functionality for TOC (PDF, DOCX formats)
- [ ] Add progress indicators for TOC loading/saving operations
- [ ] Implement warning system for unsaved changes on page navigation
- [ ] Add error handling and recovery UI for failed save operations

### Backend Tasks
- [ ] Enhance TOC database schema to support version history <!-- Not implemented: current schema only stores single version with basic metadata -->
- [ ] Implement API endpoint for retrieving TOC version history <!-- Not implemented: no version history endpoints exist -->
- [ ] Create API endpoint for restoring previous TOC versions <!-- Not implemented: no version restoration functionality -->
- [ ] Build export service for generating TOC documents (PDF, DOCX) <!-- Not implemented: no export service endpoints -->
- [ ] Implement conflict detection and resolution for concurrent edits <!-- Not implemented: no conflict detection mechanism -->
- [ ] Create efficient delta-based TOC update mechanism <!-- Not implemented: current implementation replaces entire TOC structure -->
- [X] Add data validation and sanitization for TOC persistence <!-- Implemented: comprehensive validation using TocItemCreate/Update schemas and validators.py -->
- [ ] Implement automated backups of TOC data <!-- Not implemented: no backup mechanism beyond database persistence -->
- [ ] Create throttling mechanism for frequent save operations <!-- Not implemented: no specific throttling for TOC save operations -->
- [ ] Implement transaction-based TOC updates to prevent partial saves <!-- Partially implemented: uses atomic database updates but no explicit transaction management -->
- [X] Add metadata for TOC versions (timestamp, user, change description) <!-- Implemented: stores generated_at, updated_at, status, and version metadata -->
- [ ] Build cross-book TOC copying functionality <!-- Not implemented: no cross-book operations -->

### Testing Tasks
- [ ] Test auto-save functionality with different change frequencies
- [ ] Verify manual save operation and feedback
- [ ] Test offline mode and synchronization when connection is restored
- [ ] Validate version history retrieval and restoration
- [ ] Test export functionality for different formats
- [ ] Verify session recovery after simulated crashes
- [ ] Test conflict resolution with simultaneous edits
- [ ] Validate data integrity after save operations
- [ ] Test performance with large TOC structures and frequent saves
- [ ] Verify cross-book TOC copying functionality
- [ ] Test throttling mechanism for rapid changes
- [ ] Validate error handling and recovery procedures

### Documentation Tasks
- [ ] Document TOC persistence mechanisms and behaviors
- [ ] Create user guide for version history and restoration
- [ ] Document export functionality and supported formats
- [ ] Add troubleshooting guide for TOC persistence issues
- [ ] Create API documentation for TOC persistence endpoints
- [ ] Document offline capability and synchronization behavior
- [ ] Add guidance for conflict resolution during concurrent editing
- [ ] Document backup and recovery procedures


# Epic 4: Chapter Content Creation
## User Story 4.1: View Chapters in Tabs


## User Story 4.2: Interview-Style Prompts


## User Story 4.3: Input Text or Voice


## User Story 4.4: Generate Draft from Answers


## User Story 4.5: Edit Drafted Text


# Epic 5: Regeneration & Flexibility
## User Story 5.1: Regenerate TOC


## User Story 5.2: Regenerate Prompts


## User Story 5.3: Regenerate Content


# Epic 6: UI & Experience Enhancements
## User Story 6.1: TOC Sidebar


## User Story 6.2: Clean Book/TOC UI


## User Story 6.3: Voice-to-Text Integration


# Epic 7: Optional/Stretch Goals
## User Story 7.1: AI Tons/Style Selector


## User Story 7.2: Chapter Status Labels


# Epic 8: Integrations
## User Story 8.1: Export Book Content


## User Story 8.2: Collaborative Editing


## User Story 8.3: AI Research Assistant


## User Story 8.4: Content Analytics Dashboard


## User Story 8.5: Automatic Backup and Version History


## User Story 8.6: Writing Progress Statistics


## User Story 8.7: Grammar and Style Checking


## User Story 8.8: AI Image Generation for Chapters


## User Story 8.9: Chapter Templates and Patterns


# Epic 9: Application Interaction
## User Story 9.1: Contextual Help and Tutorials


## User Story 9.2: Feedback and Bug Reporting


## User Story 9.3: Integration with External Tools


## User Story 9.4: Mobile Companion App


## User Story 9.5: Book Publishing Assistance


