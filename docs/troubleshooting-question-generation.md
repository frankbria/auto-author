# Troubleshooting Guide for Question Generation Issues

## Overview
This guide helps resolve common issues with the AI-powered question generation system, including generation failures, quality problems, and performance issues.

## Common Issues and Solutions

### Question Generation Failures

#### Issue: No Questions Generated
**Symptoms:**
- Generate button doesn't work
- Empty response or error message
- Loading indicator never completes

**Possible Causes & Solutions:**

1. **Chapter has no title**
   - Ensure the chapter has a descriptive title
   - Title should be at least 3 characters long
   - Avoid generic titles like "Chapter 1"

2. **Network connectivity issues**
   - Check internet connection
   - Verify API endpoint is accessible
   - Try refreshing the page and attempting again

3. **Authentication problems**
   - Log out and log back in
   - Clear browser cache and cookies
   - Verify user permissions for the book

4. **Server overload**
   - Try generating fewer questions (5-10 instead of 15-20)
   - Wait a few minutes and try again
   - Generate questions during off-peak hours

#### Issue: Generation Takes Too Long
**Symptoms:**
- Request times out after 30+ seconds
- Browser shows "loading" indefinitely

**Solutions:**
1. **Reduce question count**
   ```json
   // Instead of:
   { "count": 20 }
   
   // Try:
   { "count": 8 }
   ```

2. **Simplify generation parameters**
   ```json
   // Instead of complex request:
   {
     "count": 15,
     "difficulty": "hard",
     "focus": ["character", "plot", "setting", "theme"]
   }
   
   // Try simpler:
   {
     "count": 10,
     "difficulty": "medium"
   }
   ```

3. **Check chapter content length**
   - Very long chapters (>10,000 words) take longer to process
   - Consider generating questions for specific sections

### Question Quality Issues

#### Issue: Questions Are Too Generic
**Symptoms:**
- Questions like "What happens in this chapter?"
- Repetitive question patterns
- No specific references to chapter content

**Solutions:**
1. **Improve chapter title specificity**
   ```
   // Instead of:
   "Chapter 3"
   
   // Use:
   "Sarah's Discovery of the Hidden Journal"
   ```

2. **Add chapter content before generating**
   - Even a brief outline helps
   - Include key characters, events, or themes
   - Add setting details

3. **Use focused question types**
   ```json
   {
     "count": 10,
     "focus": ["character", "setting"]  // More specific than all types
   }
   ```

4. **Rate poor questions and regenerate**
   - Give low ratings (1-2 stars) to generic questions
   - Provide specific feedback
   - Use regeneration with "preserve_responses: true"

#### Issue: Questions Don't Match Genre
**Symptoms:**
- Romance questions for a technical manual
- Fantasy questions for a business book
- Inappropriate difficulty level

**Solutions:**
1. **Verify book metadata**
   - Check genre setting in book details
   - Update target audience if needed
   - Ensure book description is accurate

2. **Use genre-specific focus**
   ```json
   // For technical books:
   { "focus": ["research"] }
   
   // For fiction:
   { "focus": ["character", "plot", "setting"] }
   
   // For non-fiction:
   { "focus": ["theme", "research"] }
   ```

#### Issue: Questions Are Too Easy/Hard
**Symptoms:**
- Questions don't challenge the writer appropriately
- Difficulty doesn't match writing experience

**Solutions:**
1. **Adjust difficulty setting**
   ```json
   {
     "difficulty": "easy",    // For new writers
     "difficulty": "medium",  // For experienced writers
     "difficulty": "hard"     // For professional authors
   }
   ```

2. **Review and rate questions**
   - Rate difficulty appropriately
   - System learns from your feedback
   - Regenerate with better parameters

### Response and Interface Issues

#### Issue: Can't Save Responses
**Symptoms:**
- Save button doesn't work
- Responses disappear after typing
- Error messages when saving

**Solutions:**
1. **Check response length**
   - Ensure response has at least 1 character
   - Verify no special characters causing issues
   - Try shorter responses first

2. **Browser issues**
   - Disable browser extensions temporarily
   - Clear browser cache
   - Try incognito/private mode

3. **Network problems**
   - Check internet connection stability
   - Try saving smaller portions at a time
   - Use auto-save feature (saves every 30 seconds)

#### Issue: Auto-Save Not Working
**Symptoms:**
- Changes lost when navigating away
- No save indicators shown
- Manual save required constantly

**Solutions:**
1. **Verify auto-save settings**
   - Check if feature is enabled in preferences
   - Look for save indicators (usually a small dot or "saving..." text)

2. **Browser compatibility**
   - Update to latest browser version
   - Enable JavaScript
   - Allow cookies for the domain

3. **Network stability**
   - Ensure stable internet connection
   - Try manual saves (Ctrl+S) as backup

