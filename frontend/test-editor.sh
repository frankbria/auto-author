#!/bin/bash
# Script to test the tiptap editor integration

# Run the unit tests
echo "Running unit tests for the rich text editor..."
cd "$(dirname "$0")"
npm test RichTextEditor

# Start the development server to see the editor in action
echo ""
echo "Starting development server to test the editor in the browser..."
echo "You can access the editor at http://localhost:3000"
echo "Navigate to any book chapter to see the rich text editor in action"
echo ""
echo "Press Ctrl+C to stop the server when you're done testing"
npm run dev
