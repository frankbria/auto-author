# Troubleshooting TOC Persistence Issues

This guide helps resolve common issues related to Table of Contents (TOC) persistence, saving, and loading in Auto Author.

## Common TOC Persistence Issues

### Save Button Not Working

#### Symptoms
- Save button appears disabled or unresponsive
- "Saving..." state never completes
- No feedback after clicking save

#### Possible Causes & Solutions

**1. Network Connectivity**
- **Cause**: Poor or interrupted internet connection
- **Solution**: Check your network connection and try again
- **Test**: Try refreshing the page or accessing other online services

**2. Authentication Issues**
- **Cause**: Session expired or authentication token invalid
- **Solution**: Refresh the page and log in again
- **Prevention**: Avoid keeping the page open for extended periods without activity

**3. TOC Validation Errors**
- **Cause**: Invalid TOC structure or missing required fields
- **Solution**: Ensure all chapters have titles and valid structure
- **Check**: Look for empty chapter titles or malformed hierarchy

**4. Server Errors**
- **Cause**: Backend service temporary unavailable
- **Solution**: Wait a few minutes and try again
- **Escalation**: If persistent, contact support with error details

### TOC Changes Not Persisting

#### Symptoms
- Changes appear to save but revert when page reloads
- Edits lost after navigating away from page
- TOC returns to previous state unexpectedly

#### Troubleshooting Steps

**1. Check Save Confirmation**
- Look for "Saved successfully" message after making changes
- Green checkmark or success indicator should appear
- If no confirmation appears, the save may have failed

**2. Verify TOC Structure**
- Ensure all chapters have titles (cannot be empty)
- Check that hierarchy levels are consistent
- Verify no duplicate chapter IDs exist

**3. Clear Browser Cache**
- Clear browser cache and cookies for the application
- Refresh the page and try editing again
- This resolves cached data conflicts

**4. Test in Incognito/Private Mode**
- Open the application in a private browsing window
- If it works there, clear your browser data
- This isolates browser-specific issues

### Loading Issues

#### Symptoms
- TOC fails to load when opening a book
- Spinning loader never completes
- "Failed to load TOC" error message

#### Resolution Steps

**1. Refresh the Page**
- Simple page refresh often resolves temporary loading issues
- Use Ctrl+F5 (or Cmd+Shift+R) for hard refresh

**2. Check Book Status**
- Ensure the book exists and you have access permissions
- Verify you're logged into the correct account

**3. Network Troubleshooting**
- Check internet connectivity
- Try accessing other parts of the application
- Disable VPN if using one

**4. Browser Compatibility**
- Ensure you're using a supported browser version
- Try accessing from a different browser
- Update your browser to the latest version

### Data Corruption or Loss

#### Symptoms
- TOC structure appears scrambled or incorrect
- Chapters appear in wrong order
- Missing chapters or subchapters

#### Recovery Steps

**1. Check Version History** (Future Feature)
- Look for "Version History" or "Restore" options
- Select a previous version that was working correctly
- Note: This feature is planned for v2.0+

**2. Restore from Backup** (Current Method)
- TOC data is automatically backed up with each save
- Contact support to restore from backup if needed
- Provide your book ID and approximate time of last known good state

**3. Manual Reconstruction**
- If other methods fail, manually recreate the TOC structure
- Use the TOC editing interface to rebuild your content
- Consider starting from a previously exported version if available

### Performance Issues

#### Symptoms
- Slow saving or loading of large TOCs
- Interface becomes unresponsive during operations
- Timeout errors during save operations

#### Optimization Steps

**1. Reduce TOC Complexity**
- Consider breaking very large books into smaller sections
- Limit subchapter nesting to 3-4 levels maximum
- Keep chapter descriptions concise

**2. Optimize Network**
- Use a stable, high-speed internet connection
- Avoid saving during peak network usage times
- Close other applications using bandwidth

**3. Browser Performance**
- Close unnecessary browser tabs
- Restart your browser if it's been running for a long time
- Ensure sufficient system memory is available

