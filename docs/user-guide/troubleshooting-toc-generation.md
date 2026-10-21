# Troubleshooting TOC Generation

This guide provides solutions for common issues encountered during Table of Contents (TOC) generation in Auto Author.

## Common Issues & Solutions

### Summary Not Ready for TOC Generation

#### Symptoms
- "Summary needs improvement" step in the TOC wizard
- Low confidence score
- Improvement suggestions
- A disabled "Complete Book Summary First" button on the book page (no summary saved yet)

#### Causes
1. **Summary too short** (the minimum is 30 words and 150 characters)
2. **Lack of clear themes or structure**
3. **Missing genre or audience indicators**
4. **Overly vague or general content**

#### Solutions
1. **Expand your summary** past the minimum of 30 words and 150 characters (the summary page shows both counts). The maximum is 2,000 characters
2. **Add specific topics** you plan to cover
3. **Mention your target audience** and book's purpose
4. **Clarify the book's genre** and overall approach
5. **Include structural elements** like key sections or themes
6. **Revise based on the suggestions** provided in the readiness check

### AI Service Timeout

#### Symptoms
- An error message instead of the generated TOC
- Generation process stuck at a specific percentage
- Error occurs after waiting more than 60 seconds

#### Causes
1. **Server load issues**
2. **Complex summary requiring extensive processing**
3. **Network connectivity problems**
4. **Temporary AI service disruption**

#### Solutions
1. **Wait 1-2 minutes** then try again
2. **Simplify your summary** if extremely complex
3. **Check your internet connection**
4. **Clear browser cache** and reload the page
5. **Try from a different device or network**

### Empty or Incomplete TOC Results

#### Symptoms
- TOC generates with missing chapters
- Empty sections in the TOC structure
- "Undefined" or placeholder titles
- Missing descriptions 

#### Causes
1. **Ambiguous summary content**
2. **Contradictory information in responses**
3. **Edge case handling in AI service**
4. **Summary topics outside AI's knowledge domain**

#### Solutions
1. **Regenerate the TOC** to get a different structure
2. **Revise answers to clarifying questions** to be more specific
3. **Add more specific themes/topics** to your summary
4. **Check for contradictions** in your summary and responses
5. **If persistent, create a TOC manually** using the edit interface

### Rate Limit Exceeded

#### Symptoms
- A "Rate limit exceeded. Try again in N seconds." message (generation allows 2 requests per 5 minutes)
- Unable to generate a new TOC after multiple attempts

#### Causes
1. **Multiple TOC generation attempts** in short succession
2. **Retrying after a failed generation** counts toward the limit

#### Solutions
1. **Wait 5 minutes** before trying again
2. **Plan your TOC approach** before generating
3. **Use the edit interface** to modify existing TOC rather than regenerating
4. Generating clarifying questions has its own limit of 3 requests per minute

### Clarifying Questions Not Generated

#### Symptoms
- Stuck on "Generating questions..." screen
- Error message when trying to generate questions
- Questions seem generic or unrelated to summary

#### Causes
1. **Summary too vague or short**
2. **Service disruption**
3. **Data format issues**

#### Solutions
1. **Improve your summary** with more specific details
2. **Refresh the page** and try again
3. **Check for special characters** in your summary that might cause issues
4. **Clear cache** and cookies, then retry

### TOC Editing Issues

#### Symptoms
- Changes not saving
- Chapters disappearing when editing
- Unable to add subchapters
- Drag-and-drop reordering not working

#### Causes
1. **Browser compatibility issues**
2. **JavaScript errors**
3. **Temporary session issues**
4. **Invalid data format**

#### Solutions
1. **Save frequently** while making changes
2. **Try a different browser** (Chrome or Firefox recommended)
3. **Clear browser cache** and reload
4. **Check browser console** for specific errors (F12 → Console)
5. **If persistent, copy your TOC data**, refresh, and re-enter

### Generated TOC Not Appropriate

