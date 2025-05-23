# Validation Rules and Error Messages for Book Metadata

This document provides a comprehensive reference for all validation rules applied to book metadata fields in the Auto Author application, along with the corresponding error messages and handling guidelines.

## Frontend Validation

The frontend application uses Zod for form validation, with the following rules:

### Title

| Validation Rule | Error Message | Description |
|-----------------|---------------|-------------|
| Required | "Title is required" | The title field cannot be empty |
| Max length: 100 chars | "Title must be 100 characters or less" | The title must not exceed 100 characters |

### Subtitle

| Validation Rule | Error Message | Description |
|-----------------|---------------|-------------|
| Max length: 200 chars | "Subtitle must be 200 characters or less" | The subtitle must not exceed 200 characters |
| Optional | N/A | The subtitle field can be left empty |

### Description

| Validation Rule | Error Message | Description |
|-----------------|---------------|-------------|
| Max length: 1000 chars | "Description must be 1000 characters or less" | The description must not exceed 1000 characters |
| Optional | N/A | The description field can be left empty |

### Genre

| Validation Rule | Error Message | Description |
|-----------------|---------------|-------------|
| Max length: 50 chars | "Genre must be 50 characters or less" | The genre must not exceed 50 characters |
| Optional | N/A | The genre field can be left empty |
| Enum validation | N/A | The application UI restricts selection to predefined values |

### Target Audience

| Validation Rule | Error Message | Description |
|-----------------|---------------|-------------|
| Max length: 100 chars | "Target audience must be 100 characters or less" | The target audience must not exceed 100 characters |
| Optional | N/A | The target audience field can be left empty |
| Enum validation | N/A | The application UI restricts selection to predefined values |

### Cover Image URL

| Validation Rule | Error Message | Description |
|-----------------|---------------|-------------|
| Valid URL format | "Cover image must be a valid URL" | The URL must conform to standard URL format (protocol, domain, etc.) |
| Max length: 300 chars | N/A | The URL is truncated if it exceeds 300 characters |
| Optional | N/A | The cover image URL field can be left empty |

## Backend Validation

The backend API uses Pydantic for data validation, with the following rules:

### Title

| Validation Rule | Error Message | HTTP Status |
|-----------------|---------------|-------------|
| Required | "field required" | 422 Unprocessable Entity |
| Min length: 1 char | "ensure this value has at least 1 characters" | 422 Unprocessable Entity |
| Max length: 100 chars | "ensure this value has at most 100 characters" | 422 Unprocessable Entity |

### Subtitle

| Validation Rule | Error Message | HTTP Status |
|-----------------|---------------|-------------|
| Max length: 255 chars | "ensure this value has at most 255 characters" | 422 Unprocessable Entity |
| Optional | N/A | N/A |

### Description

| Validation Rule | Error Message | HTTP Status |
|-----------------|---------------|-------------|
| Max length: 5000 chars | "ensure this value has at most 5000 characters" | 422 Unprocessable Entity |
| Optional | N/A | N/A |

### Genre

| Validation Rule | Error Message | HTTP Status |
|-----------------|---------------|-------------|
| Max length: 100 chars | "ensure this value has at most 100 characters" | 422 Unprocessable Entity |
| Optional | N/A | N/A |

### Target Audience

| Validation Rule | Error Message | HTTP Status |
|-----------------|---------------|-------------|
| Max length: 100 chars | "ensure this value has at most 100 characters" | 422 Unprocessable Entity |
| Optional | N/A | N/A |

### Cover Image URL

| Validation Rule | Error Message | HTTP Status |
|-----------------|---------------|-------------|
| Max length: 2083 chars | "ensure this value has at most 2083 characters" | 422 Unprocessable Entity |
| Optional | N/A | N/A |

## API Response Error Formats

### Validation Errors (HTTP 422)

```json
{
  "detail": [
    {
      "loc": ["body", "title"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Not Found Errors (HTTP 404)

```json
{
  "detail": "Book not found"
}
```

### Authentication Errors (HTTP 401)

```json
{
  "detail": "Authentication required"
}
```

### Permission Errors (HTTP 403)

```json
{
  "detail": "You don't have access to this book"
}
```

## Error Handling Best Practices

### Frontend Error Handling

1. **Display inline validation errors**
   - Show error messages directly below the corresponding input fields
   - Use red text and appropriate icons to indicate errors
   - Keep error messages concise and actionable

2. **Handle network and API errors**
   - Display a notification toast for API failures
   - Provide a clear error message with retry options when appropriate
   - Log detailed errors to the console for debugging

3. **Prevent form submission with validation errors**
   - Disable the submit button when validation errors exist
   - Highlight all fields with errors when submission is attempted
   - Auto-focus the first field with an error for better UX

### Backend Error Handling

1. **Provide descriptive error messages**
   - Include the specific field and validation rule that failed
   - Keep error messages consistent and documentation-aligned
   - Include reference IDs for server errors to aid in troubleshooting

2. **Log validation failures appropriately**
   - Log validation errors at the INFO level
   - Log unexpected errors at the ERROR level with stack traces
   - Include request IDs in logs for correlation

3. **Rate limiting and security**
   - Return 429 Too Many Requests when rate limits are exceeded
   - Use generic error messages for security-related failures
   - Include retry-after headers when applicable

## Differences Between Frontend and Backend Validation

Some validation rules differ between frontend and backend for practical reasons:

1. **Description length**
   - Frontend: 1000 characters maximum
   - Backend: 5000 characters maximum
   - Reason: The frontend limit is for better user experience and interface performance, while the backend allows for compatibility with external systems or API clients

2. **Genre length**
   - Frontend: 50 characters maximum
   - Backend: 100 characters maximum
   - Reason: Similar to description, the backend allows more flexibility for API clients

3. **Cover Image URL length**
   - Frontend: 300 characters implicitly (input field constraint)
   - Backend: 2083 characters (maximum URL length supported by browsers)
   - Reason: The backend accommodates the full range of valid URLs

## Custom Error Messages

For improved user experience, the application uses custom error messages rather than the default validation errors:

| Default Error | Custom Message |
|---------------|----------------|
| "String must contain at least 1 character(s)" | "Title is required" |
| "String must contain at most N character(s)" | "[Field] must be N characters or less" |
| "Invalid url" | "Cover image must be a valid URL" |

## Validation Lifecycle

1. **Real-time validation**
   - Occurs as the user types or changes field values
   - Visual indicators appear immediately (red outlines, icons)
   - Error messages appear when focus leaves the field (blur event)

2. **Pre-submission validation**
   - All fields are validated before the form can be submitted
   - Client-side validation prevents most invalid submissions

3. **Backend validation**
   - Provides a second layer of validation for security
   - Handles edge cases and more complex validations
   - Ensures data integrity in the database
