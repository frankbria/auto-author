# Troubleshooting: Summary Input Issues

This guide helps resolve common problems encountered when using the summary input feature in Auto Author.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Text Input Issues](#text-input-issues)
3. [Voice-to-Text Problems](#voice-to-text-problems)
4. [Auto-save Issues](#auto-save-issues)
5. [Validation and Requirements](#validation-and-requirements)
6. [Browser Compatibility](#browser-compatibility)
7. [Network and Connectivity](#network-and-connectivity)
8. [Advanced Troubleshooting](#advanced-troubleshooting)

## Quick Diagnostics

Before diving into specific issues, run through this quick checklist:

### ✅ Basic Checks
- [ ] Are you logged in to your Auto Author account?
- [ ] Is your internet connection stable?
- [ ] Are you using a supported browser (Chrome, Firefox, Safari, Edge)?
- [ ] Have you refreshed the page recently?
- [ ] Is the summary page fully loaded?

### ✅ Summary Requirements
- [ ] Does your summary have at least 30 words?
- [ ] Is your summary under 2,000 characters?
- [ ] Does your summary contain actual content (not just spaces)?
- [ ] Have you included meaningful description of your book?

## Text Input Issues

### Problem: Can't Type in Summary Text Area

**Symptoms:**
- Text area appears grayed out or disabled
- Cursor doesn't appear when clicking in text area
- Keyboard input doesn't register

**Solutions:**

1. **Check if voice recording is active**
   - Look for "Listening..." indicator
   - Click "Stop Listening" if voice input is active
   - Text input is disabled during voice recording

2. **Refresh the page**
   - Press `Ctrl+R` (Windows) or `Cmd+R` (Mac)
   - Wait for page to fully load before trying again

3. **Clear browser focus**
   - Click outside the text area, then click back in
   - Try pressing `Tab` key to cycle through elements

4. **Check browser console for errors**
   - Press `F12` to open developer tools
   - Look for JavaScript errors in the Console tab
   - Refresh page if errors are present

### Problem: Text Disappears While Typing

**Symptoms:**
- Text vanishes after typing
- Content reverts to previous version
- Work is lost unexpectedly

**Solutions:**

1. **Check auto-save conflicts**
   - Look for "Saving..." indicator
   - Wait for save to complete before continuing
   - Avoid rapid typing during save operations

2. **Disable browser auto-fill**
   - Turn off form auto-completion in browser settings
   - Some auto-fill features can interfere with text areas

3. **Check revision history**
   - Your content might be saved in a previous revision
   - Look for revision history options in the interface

### Problem: Character Count Not Updating

**Symptoms:**
- Character/word count shows incorrect numbers
- Count doesn't change when typing
- Counter shows 0/2000 despite having text

**Solutions:**

1. **Refresh the page**
   - Counter will reset and recalculate correctly

2. **Clear and re-enter text**
   - Select all text (`Ctrl+A`) and cut (`Ctrl+X`)
   - Paste back in (`Ctrl+V`) to trigger recalculation

3. **Check for invisible characters**
   - Copy text to a plain text editor
   - Remove any special formatting or hidden characters

## Voice-to-Text Problems

### Problem: "Speak Summary" Button Doesn't Work

**Symptoms:**
- Button doesn't respond to clicks
- No microphone permission prompt appears
- "Listening..." indicator never shows

**Solutions:**

1. **Check microphone permissions**
   - Look for microphone icon in browser address bar
   - Click the icon and set permissions to "Allow"
   - Refresh page after changing permissions

2. **Verify browser support**
   - Voice input requires Chrome, Firefox, Safari, or Edge
   - Internet Explorer and older browsers are not supported
   - Update your browser to the latest version

3. **Test microphone hardware**
   - Try using microphone in other applications
   - Check if microphone is muted or volume is too low
   - Ensure correct microphone is selected in system settings

### Problem: Microphone Permission Denied

**Symptoms:**
- Browser shows "Permission denied" error
- Microphone icon in address bar shows blocked status
- Voice input fails immediately

**Solutions:**

1. **Grant microphone permissions in browser**

   **Chrome:**
   - Click lock icon next to address bar
   - Set "Microphone" to "Allow"
   - Refresh the page

   **Firefox:**
   - Click shield icon next to address bar
   - Enable microphone permissions
   - Refresh the page

   **Safari:**
   - Safari > Preferences > Websites > Microphone
   - Find Auto Author site and set to "Allow"

2. **Check system permissions (macOS)**
   - System Preferences > Security & Privacy > Privacy
   - Select "Microphone" from list
   - Ensure your browser is checked and allowed

3. **Reset site permissions**
   - Clear all site data for Auto Author
   - Navigate back to the site
   - Grant permissions when prompted

### Problem: Voice Transcription is Inaccurate

**Symptoms:**
- Spoken words appear incorrectly
- Punctuation is missing or wrong
- Names or technical terms are misspelled

**Solutions:**

1. **Improve speaking conditions**
   - Move to a quieter environment
   - Speak closer to the microphone
   - Speak more slowly and clearly
   - Pause between sentences

2. **Use voice punctuation commands**
   - Say "period" for .
   - Say "comma" for ,
   - Say "question mark" for ?
   - Say "new paragraph" for line breaks

3. **Edit after transcription**
   - Always review transcribed text
   - Manually correct any errors
   - Consider typing technical terms

4. **Check microphone quality**
   - Use a dedicated microphone if available
   - Reduce background noise
   - Test with other voice applications

### Problem: Voice Recording Stops Unexpectedly

**Symptoms:**
- Recording stops before you finish speaking
- "Listening..." indicator disappears suddenly
- Partial transcription appears

**Solutions:**

1. **Speak continuously**
   - Avoid long pauses (more than 2-3 seconds)
   - Say "um" or "uh" to maintain audio input
   - Record shorter segments if needed

2. **Check timeout settings**
   - Voice recognition has automatic timeout
   - Click "Speak Summary" again to continue
   - Break long content into multiple recordings

3. **Monitor network connection**
   - Unstable internet can interrupt recording
   - Ensure strong Wi-Fi or cellular signal
   - Try again with better connectivity

## Auto-save Issues

### Problem: Auto-save Not Working

**Symptoms:**
- "Saving..." indicator never appears
- Changes are lost when refreshing page
- No save confirmation messages

**Solutions:**

1. **Check internet connectivity**
   - Verify you can load other websites
   - Look for connectivity indicators in browser
   - Try saving manually if available

2. **Wait for typing to finish**
   - Auto-save triggers 600ms after stopping typing
   - Don't navigate away immediately after typing
   - Look for save confirmation before leaving page

3. **Clear browser cache**
   - Clear cache and cookies for Auto Author
   - Reload page and try again
   - This resolves many JavaScript issues

### Problem: Local Storage Full

**Symptoms:**
- Warning about storage space
- Auto-save fails silently
- Browser performance issues

**Solutions:**

1. **Clear local storage**
   - Browser settings > Privacy > Clear browsing data
   - Select "Local storage" or "Site data"
   - Keep login data if possible

2. **Free up browser storage**
   - Close unnecessary tabs
   - Clear downloads and browsing history
   - Remove unused browser extensions

## Validation and Requirements

### Problem: "Generate TOC" Button Disabled

**Symptoms:**
- Button appears grayed out
- Can't proceed to table of contents generation
- Button doesn't respond to clicks

**Solutions:**

1. **Check minimum word count**
   - Summary must have at least 30 words
   - Look at word counter in bottom right
   - Add more content to reach minimum

2. **Verify meaningful content**
   - Summary must contain actual descriptive text
   - Avoid placeholder text or test content
   - Include book topic, audience, and key themes

3. **Wait for validation**
   - System needs time to validate content
   - Button may enable after a few seconds
   - Try typing additional content

### Problem: Validation Errors

**Symptoms:**
- Red error messages appear
- Content marked as invalid
- Save operations fail

**Solutions:**

1. **Review content length**
   - Maximum 2,000 characters allowed
   - Check character counter
   - Edit content to fit within limits

2. **Check for problematic content**
   - Remove excessive special characters
   - Avoid repeated punctuation (!!!, ???)
   - Ensure content is appropriate

3. **Verify required fields**
   - Summary cannot be completely empty
   - Must contain alphabetic characters
   - Numbers and symbols alone are insufficient

## Browser Compatibility

### Supported Browsers

| Browser | Voice Input | Text Input | Auto-save |
|---------|-------------|------------|-----------|
| Chrome 70+ | ✅ | ✅ | ✅ |
| Firefox 65+ | ✅ | ✅ | ✅ |
| Safari 14+ | ✅ | ✅ | ✅ |
| Edge 79+ | ✅ | ✅ | ✅ |
| Internet Explorer | ❌ | ⚠️ | ❌ |

### Browser-Specific Issues

#### Chrome
- **Issue**: Voice input may not work in incognito mode
- **Solution**: Use regular browsing mode or enable microphone in incognito

#### Firefox
- **Issue**: Auto-save might be slower than other browsers
- **Solution**: Wait longer for save confirmation

#### Safari
- **Issue**: Voice commands for punctuation may not work
- **Solution**: Manually add punctuation after transcription

#### Mobile Browsers
- **Voice input**: Generally works well on mobile
- **Text editing**: May have different behavior than desktop
- **Auto-save**: Might be affected by background app restrictions

## Network and Connectivity

### Slow Internet Connection

**Symptoms:**
- Voice transcription takes a long time
- Auto-save appears to hang
- Page loads slowly

**Solutions:**

1. **Use text input instead**
   - Text typing doesn't require internet
   - Switch to typing for better experience
   - Use voice input when connection improves

2. **Optimize connection**
   - Close other bandwidth-heavy applications
   - Move closer to Wi-Fi router
   - Switch to cellular data if available

3. **Work offline**
   - Text changes are cached locally
   - Continue working without voice features
   - Changes will sync when connection improves

### Intermittent Connectivity

**Symptoms:**
- Auto-save works sometimes but not always
- Voice input works inconsistently
- Error messages about network issues

**Solutions:**

1. **Enable local backup**
   - Copy important content to clipboard regularly
   - Use browser's back button carefully
   - Consider working in external text editor first

2. **Monitor connection**
   - Check Wi-Fi signal strength
   - Restart router if necessary
   - Contact internet service provider if issues persist

## Advanced Troubleshooting

### Browser Developer Tools

Use browser developer tools for advanced diagnosis:

1. **Open Developer Tools**
   - Press `F12` or `Ctrl+Shift+I`
   - Look for errors in Console tab
   - Check Network tab for failed requests

2. **Common JavaScript Errors**
   - `SpeechRecognition is not defined`: Browser doesn't support voice input
   - `Permission denied`: Microphone access blocked
   - `Network error`: Connectivity or server issues

3. **Local Storage Check**
   - Application tab > Local Storage
   - Look for Auto Author data
   - Clear if corrupted (data may be lost)

### Reset and Recovery

If all else fails:

1. **Complete browser reset**
   - Clear all Auto Author site data
   - Disable browser extensions temporarily
   - Try in incognito/private mode

2. **Different device test**
   - Try on different computer or mobile device
   - Helps identify if issue is device-specific
   - Use different network if possible

3. **Contact support**
   - Use in-app help system
   - Provide specific error messages
   - Include browser version and operating system

### Data Recovery

If you've lost summary content:

1. **Check revision history**
   - Look for previous versions in the interface
   - Content might be saved in earlier revision

2. **Browser history**
   - Back button might restore previous state
   - Don't refresh page before trying this

3. **Local storage**
   - Developer tools > Application > Local Storage
   - Look for auto-saved content
   - May be recoverable by support team

## Prevention Tips

### Best Practices
- **Save frequently**: Don't rely only on auto-save
- **Use stable internet**: Avoid public Wi-Fi for important work
- **Keep browser updated**: Latest versions have fewer issues
- **Test voice input**: Try a few words before starting long recordings
- **Back up content**: Copy important text to external documents

### Environment Setup
- **Quiet space**: Use voice input in noise-free environment
- **Good microphone**: Invest in quality audio equipment
- **Stable power**: Ensure laptop is plugged in for long sessions
- **Multiple devices**: Have backup device available if possible

## Getting Additional Help

### In-App Support
- Look for help button or chat icon in the application
- Use contextual help available on summary page
- Check for help tooltips and guided tours

### Community Resources
- User forum and community discussions
- Video tutorials and walkthroughs
- FAQ section in main documentation

### Technical Support
- Contact support team for persistent issues
- Provide detailed description of problem
- Include screenshots or recordings if helpful
- Mention browser version and operating system

## Related Documentation

- [User Guide: Summary Input and Voice-to-Text](user-guide-summary-input.md)
- [Summary Input Requirements and Best Practices](summary-input-requirements.md)
- [API Endpoints: Summary Operations](api-summary-endpoints.md)
- [Browser Compatibility Guide](browser-compatibility.md)

---

Last updated: May 17, 2025