### Performance Issues

#### Issue: Slow Question Loading
**Symptoms:**
- Questions take long time to appear
- Page feels sluggish
- Timeouts when switching between questions

**Solutions:**
1. **Reduce questions per page**
   - Use pagination with smaller page sizes
   - Filter questions by type or status
   - Load questions on demand

2. **Browser optimization**
   - Close unnecessary tabs
   - Clear browser cache
   - Restart browser

3. **Data optimization**
   ```javascript
   // Request only necessary fields
   fetch('/api/questions?fields=id,question_text,type')
   ```

#### Issue: High Memory Usage
**Symptoms:**
- Browser becomes slow or crashes
- Computer fan runs constantly
- Other applications slow down

**Solutions:**
1. **Limit concurrent operations**
   - Don't generate questions for multiple chapters simultaneously
   - Close unused tabs
   - Work on one chapter at a time

2. **Optimize response handling**
   - Don't keep all responses loaded in memory
   - Use pagination effectively
   - Clear completed work from active memory

## Error Messages and Codes

### Common Error Messages

#### "Generation failed: Invalid parameters"
**Cause:** Request parameters don't meet API requirements
**Solution:**
- Check count is between 1-50
- Verify difficulty is "easy", "medium", or "hard"
- Ensure focus types are valid

#### "Insufficient content for generation"
**Cause:** Chapter lacks enough context for quality questions
**Solution:**
- Add a descriptive chapter title
- Include brief chapter outline or summary
- Provide character names or key themes

#### "Rate limit exceeded"
**Cause:** Too many generation requests in short time
**Solution:**
- Wait 5-10 minutes before trying again
- Reduce generation frequency
- Consider generating fewer questions at once

#### "Authentication failed"
**Cause:** User session expired or invalid
**Solution:**
- Log out and log back in
- Clear browser cookies
- Verify account permissions

### API Error Codes
| Code | Meaning | Solution |
|------|---------|----------|
| 400 | Bad Request | Check request parameters |
| 401 | Unauthorized | Re-authenticate |
| 403 | Forbidden | Verify permissions |
| 404 | Not Found | Check book/chapter exists |
| 429 | Rate Limited | Wait and retry |
| 500 | Server Error | Try again later or contact support |

## Debugging Steps

### Basic Troubleshooting Checklist
1. ✓ Chapter has descriptive title
2. ✓ Internet connection is stable
3. ✓ User is logged in properly
4. ✓ Browser is up to date
5. ✓ JavaScript is enabled
6. ✓ No browser extensions interfering
7. ✓ Request parameters are valid

### Advanced Debugging

#### Enable Developer Tools
1. Open browser developer tools (F12)
2. Go to Network tab
3. Attempt question generation
4. Look for failed requests or error responses
5. Check Console tab for JavaScript errors

#### Check Request Details
```javascript
// Example of debugging request in browser console
fetch('/api/v1/books/123/chapters/456/generate-questions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + localStorage.getItem('token')
  },
  body: JSON.stringify({
    count: 10,
    difficulty: 'medium'
  })
}).then(r => r.json()).then(console.log);
```

## Prevention Best Practices

### Before Generating Questions
1. **Prepare chapter context**
   - Write clear, descriptive titles
   - Add basic chapter outlines
   - Include key character names

2. **Set realistic expectations**
   - Start with smaller question counts
   - Use appropriate difficulty levels
   - Focus on specific question types

3. **Optimize environment**
   - Use stable internet connection
   - Close unnecessary browser tabs
   - Update browser to latest version

### During Generation
1. **Monitor progress**
   - Watch for error messages
   - Don't refresh page during generation
   - Be patient with processing time

2. **Save work frequently**
   - Use auto-save feature
   - Manual save important responses
   - Export responses periodically

### After Generation
1. **Review and rate questions**
   - Provide honest feedback
   - Rate question relevance
   - Note improvement suggestions

2. **Optimize for future use**
   - Learn from successful generations
   - Document effective parameters
   - Build on previous responses

## Getting Help

### Self-Service Resources
- Check status page for system-wide issues
- Review API documentation for parameter details
- Search knowledge base for similar issues

### Contact Support
If issues persist after following this guide:

1. **Gather information:**
   - Browser type and version
   - Error messages (exact text)
   - Steps to reproduce issue
   - Screenshots if helpful

2. **Include request details:**
   - Book ID and chapter ID
   - Generation parameters used
   - Timestamp of issue

3. **Contact methods:**
   - Support ticket system
   - Email: support@example.com
   - Emergency: Live chat (for critical issues)

---

*For additional help with the question system, see [User Guide for Answering Questions](user-guide-question-answering.md) and [API Documentation](api-question-endpoints.md).*
