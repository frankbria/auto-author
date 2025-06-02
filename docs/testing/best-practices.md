# Testing Best Practices

This document outlines best practices for testing in the Auto-Author application.

## General Principles

### 1. Test Pyramid Strategy
```
    /\
   /  \    E2E Tests (Few, Slow, High Confidence)
  /____\
 /      \   Integration Tests (Some, Medium Speed)
/__Unit__\  Unit Tests (Many, Fast, Low-level)
```

- **70% Unit Tests**: Fast, isolated, test individual functions/components
- **20% Integration Tests**: Test component interactions and API endpoints
- **10% E2E Tests**: Test complete user workflows

### 2. Testing Philosophy
- **Test behavior, not implementation**
- **Write tests first (TDD) when possible**
- **Prefer integration tests over mocks for critical paths**
- **Test edge cases and error conditions**
- **Keep tests simple and readable**

## Frontend Testing Best Practices

### 1. Component Testing

#### ✅ Do: Test User Interactions
```typescript
test('should generate questions when button is clicked', async () => {
  const user = userEvent.setup()
  render(<ChapterQuestions chapterId="1" />)
  
  const generateButton = screen.getByRole('button', { name: /generate questions/i })
  await user.click(generateButton)
  
  expect(screen.getByText(/generating questions/i)).toBeInTheDocument()
})
```

#### ❌ Don't: Test Implementation Details
```typescript
// Bad - testing internal state
test('should set loading to true', () => {
  const { container } = render(<ChapterQuestions />)
  expect(container.querySelector('.loading')).toBeInTheDocument()
})
```

### 2. Query Priorities
Use queries in this order of preference:
1. **getByRole**: Most accessible
2. **getByLabelText**: Good for forms
3. **getByPlaceholderText**: Placeholder text
4. **getByText**: Visible text
5. **getByTestId**: Last resort

```typescript
// Preferred
const button = screen.getByRole('button', { name: /submit/i })
const input = screen.getByLabelText(/email address/i)

// Avoid
const button = screen.getByTestId('submit-button')
```

### 3. Async Testing
```typescript
// Wait for elements to appear
await waitFor(() => {
  expect(screen.getByText(/questions generated/i)).toBeInTheDocument()
})

// Wait for elements to disappear
await waitForElementToBeRemoved(screen.queryByText(/loading/i))
```

### 4. Mocking Guidelines

#### Mock External Dependencies
```typescript
// Mock API calls
jest.mock('@/lib/api', () => ({
  generateQuestions: jest.fn(),
}))

// Mock Next.js router
jest.mock('next/router', () => ({
  useRouter: () => ({
    push: jest.fn(),
    pathname: '/chapter/1',
  }),
}))
```

#### Don't Mock What You're Testing
```typescript
// Bad - mocking the component you're testing
jest.mock('@/components/ChapterQuestions')

// Good - mock its dependencies
jest.mock('@/lib/api')
```

### 5. Test Data Management
```typescript
// Use factories for consistent test data
const createMockQuestion = (overrides = {}) => ({
  id: '1',
  text: 'What is the main theme?',
  type: 'open-ended',
  ...overrides,
})

// Use realistic data
const mockChapter = {
  id: '1',
  title: 'Introduction to Testing',
  content: 'Testing is important...',
  questions: [createMockQuestion()],
}
```

## Backend Testing Best Practices

### 1. Test Structure (AAA Pattern)
```python
def test_generate_questions_success():
    # Arrange
    chapter_data = {
        "id": "1",
        "content": "Sample chapter content"
    }
    
    # Act
    result = question_service.generate_questions(chapter_data)
    
    # Assert
    assert len(result) == 5
    assert all(q.endswith('?') for q in result)
```

### 2. Fixture Usage
```python
@pytest.fixture
def sample_chapter():
    return {
        "id": "test-chapter-1",
        "title": "Test Chapter",
        "content": "This is test content for the chapter."
    }

@pytest.fixture
def mock_openai_client(monkeypatch):
    mock_client = Mock()
    mock_client.generate_questions.return_value = [
        "What is the main point?",
        "How does this relate to the topic?"
    ]
    monkeypatch.setattr("app.services.ai_service.openai_client", mock_client)
    return mock_client

def test_question_generation(sample_chapter, mock_openai_client):
    result = generate_questions(sample_chapter)
    assert len(result) == 2
    mock_openai_client.generate_questions.assert_called_once()
```

### 3. Database Testing
```python
@pytest.fixture
def db_session():
    # Use transaction rollback for isolation
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

def test_create_question(db_session):
    question = Question(
        text="Test question?",
        chapter_id="1",
        type="multiple-choice"
    )
    db_session.add(question)
    db_session.commit()
    
    saved_question = db_session.query(Question).filter_by(text="Test question?").first()
    assert saved_question is not None
    assert saved_question.chapter_id == "1"
```

### 4. API Testing
```python
def test_generate_questions_endpoint(client, auth_headers):
    payload = {
        "chapter_id": "1",
        "content": "Sample content",
        "question_count": 3
    }
    
    response = client.post(
        "/api/questions/generate",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["questions"]) == 3
    assert "question_id" in data["questions"][0]
```

### 5. Error Testing
```python
def test_generate_questions_invalid_input():
    with pytest.raises(ValidationError) as exc_info:
        generate_questions(None)
    
    assert "chapter_content" in str(exc_info.value)

def test_api_error_handling(client):
    response = client.post("/api/questions/generate", json={})
    
    assert response.status_code == 422
    assert "validation error" in response.json()["detail"].lower()
```

## Integration Testing Best Practices

