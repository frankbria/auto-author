# OpenAI Integration Setup Guide

## Overview

The Auto Author application uses OpenAI's GPT-4 model for AI-powered features including:
- Book summary analysis
- Table of Contents (TOC) generation
- Chapter-specific question generation
- Draft content generation from Q&A responses

## Setup Instructions

### 1. Obtain an OpenAI API Key

1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (it starts with `sk-`)

### 2. Configure the Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file and add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

### 3. Verify the Configuration

1. Start the backend server:
   ```bash
   cd backend
   source .venv/bin/activate  # or use 'uv run'
   uv run uvicorn app.main:app --reload
   ```

2. The server should start without errors. If you see OpenAI-related errors, verify your API key is correct.

## API Endpoints Using OpenAI

The following endpoints utilize the OpenAI integration:

### 1. Summary Analysis
- **Endpoint**: `POST /api/v1/books/{book_id}/analyze-summary`
- **Purpose**: Analyzes if a book summary is suitable for TOC generation

### 2. Clarifying Questions Generation
- **Endpoint**: `POST /api/v1/books/{book_id}/generate-questions`
- **Purpose**: Generates 3-5 clarifying questions to improve TOC generation

### 3. TOC Generation
- **Endpoint**: `POST /api/v1/books/{book_id}/generate-toc`
- **Purpose**: Generates a hierarchical table of contents from summary and answers

### 4. Chapter Draft Generation
- **Endpoint**: `POST /api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft`
- **Purpose**: Transforms Q&A responses into narrative chapter content

## Cost Considerations

- GPT-4 usage is billed per token (roughly 750 words = 1000 tokens)
- Typical costs per operation:
  - Summary analysis: ~$0.01-0.02
  - Question generation: ~$0.02-0.03
  - TOC generation: ~$0.03-0.05
  - Chapter draft: ~$0.10-0.30 (depending on length)

## Error Handling

The AI service includes:
- Automatic retry with exponential backoff for rate limits
- Graceful error handling for API failures
- Fallback responses for common issues

## Troubleshooting

### Common Issues

1. **"Invalid API Key" Error**
   - Verify the key in `.env` is correct
   - Ensure the key has not been revoked
   - Check for extra spaces or quotes around the key

2. **Rate Limit Errors**
   - The service automatically retries with backoff
   - Consider upgrading your OpenAI plan for higher limits

3. **Model Access Errors**
   - Ensure your OpenAI account has access to GPT-4
   - New accounts may need to add payment method first

## Security Notes

- Never commit your API key to version control
- The `.env` file is gitignored by default
- Consider using environment-specific keys for production
- Monitor your OpenAI usage dashboard for unexpected activity

## Alternative: Using Claude (Anthropic)

While the current implementation uses OpenAI, the service architecture supports easy adaptation to other providers like Claude. To use Claude instead:

1. Install the Anthropic SDK: `pip install anthropic`
2. Update `ai_service.py` to use Anthropic client
3. Replace `OPENAI_API_KEY` with `ANTHROPIC_API_KEY` in settings
4. Adjust prompt formatting for Claude's preferences

---

*Last Updated: January 2025*