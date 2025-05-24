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
- [ ]  Build a TOC generation wizard, which takes the book summary and uses AI to generate 3 - 5 clarifying questions in order to generate a draft TOC and save it in the book record. The backend should handle all AI endpoints and pass information via API endpoints.


## User Story 3.3: Edit and Save TOC


## User Story 3.4: TOC Persistence


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


