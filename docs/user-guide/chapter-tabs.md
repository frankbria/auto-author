# User Guide: Chapter Tab Navigation and Management

## Overview
The chapter tab interface allows you to quickly switch between chapters, manage open tabs, and keep your writing workflow organized.

## Opening and Navigating Tabs
- Each chapter in your table of contents has a tab. Click a tab to make it active.
- On a desktop screen the tabs are listed vertically on the left. At 768px wide and below a mobile tab layout is used.
- Use keyboard shortcuts (see below) for fast navigation.

## Managing Tabs
- **Reorder Tabs**: Drag and drop tabs to change their order.
- **Close Tabs**: Click the close button (x) on the tab.
- **Chapter options**: Click the "Chapter options" button (three dots) to open a menu for the active chapter. It has Edit, Mark as Draft, Mark as In Progress, Mark as Completed, Mark as Published and Delete.
- **Tab Overflow**: If you open many chapters, use the scroll bar or overflow menu to access hidden tabs.

## Tab Status Indicators
- Each tab shows a colored dot for the chapter's status: draft, in progress, completed or published.
- Hover over a tab for a tooltip with the title, status, word count and reading time.

## Persistence
- Your open tabs and their order are saved automatically and restored on your next visit.

## Keyboard
- **Ctrl+1 to Ctrl+9**: switch to the 1st to 9th tab, counted in the order shown in the tab bar. Nothing happens if there is no tab at that position.
- **Tab, then Enter or Space**: move focus to a tab and open it. The close button on each tab works the same way.

These are the only tab shortcuts. Shortcuts such as Ctrl+Tab, Ctrl+W or Ctrl+Shift+T are the browser's own and do not act on chapter tabs.

## Accessibility
- Tabs are focusable, show a visible focus ring, and have labels for screen readers ("Open chapter ...", "Close chapter").
- Tab details are available in a tooltip.

## Troubleshooting

| Problem | Likely cause | What to do |
|---------|--------------|------------|
| Tabs are not restored on the next visit | The saved tab state could not be stored (browser storage blocked or cleared, or you are signed out) | Make sure you are signed in and the site may use local storage. Tab state is saved to your browser and to your account about a second after each change; the newer copy wins |
| Tab order resets | The save request failed | Reorder again, wait a moment, and reload. Check the browser's Network tab for a failed `tab-state` request |
| A deleted chapter still has a tab, or a new chapter has none | The tabs were out of date | Reload the page. Saved tabs for chapters that no longer exist are dropped, and new chapters are added after the others |
| "Error loading chapters" with a Retry button | The chapter list could not be loaded | Click Retry. If it keeps failing, check the network connection and that you are still signed in |
| Ctrl+number does nothing | There is no tab at that position in the tab bar | Click the tab instead |
| A status change does not stick | The status request failed, and the tab list is reloaded from the server | Set the status again from the chapter menu, or reload |

---
