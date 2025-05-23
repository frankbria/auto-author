# Troubleshooting Guide: Common Book Metadata Issues

This guide provides solutions to common issues encountered when working with book metadata in the Auto Author application.

## Auto-Save Issues

### Problem: Changes aren't being saved automatically

**Possible causes and solutions:**

1. **Invalid data in one or more fields**
   - Look for error messages under form fields
   - Fix the validation errors and try again
   - The auto-save function only works when all fields pass validation

2. **Network connectivity issues**
   - Check your internet connection
   - Look for network error notifications in the application
   - If using a VPN, try disabling it temporarily

3. **Session timeout**
   - Your authentication may have expired
   - Try refreshing the page (your changes may be lost)
   - Log out and log back in if the issue persists

### Problem: "Saving..." indicator never goes away

**Possible causes and solutions:**

1. **Server processing delay**
   - Wait a few more seconds for the operation to complete
   - Refresh the page if it persists for more than a minute

2. **Background request error**
   - Check the browser's developer console for error messages
   - Refresh the page and try again with smaller changes

## Validation Issues

### Problem: "Title is required" error won't go away

**Possible causes and solutions:**

1. **Empty or whitespace-only title**
   - Make sure your title contains actual text characters
   - Remove leading and trailing spaces
   - Check for invisible characters that may have been copied

2. **Form state inconsistency**
   - Try clicking elsewhere in the form to trigger a re-validation
   - Refresh the page and enter the title again

### Problem: Text is being cut off unexpectedly

**Possible causes and solutions:**

1. **Exceeding character limits**
   - Title: 100 characters maximum
   - Subtitle: 200 characters maximum
   - Description: 1000 characters maximum
   - Use a character counter tool if needed

2. **Hidden characters or formatting**
   - Try typing the content directly rather than copy-pasting
   - If copying from another source, paste into a plain text editor first

## Cover Image Issues

### Problem: Cover image not appearing

**Possible causes and solutions:**

1. **Invalid URL format**
   - Ensure the URL begins with `http://` or `https://`
   - Check for typos or missing characters in the URL
   - Verify you're linking directly to the image file, not a webpage containing the image

2. **Image accessibility issues**
   - The image host may require authentication or have restrictions
   - Try opening the URL directly in a new browser tab to check access
   - Some image hosting services block direct linking/hotlinking

3. **Unsupported file format**
   - Ensure you're using a supported format (JPG, PNG, WebP)
   - Convert the image to a supported format if necessary

### Problem: Cover image looks distorted

**Possible causes and solutions:**

1. **Incorrect aspect ratio**
   - Use a 2:3 aspect ratio (e.g., 1600 x 2400 pixels) for best results
   - Resize your image before uploading it

2. **Low resolution**
   - Use an image with at least 1000 pixels on the shortest side
   - Avoid enlarging small images as they will appear pixelated

## Genre and Target Audience Issues

### Problem: Custom genre or audience not appearing in dropdown

**Possible causes and solutions:**

1. **Limited to predefined options**
   - The application currently only supports selecting from the provided options
   - Choose the closest match and provide specifics in the description field

2. **Dropdown not showing all options**
   - Scroll through the dropdown to see all available options
   - Click on the dropdown to ensure it's fully expanded

## Performance Issues

### Problem: Metadata editor loads slowly or is unresponsive

**Possible causes and solutions:**

1. **Large description or metadata**
   - Try breaking up very large text fields
   - Remove unnecessary formatting or special characters

2. **Browser performance**
   - Try clearing your browser cache
   - Close unused browser tabs
   - Try a different browser

### Problem: Changes take too long to save

**Possible causes and solutions:**

1. **Network latency**
   - Check your internet connection speed
   - The auto-save debounce is set to 600ms, so rapid consecutive changes will be batched

2. **Server under high load**
   - Try again during off-peak hours
   - Split large changes into smaller updates

## Data Recovery

### Problem: Lost unsaved changes

**Possible causes and solutions:**

1. **Browser crash or accidental navigation**
   - Unfortunately, if changes weren't auto-saved, they may be lost
   - In future edits, wait for the "Saving..." indicator to confirm your changes are saved
   - Consider drafting longer descriptions in a separate text editor

2. **Session timeout**
   - Keep your session active by interacting with the page periodically
   - Save important changes before taking breaks

## API-Related Issues

### Problem: Receiving "Rate limit exceeded" errors

**Possible causes and solutions:**

1. **Too many requests in a short period**
   - The API has the following rate limits:
     - Creating books: 10 requests per minute
     - Updating books: 15 requests per minute
     - Getting book details: 20 requests per minute
   - Wait a minute before trying again
   - Avoid scripts or automation that make frequent requests

### Problem: "Failed to update book" error

**Possible causes and solutions:**

1. **Server-side validation failure**
   - The backend may have stricter validation rules than the frontend
   - Check the error message for specific details
   - Ensure all fields meet the requirements in the documentation

2. **Permission issues**
   - Verify you have proper permissions for the book you're trying to edit
   - You can only edit books that you own or have been granted editor access to

## Contact Support

If none of these troubleshooting steps resolve your issue:

1. Take a screenshot of the error
2. Note the steps to reproduce the problem
3. Include your browser and operating system information
4. Contact support at support@autoauthor.com

Our support team typically responds within 24 business hours.