#### Symptoms
- TOC structure doesn't match your vision
- Chapter topics seem irrelevant
- Organization doesn't make sense for your content

#### Causes
1. **Summary lacks clear direction**
2. **Insufficient information in clarifying questions**
3. **AI misinterpreted your genre or approach**

#### Solutions
1. **Try regenerating** the TOC
2. **Revise your summary** to be more specific
3. **Provide clearer answers** to clarifying questions
4. **Use the edit interface** to restructure as needed
5. **Consider manually creating** the TOC structure

### TOC Will Not Save or Load

The TOC editor (**Save & Continue**) saves with `PUT /api/v1/books/{book_id}/toc` and loads with `GET /api/v1/books/{book_id}/toc`. The editor shows one of these messages:

| Message or status | Cause | Solution |
|-------------------|-------|----------|
| "Failed to load the table of contents. Please try again." | The TOC could not be fetched (network, expired session, or server error) | Reload the page; if you were signed out, sign in again |
| "Failed to save the table of contents. Please try again." | Any other save failure | Retry. Your edits stay on the page until you leave it, so copy anything important first |
| "This table of contents changed elsewhere since you opened it." (409) | Another tab or device saved the TOC after you opened it | Reload to get the latest version. Your unsaved edits on this page are discarded |
| "Two chapters share an id, so this table of contents could not be saved." | An older book has duplicate chapter ids | Reload so the repaired chapters load, then redo your changes |
| `Chapter N must have a title` (400) | A chapter's title is empty. `N` counts from 0 | Give every chapter a title |
| "The table of contents is too large to save" (413) | The TOC is over 1,000,000 bytes | Shorten descriptions or remove chapters |

The **Save & Continue** button is disabled while saving and when the TOC has no chapters. A save that succeeds returns you to the book page. If nothing seems to happen, open the browser's Network tab and check the status of the `PUT .../toc` request: a `401` means your session ended (sign in again, see [Authentication](auth.md#signed-out-or-redirected-to-sign-in)) and a `5xx` means the server failed, so wait a moment and retry.

## Advanced Troubleshooting

### Debugging TOC Generation Process

If you're experiencing persistent issues with TOC generation, you can use the browser's developer tools to check for specific error messages:

1. Open your browser's developer tools (F12 or right-click → Inspect)
2. Go to the Console tab
3. Look for error messages related to API calls
4. Check Network tab for failed requests to `/api/v1/books/{book_id}/generate-toc`

Common error responses and meanings:

| Error Message | Meaning | Solution |
|---------------|---------|----------|
| 500 - AI service error | Backend AI service failed | Try again later |
| 429 - Rate limit exceeded | Too many requests | Wait for the time in the message (up to 5 minutes) |
| 400 - Invalid request | No summary saved, or no question responses | Save your summary and answer the questions |
| 400 on saving a summary | Summary over 2,000 characters or under 30 | Change the summary length |

### Recovering from Failed Generation

If TOC generation fails repeatedly:

1. **Create a manual TOC** using the edit interface
2. **Export your summary and responses** (copy to a document)
3. **Contact support** with your book ID and error details
4. **Try from a different device** or network

### Resolving Persistent TOC Structure Issues

If the TOC never seems to match your expectations:

1. Accept any generated TOC to get to the edit interface
2. Completely restructure using the editing tools
3. Consider breaking down your book into smaller, clearer sections
4. Reference the [User Guide](toc-generation.md) for TOC editing tips

## When to Contact Support

Contact support if you experience:

- Repeated failures after trying all troubleshooting steps
- Data loss during TOC generation or editing
- Persistent error messages not covered in this guide
- Issues with TOC structure after editing and saving

Provide the following information:
- Your book ID
- Exact error messages
- Steps you've already tried
- Screenshots of any error messages
- Time and date of the issue

## Related Documentation

- [User Guide for TOC Generation](toc-generation.md)
- [API TOC Endpoints](../api/toc.md)
