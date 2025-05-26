# Table of Contents Generation Requirements

This document outlines the technical requirements and integration details for the Auto Author Table of Contents (TOC) generation functionality.

## Overview

The TOC generation feature uses AI to automatically create a structured table of contents based on the user's book summary and responses to clarifying questions. This creates a foundation for the book's structure that can be further refined through the editing interface.

## Requirements

### Summary Input Requirements

- Minimum word count: 100 words
- Recommended word count: 250-500 words
- Summary must contain sufficient thematic content to generate a meaningful structure
- Confidence score is calculated based on:
  - Word count
  - Topic clarity
  - Genre identification
  - Narrative progression identifiers

### TOC Structure Requirements

- Each TOC must generate:
  - Top-level chapters (minimum 3, maximum 20)
  - Optional subchapters (nested up to 2 levels)
  - Brief description for each chapter/subchapter
  - Estimated page count
  - Structure notes with AI insights

### AI Integration Requirements

#### Input Processing

- Summary text is preprocessed to:
  - Remove irrelevant content
  - Identify key themes and topics
  - Extract genre and audience information
  - Analyze narrative or argumentative structure

#### Generation Process

1. **Readiness Assessment**
   - AI analyzes summary for completeness
   - Calculates confidence score
   - Provides specific feedback if requirements aren't met

2. **Clarifying Questions**
   - AI generates 3-5 targeted questions based on gaps in the summary
   - Questions focus on genre, audience, structure, and content depth
   - Responses are incorporated into the final TOC generation

3. **TOC Generation**
   - AI constructs hierarchical chapter structure
   - Determines logical chapter sequence
   - Creates descriptive chapter titles
   - Generates brief content descriptions for each chapter
   - Adds structure notes with rationale for the organization

## LLM Prompt Engineering

The system uses carefully engineered prompts to guide the AI in producing high-quality TOC structures:

1. **Readiness Assessment Prompt**
   - Evaluates summary completeness
   - Identifies information gaps
   - Calculates confidence score
   - Suggests improvements

2. **Clarifying Questions Prompt**
   - Identifies specific gaps in the summary
   - Generates questions to fill those gaps
   - Ensures questions cover genre, audience, structure, and content depth

3. **TOC Generation Prompt**
   - Combines summary and question responses
   - Specifies desired TOC format and depth
   - Guides hierarchical structure creation
   - Sets constraints for chapter/subchapter count
   - Requests brief descriptions and structure notes

## Error Handling

- Graceful degradation if AI service fails
- Retry mechanism for transient errors
- User-friendly error messages
- Fallback to manual TOC creation if automated generation fails
- Timeout handling for long-running AI operations

## Performance Considerations

- AI requests are rate-limited (2 per 5 minutes per user)
- Caching of TOC generation results
- Asynchronous processing for long-running operations
- Progress indicators during generation
- Efficient storage of TOC structures in MongoDB

## Related Documentation

- [TOC Generation User Guide](user-guide-toc-generation.md)
- [API TOC Endpoints](api-toc-endpoints.md)
- [Troubleshooting TOC Generation](troubleshooting-toc-generation.md)
