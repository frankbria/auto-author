# Refactoring Guide: Migrating Tests from authenticated_client to auth_client_factory

This guide provides instructions on how to refactor tests from using `authenticated_client` to using `auth_client_factory`.

## Step 1: Identify Files to Refactor

All test files that use the `authenticated_client` fixture need to be refactored. You can find them with:

```powershell
Get-ChildItem -Path "backend\tests\test_api\test_routes" -Filter "*.py" | 
    Select-String -Pattern "authenticated_client" | 
    Select-Object Path -Unique | 
    Format-Table -HideTableHeaders
```

## Step 2: Refactoring Pattern

For each test function that uses `authenticated_client`, follow this pattern:

### Before:
```python
def test_example(authenticated_client, mock_user_data):
    # Test implementation using authenticated_client
    response = authenticated_client.get("/some/endpoint")
    # Assertions
```

### After:
```python
def test_example(auth_client_factory, test_user):
    # Create client with test user data
    client = auth_client_factory()
    
    # Test implementation using client
    response = client.get("/some/endpoint")
    # Assertions
```

## Step 3: Handling Mock User Data

If the test uses `mock_user_data`, replace it with `test_user`. If you need specific user data, pass it to `auth_client_factory`:

```python
# Create client with specialized user data
client = auth_client_factory({
    "role": "admin",
    "books": ["book1", "book2"]
})
```

## Step 4: Simplifying Mocks

The `auth_client_factory` already handles authentication mocking, so simplify the test by:

1. Removing unnecessary authentication mocks:
   - `app.core.security.verify_jwt_token`
   - `app.core.security.get_user_by_clerk_id`
   - `app.db.database.get_user_by_clerk_id`
   - `app.api.endpoints.users.get_current_user`

2. Only mock functions that are directly related to the behavior being tested:
   ```python
   with patch("app.db.database.update_user", return_value=expected_result):
       # Test code
   ```

## Step 5: Validating Refactored Tests

After refactoring, run the tests to ensure they still work:

```powershell
cd backend
python -m pytest tests/test_api/test_routes/test_profile_updates_refactored.py -v
```

## Example Refactoring

See the refactored example in `test_profile_updates_refactored.py`.

## Files Refactored:

- [x] `test_account_deletion.py`
- [x] `test_concurrent_profile_edits.py`
- [ ] `test_profile_updates.py` (example provided in `test_profile_updates_refactored.py`)
- [ ] `test_email_verification.py`
- [ ] `test_password_change.py`
- [ ] `test_user_preferences.py`
- [ ] `test_form_validation.py`
- [ ] `test_profile_picture.py`
- [ ] `test_profile_validation.py`
- [ ] `test_error_handling.py`