### 1. Test Real Workflows
```python
def test_complete_question_workflow(client, db_session, auth_headers):
    # Create chapter
    chapter_response = client.post(
        "/api/chapters",
        json={"title": "Test", "content": "Content"},
        headers=auth_headers
    )
    chapter_id = chapter_response.json()["id"]
    
    # Generate questions
    questions_response = client.post(
        f"/api/chapters/{chapter_id}/questions/generate",
        headers=auth_headers
    )
    questions = questions_response.json()["questions"]
    
    # Submit responses
    for question in questions:
        response = client.post(
            f"/api/questions/{question['id']}/responses",
            json={"answer": "Test answer"},
            headers=auth_headers
        )
        assert response.status_code == 201
```

### 2. Test Service Integration
```typescript
describe('ChapterQuestions Integration', () => {
  it('should complete full question lifecycle', async () => {
    // Mock API responses
    mockApiClient.generateQuestions.mockResolvedValue({
      questions: [{ id: '1', text: 'Test question?' }]
    })
    
    render(<ChapterQuestions chapterId="1" />)
    
    // Generate questions
    await user.click(screen.getByRole('button', { name: /generate/i }))
    
    // Verify questions appear
    expect(await screen.findByText('Test question?')).toBeInTheDocument()
    
    // Answer question
    const input = screen.getByRole('textbox')
    await user.type(input, 'Test answer')
    
    // Submit response
    await user.click(screen.getByRole('button', { name: /submit/i }))
    
    // Verify API calls
    expect(mockApiClient.generateQuestions).toHaveBeenCalledWith('1')
    expect(mockApiClient.saveResponse).toHaveBeenCalledWith('1', 'Test answer')
  })
})
```

## Performance Testing Best Practices

### 1. Measure What Matters
```typescript
test('should render large question lists efficiently', async () => {
  const startTime = performance.now()
  
  const manyQuestions = Array.from({ length: 100 }, (_, i) => ({
    id: i.toString(),
    text: `Question ${i}?`
  }))
  
  render(<QuestionList questions={manyQuestions} />)
  
  const endTime = performance.now()
  expect(endTime - startTime).toBeLessThan(100) // 100ms threshold
})
```

### 2. Memory Leak Detection
```typescript
test('should not leak memory on component unmount', () => {
  const { unmount } = render(<ChapterQuestions chapterId="1" />)
  
  const initialMemory = performance.memory?.usedJSHeapSize || 0
  unmount()
  
  // Force garbage collection if available
  if (global.gc) {
    global.gc()
  }
  
  const finalMemory = performance.memory?.usedJSHeapSize || 0
  expect(finalMemory).toBeLessThanOrEqual(initialMemory * 1.1) // 10% tolerance
})
```

## Accessibility Testing Best Practices

### 1. Screen Reader Testing
```typescript
test('should be accessible to screen readers', async () => {
  render(<ChapterQuestions chapterId="1" />)
  
  // Check for proper ARIA labels
  expect(screen.getByRole('main')).toHaveAttribute('aria-label', 'Chapter Questions')
  
  // Check for heading hierarchy
  expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
  
  // Check for keyboard navigation
  const firstButton = screen.getAllByRole('button')[0]
  firstButton.focus()
  expect(document.activeElement).toBe(firstButton)
})
```

### 2. Keyboard Navigation
```typescript
test('should support keyboard navigation', async () => {
  const user = userEvent.setup()
  render(<QuestionForm />)
  
  // Tab through interactive elements
  await user.tab()
  expect(screen.getByRole('textbox')).toHaveFocus()
  
  await user.tab()
  expect(screen.getByRole('button', { name: /submit/i })).toHaveFocus()
  
  // Test Enter key submission
  await user.keyboard('{Enter}')
  expect(mockSubmit).toHaveBeenCalled()
})
```

## Test Organization

### 1. File Structure
```
src/
├── __tests__/
│   ├── components/
│   │   ├── ChapterQuestions.test.tsx
│   │   └── QuestionForm.test.tsx
│   ├── pages/
│   │   └── chapter.test.tsx
│   ├── utils/
│   │   └── api.test.ts
│   ├── fixtures/
│   │   ├── chapters.ts
│   │   └── questions.ts
│   └── mocks/
│       ├── api.ts
│       └── router.ts
```

### 2. Test Naming
```typescript
// Component tests
describe('ChapterQuestions', () => {
  describe('when questions are loading', () => {
    it('should show loading spinner', () => {})
    it('should disable generate button', () => {})
  })
  
  describe('when questions are generated', () => {
    it('should display question list', () => {})
    it('should enable editing', () => {})
  })
})

// API tests
describe('POST /api/questions/generate', () => {
  describe('with valid input', () => {
    it('should return generated questions', () => {})
  })
  
  describe('with invalid input', () => {
    it('should return validation error', () => {})
  })
})
```

## Code Coverage Guidelines

### 1. Coverage Targets
- **Statements**: 90%
- **Branches**: 85%
- **Functions**: 90%
- **Lines**: 90%

### 2. What to Exclude
```json
// jest.config.cjs
{
  "collectCoverageFrom": [
    "src/**/*.{ts,tsx}",
    "!src/**/*.d.ts",
    "!src/**/*.stories.{ts,tsx}",
    "!src/**/index.ts",
    "!src/types/**"
  ]
}
```

### 3. Focus on Quality, Not Just Numbers
- 100% coverage doesn't guarantee bug-free code
- Focus on testing critical business logic
- Test edge cases and error conditions
- Ensure tests are maintainable and readable

## Continuous Improvement

### 1. Regular Test Reviews
- Review test failures immediately
- Refactor tests when code changes
- Remove obsolete tests
- Update test documentation

### 2. Test Metrics
- Track test execution time
- Monitor coverage trends
- Identify flaky tests
- Measure test effectiveness

### 3. Team Practices
- Code review includes test review
- Pair on complex test scenarios
- Share testing knowledge
- Regular testing retrospectives
