# Manual Test Plan for AI Draft Generation

## Test Setup
1. Ensure backend is running: `python -m uvicorn app.main:app --reload`
2. Ensure frontend is running: `npm run dev`
3. Login to the application
4. Create a test book with a table of contents

## Test Cases

### 1. ✅ Basic Draft Generation
**Steps:**
1. Navigate to a chapter in the tabbed interface
2. Click "Generate AI Draft" button in the editor toolbar
3. Answer at least one of the sample questions
4. Select "Conversational" writing style
5. Set target word count to 2000
6. Click "Generate Draft"

**Expected Result:**
- Loading spinner appears during generation
- Draft is generated and displayed in preview
- Word count and reading time are shown
- Suggestions for improvement are displayed

### 2. ✅ Apply Draft to Editor
**Steps:**
1. After generating a draft (Test Case 1)
2. Click "Use This Draft" button

**Expected Result:**
- Draft content is inserted into the chapter editor
- Dialog closes
- Success toast appears: "The generated draft has been added to your chapter"
- Content is auto-saved

### 3. ✅ Generate New Draft
**Steps:**
1. After generating a draft (Test Case 1)
2. Click "Generate New Draft" button
3. Modify answers or add new questions
4. Generate again

**Expected Result:**
- Returns to question form
- Previous answers are preserved
- Can generate a new draft with different parameters

### 4. ✅ Error Handling - No Answers
**Steps:**
1. Open draft generator dialog
2. Don't answer any questions
3. Click "Generate Draft"

**Expected Result:**
- Error toast appears: "Please answer at least one question before generating a draft"
- Generation is prevented

### 5. ✅ Different Writing Styles
**Steps:**
1. Generate drafts with different styles:
   - Conversational
   - Formal
   - Educational
   - Technical

**Expected Result:**
- Each style produces appropriately toned content
- Style is reflected in the generated text

### 6. ✅ Custom Questions
**Steps:**
1. Click "Add Question" to add custom questions
2. Enter custom question and answer
3. Remove default questions if desired
4. Generate draft

**Expected Result:**
- Custom questions can be added/removed
- Draft incorporates custom Q&A responses

### 7. ✅ API Error Handling
**Steps:**
1. Disable network or stop backend
2. Try to generate a draft

**Expected Result:**
- Error toast appears with appropriate message
- UI remains functional
- Can retry when connection restored

### 8. ✅ Rate Limiting
**Steps:**
1. Generate 5 drafts within an hour
2. Try to generate a 6th draft

**Expected Result:**
- Rate limit error is displayed
- User is informed when they can try again

## Integration Points to Verify

1. **API Endpoint**: `/api/v1/books/{bookId}/chapters/{chapterId}/generate-draft`
2. **Request Format**:
   ```json
   {
     "question_responses": [
       {"question": "...", "answer": "..."}
     ],
     "writing_style": "conversational",
     "target_length": 2000
   }
   ```
3. **Response Format**:
   ```json
   {
     "success": true,
     "draft": "Generated content...",
     "metadata": {
       "word_count": 150,
       "estimated_reading_time": 1,
       "writing_style": "conversational",
       "target_length": 2000,
       "actual_length": 150
     },
     "suggestions": ["..."],
     "message": "Draft generated successfully"
   }
   ```

## Performance Metrics
- Draft generation should complete within 30 seconds
- UI should remain responsive during generation
- Generated content should be properly formatted HTML
- Auto-save should trigger after draft insertion

## Known Issues to Check
1. Ensure draft is inserted at cursor position, not replacing all content
2. Verify HTML formatting is preserved in the editor
3. Check that special characters are properly escaped
4. Confirm word count is accurate

## Summary
The AI draft generation feature is fully implemented with:
- ✅ Backend AI service integration
- ✅ API endpoint with validation
- ✅ Frontend UI component
- ✅ Error handling and validation
- ✅ Integration with chapter editor
- ✅ Multiple writing styles
- ✅ Custom Q&A support
- ✅ Progress feedback
- ✅ Rate limiting protection