## Error Messages and Solutions

### "Failed to save TOC changes"
- **Immediate Action**: Try saving again in 30 seconds
- **If Persistent**: Check network connection and authentication
- **Prevention**: Save frequently during editing sessions

### "TOC structure validation failed"
- **Cause**: Invalid chapter structure or missing required fields
- **Solution**: Ensure all chapters have titles and proper hierarchy
- **Check**: Look for empty fields or malformed chapter structure

### "Session expired, please log in again"
- **Action**: Refresh the page and log in
- **Prevention**: Save work frequently and avoid long idle periods
- **Note**: Unsaved changes may be lost

### "Server temporarily unavailable"
- **Action**: Wait 2-3 minutes and try again
- **If Continued**: Check our status page or contact support
- **Workaround**: Continue editing offline and save when service resumes

## Best Practices for TOC Persistence

### Saving Frequency
- Save your work every 10-15 minutes during active editing
- Save immediately after major structural changes
- Use the manual save button rather than relying on auto-save (not yet implemented)

### Data Validation
- Ensure all chapters have meaningful titles
- Keep chapter descriptions under 500 characters for optimal performance
- Maintain consistent hierarchy levels

### Session Management
- Avoid keeping editing sessions open for more than 2 hours
- Log out and log back in if you experience any unusual behavior
- Use a single browser tab for editing to avoid conflicts

### Network Considerations
- Use a stable internet connection for editing
- Avoid editing during known network maintenance windows
- Save before switching networks (e.g., WiFi to mobile)

## Advanced Troubleshooting

### Browser Developer Tools
If you're comfortable with technical debugging:

1. **Open Developer Tools** (F12 in most browsers)
2. **Check Console Tab** for JavaScript errors
3. **Check Network Tab** for failed API requests
4. **Look for Error Details** in red entries

Common error patterns:
- `401 Unauthorized`: Authentication issues
- `403 Forbidden`: Permission problems
- `500 Internal Server Error`: Server-side issues
- `Timeout` or `Network Error`: Connectivity problems

### API Endpoint Status
Monitor these API endpoints for TOC persistence:
- `GET /api/v1/books/{book_id}/toc` - Loading TOC data
- `PUT /api/v1/books/{book_id}/toc` - Saving TOC changes

### Local Storage Issues
Clear local storage if experiencing persistent issues:
1. Open Developer Tools
2. Go to Application or Storage tab
3. Clear localStorage for the Auto Author domain
4. Refresh the page and try again

## Getting Help

### Self-Service Options
1. **Check Application Status**: Look for service status updates
2. **Review Recent Changes**: Consider if you made changes that might cause issues
3. **Try Different Browser**: Test in an alternative browser
4. **Check Documentation**: Review related user guides

### Contacting Support
When contacting support, please provide:

**Essential Information**:
- Your book ID (found in the URL)
- Exact error message (screenshot preferred)
- Steps you were taking when the issue occurred
- Browser and version you're using
- Time when the issue occurred

**Helpful Details**:
- Size and complexity of your TOC
- Recent changes you made to the TOC
- Whether this is a new or recurring issue
- Any browser extensions that might interfere

## Related Documentation

- [TOC Generation User Guide](user-guide-toc-generation.md)
- [API TOC Endpoints](api-toc-endpoints.md)
- [TOC Generation Troubleshooting](troubleshooting-toc-generation.md)
- [User Stories - TOC Persistence](../user-stories.md#user-story-34-toc-persistence)

## Prevention Tips

### Regular Maintenance
- Clear browser cache monthly
- Keep your browser updated
- Log out and back in weekly during heavy usage periods

### Good Editing Practices
- Make incremental changes rather than large restructures
- Test save functionality after major edits
- Keep a backup of complex TOC structures in a separate document

### Environment Optimization
- Use a dedicated browser profile for Auto Author
- Disable unnecessary browser extensions
- Ensure adequate system resources during editing sessions

---

*This troubleshooting guide covers MVP features. Advanced features like auto-save, version history, and offline sync will be documented in future releases.*
