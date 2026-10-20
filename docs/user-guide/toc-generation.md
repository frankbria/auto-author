# User Guide: TOC Generation Wizard

This guide walks through the step-by-step process of using Auto Author's Table of Contents (TOC) generation wizard.

## Getting Started

The TOC generation wizard is accessed from your book's dashboard after you've entered a summary for your book. The process guides you through a series of steps to create a well-structured table of contents tailored to your book's content.

### Prerequisites

Before generating a TOC, ensure you have:

- Created a book in your dashboard
- Entered a comprehensive summary (recommended 250+ words)
- Saved your summary

## Wizard Workflow

### Step 1: Checking Readiness

When you click "Generate Table of Contents," the wizard first checks if your summary meets the minimum requirements:

![Readiness Checker](../assets/img/toc-readiness-checker.png)

- **If ready**: The wizard automatically proceeds to Step 2
- **If not ready**: You'll see feedback on how to improve your summary

#### Not Ready Screen

If your summary needs improvement, you'll see:

- Confidence score
- Analysis of your summary
- Specific suggestions for improvement
- Word and character counts
- Option to return to the summary page for editing

### Step 2: Clarifying Questions

The AI generates 3-5 targeted questions to better understand your book's content:

![Clarifying Questions](../assets/img/toc-clarifying-questions.png)

1. Answer each question in the text boxes provided
2. Questions typically cover:
   - Genre and target audience
   - Main themes or arguments
   - Structure preferences (chronological, thematic, etc.)
   - Content depth and focus areas
3. Navigate between questions using the "Previous" and "Next" buttons
4. When all questions are answered, click "Generate Table of Contents"

#### Tips for Better Answers

- Be specific and detailed in your responses
- Mention key topics you want included in chapters
- Include information about your target audience
- Specify any structural preferences for your book

### Step 3: TOC Generation

The system processes your summary and question responses to create a TOC:

![TOC Generating](../assets/img/toc-generating.png)

During this step, you'll see:

- Progress indicator
- Current processing step
- Visual representation of the generation process

The AI performs several operations:

1. Analyzing your responses
2. Identifying key themes and topics
3. Structuring chapters and sections
4. Creating subchapter hierarchies
5. Optimizing content flow
6. Finalizing the table of contents

This process typically takes 15-45 seconds.

### Step 4: Review & Approve

Once generation is complete, you'll see the proposed TOC structure:

![TOC Review](../assets/img/toc-review.png)

This screen shows:

- Summary stats (total chapters, estimated pages, subchapter status)
- Chapter structure with expandable/collapsible sections
- AI structure notes explaining the organization
- Options to accept or regenerate

**Review features**:
- Click on chapters to expand/collapse and view subchapters
- Use "Expand All" or "Collapse All" buttons to adjust the view
- Read AI structure notes for insights on the organization

**Action options**:
- **Accept**: Saves the TOC and takes you to the detailed editing page
- **Regenerate**: Creates a new TOC with a different approach

## Step 5: Detailed TOC Editing

After accepting the generated TOC, you'll be taken to the editing interface:

![TOC Editing](../assets/img/toc-edit.png)

In this interface, you can:

- Add/delete chapters and subchapters
- Edit chapter titles and descriptions
- Reorder chapters by dragging and dropping
- Adjust the hierarchy of your content

### Editing Features

- **Add chapter**: Click "Add Chapter" button to add a top-level chapter
- **Add subchapter**: Click the "+" icon on a chapter to add a subchapter
- **Edit details**: Click on chapter titles or descriptions to edit them
- **Reorder**: Use drag handles to change the order of chapters
- **Delete**: Click the trash icon to remove a chapter or subchapter

### Saving Your Changes

When finished editing:

1. Click "Save & Continue" to save your TOC
2. Your TOC structure will be stored with your book
3. You'll be directed to the next step in the book creation process

## Tips for Successful TOC Generation

- Provide a detailed summary with clear themes and topics
- Answer clarifying questions with specific, detailed responses
- Include your target audience and purpose in your responses
- Review the generated TOC carefully before accepting
- Use the editing interface to fine-tune after generation
- Remember you can always regenerate if the initial result isn't satisfactory

## Related Documentation

- [TOC Generation Requirements](toc-generation-requirements.md)
- [API TOC Endpoints](api-toc-endpoints.md)
- [Troubleshooting TOC Generation](troubleshooting-toc-generation.md)
