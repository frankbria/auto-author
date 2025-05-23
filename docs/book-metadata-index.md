# Book Metadata Documentation Index

This index provides links to all documentation related to book metadata in the Auto Author application.

## User Documentation

* [User Guide: Editing Book Info and Uploading Cover Images](user-guide-book-metadata.md)
* [Troubleshooting Guide: Common Book Metadata Issues](troubleshooting-book-metadata.md)

## Technical Documentation

* [Book Metadata Fields Documentation](book-metadata-fields.md)
* [Book Metadata API Endpoints](api-book-endpoints.md)
* [Validation Rules and Error Messages](validation-rules-book-metadata.md)

## Related Documentation

* [Database Schema Documentation](../backend/README.md)
* [Book Creation Process](user-guide-book-creation.md)

## Quick Reference

### Key Metadata Fields

| Field | Required | Max Length |
|-------|----------|------------|
| Title | Yes | 100 chars |
| Subtitle | No | 200 chars |
| Description | No | 1000 chars (UI), 5000 chars (API) |
| Genre | No | 50 chars (UI), 100 chars (API) |
| Target Audience | No | 100 chars |
| Cover Image URL | No | Must be valid URL |

### Common Issues and Solutions

1. **Auto-save not working**: Ensure all fields pass validation
2. **Cover image not showing**: Verify URL is correct and publicly accessible
3. **Validation errors**: Check character limits and required fields

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/books` | GET | Get all user books |
| `/books` | POST | Create a new book |
| `/books/{id}` | GET | Get book by ID |
| `/books/{id}` | PUT | Update book metadata |
| `/books/{id}` | DELETE | Delete a book |

For complete information, please refer to the specific documentation linked above.
