# Question Responses Auto-Save Feature

## Problem Solved
Users were losing their clarifying question responses if they got interrupted or experienced authentication timeouts. The system was also returning 400 errors saying "question responses are required for TOC generation" even when users had filled out all questions.

## Root Cause
The frontend was not saving question responses to the database. Responses only existed in the component state and were lost on page refresh or interruption.

## Solution Implemented

### 1. Backend API Endpoints Added

#### GET `/books/{book_id}/question-responses`
- Retrieves saved question responses for a book
- Returns empty array if no responses saved
- Used to restore state when user returns

#### PUT `/books/{book_id}/question-responses` (Already existed)
- Saves question responses to database
- Validates response format and completeness
- Updates book readiness status

### 2. Frontend BookClient Functions Added

#### `saveQuestionResponses(bookId, responses)`
- Saves responses to backend database
- Called automatically during typing (auto-save)
- Called before final TOC generation

#### `getQuestionResponses(bookId)`
- Retrieves saved responses from backend
- Used to restore state on component mount
- Handles cases where no responses exist

### 3. ClarifyingQuestions Component Enhanced

#### Auto-Save Functionality
- Saves responses automatically 2 seconds after user stops typing
- Shows save status indicator (saving/saved/auto-save enabled)
- Only saves non-empty responses to avoid clutter

#### State Restoration
- Loads existing responses when component mounts
- Maps responses to questions by index
- Preserves user progress across sessions

#### Enhanced UX
- Visual feedback for save status
- No interruption to user workflow
- Graceful error handling for save failures

## Usage Flow

### New User Experience
1. User starts answering questions
2. After 2 seconds of inactivity, responses auto-save
3. Green checkmark shows "Auto-saved"
4. User can continue or leave and return later

### Returning User Experience
1. Component loads and checks for existing responses
2. Previously answered questions are pre-filled
3. User can continue from where they left off
4. All responses are saved before TOC generation

### Error Recovery
- If save fails, user can still continue (logged but not shown)
- Final save happens before TOC generation
- If final save fails, shows clear error message

## Database Schema

Question responses are stored in the book document:
```json
{
  "question_responses": {
    "responses": [
      {
        "question": "What is the main problem your book addresses?",
        "answer": "User's answer here..."
      }
    ],
    "answered_at": "2025-05-26T10:30:00Z",
    "status": "completed"
  }
}
```

## Testing

Use the `test_question_responses.py` script to verify:
1. Response saving works correctly
2. Response retrieval works correctly  
3. TOC generation uses saved responses
4. End-to-end flow works without errors

## Configuration

No additional configuration required. Feature works automatically with existing authentication and database setup.

## Error Handling

### Frontend
- Auto-save failures are logged but don't interrupt user
- Final save failures show user-friendly error
- Network timeouts are handled gracefully

### Backend
- Validates response format and completeness
- Returns clear error messages for malformed data
- Handles edge cases (empty responses, missing questions)

## Performance Impact

- Minimal: Auto-save only triggers 2 seconds after inactivity
- Debounced to prevent excessive API calls
- Only saves changed responses
- No impact on initial page load
