# Test Data Management

This document outlines the test data management strategy, including data seeding, cleanup utilities, and environment management.

## Overview

Test data management ensures:
- **Consistent test data** across all environments
- **Isolated test execution** with clean data states
- **Realistic data scenarios** for comprehensive testing
- **Efficient data cleanup** to maintain performance
- **Environment-specific data** for different testing needs

## Data Management Strategy

### 1. Test Data Categories

#### Static Reference Data
- User roles and permissions
- Application configuration
- Genre classifications
- Question types and templates

#### Dynamic Test Data
- User accounts and profiles
- Books and chapters
- Questions and responses
- Session and progress data

#### Performance Test Data
- Large datasets for load testing
- High-volume user scenarios
- Bulk operations data

### 2. Data Lifecycle

```
Generate → Seed → Test → Cleanup → Reset
```

1. **Generate**: Create test data using factories
2. **Seed**: Populate test database
3. **Test**: Execute tests with data
4. **Cleanup**: Remove test artifacts
5. **Reset**: Return to clean state

## Frontend Test Data Management

### 1. Test Fixtures

#### Chapter Test Data
```typescript
// frontend/src/__tests__/fixtures/chapters.ts
export const createMockChapter = (overrides: Partial<Chapter> = {}): Chapter => ({
  id: 'chapter-1',
  title: 'Introduction to Testing',
  content: 'This chapter covers the fundamentals of testing...',
  book_id: 'book-1',
  order: 1,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  ...overrides,
})

export const createMockChapters = (count: number = 3): Chapter[] => 
  Array.from({ length: count }, (_, i) => 
    createMockChapter({
      id: `chapter-${i + 1}`,
      title: `Chapter ${i + 1}`,
      order: i + 1,
    })
  )

export const chapterWithQuestions = createMockChapter({
  id: 'chapter-with-questions',
  questions: [
    createMockQuestion({ id: 'q1', text: 'What is the main theme?' }),
    createMockQuestion({ id: 'q2', text: 'How does this relate to the story?' }),
  ],
})
```

#### Question Test Data
```typescript
// frontend/src/__tests__/fixtures/questions.ts
export const createMockQuestion = (overrides: Partial<Question> = {}): Question => ({
  id: 'question-1',
  text: 'What is the primary conflict in this chapter?',
  type: 'open-ended',
  chapter_id: 'chapter-1',
  order: 1,
  created_at: '2024-01-01T00:00:00Z',
  response: null,
  ...overrides,
})

export const questionTypes = {
  openEnded: createMockQuestion({ type: 'open-ended' }),
  multipleChoice: createMockQuestion({ 
    type: 'multiple-choice',
    options: ['Option A', 'Option B', 'Option C', 'Option D']
  }),
  yesNo: createMockQuestion({ 
    type: 'yes-no',
    text: 'Is this character trustworthy?'
  }),
}

export const createQuestionBatch = (count: number, chapterId: string): Question[] =>
  Array.from({ length: count }, (_, i) =>
    createMockQuestion({
      id: `question-${chapterId}-${i + 1}`,
      text: `Question ${i + 1} for chapter?`,
      chapter_id: chapterId,
      order: i + 1,
    })
  )
```

#### User Test Data
```typescript
// frontend/src/__tests__/fixtures/users.ts
export const createMockUser = (overrides: Partial<User> = {}): User => ({
  id: 'user-1',
  email: 'test@example.com',
  name: 'Test User',
  role: 'author',
  created_at: '2024-01-01T00:00:00Z',
  preferences: {
    theme: 'light',
    auto_save: true,
    notifications: true,
  },
  ...overrides,
})

export const userRoles = {
  author: createMockUser({ role: 'author' }),
  editor: createMockUser({ role: 'editor', id: 'user-editor' }),
  admin: createMockUser({ role: 'admin', id: 'user-admin' }),
}
```

### 2. Mock Data Providers

#### API Mock Provider
```typescript
// frontend/src/__tests__/mocks/apiProvider.ts
export class MockApiProvider {
  private static instance: MockApiProvider
  private data: Map<string, any> = new Map()

  static getInstance(): MockApiProvider {
    if (!MockApiProvider.instance) {
      MockApiProvider.instance = new MockApiProvider()
    }
    return MockApiProvider.instance
  }

  seedData(key: string, data: any): void {
    this.data.set(key, data)
  }

  getData(key: string): any {
    return this.data.get(key)
  }

  clearData(): void {
    this.data.clear()
  }

  // Simulate API responses
  async getChapter(id: string): Promise<Chapter> {
    const chapters = this.getData('chapters') || []
    const chapter = chapters.find((c: Chapter) => c.id === id)
    if (!chapter) throw new Error(`Chapter ${id} not found`)
    return chapter
  }

  async generateQuestions(chapterId: string, count: number = 5): Promise<Question[]> {
    return createQuestionBatch(count, chapterId)
  }
}
```

### 3. Test Setup and Teardown

#### Global Test Setup
```typescript
// frontend/src/__tests__/setup/globalSetup.ts
import { MockApiProvider } from '../mocks/apiProvider'
import { createMockChapters, createMockUser } from '../fixtures'

export const setupTestData = (): void => {
  const mockApi = MockApiProvider.getInstance()
  
  // Seed standard test data
  mockApi.seedData('chapters', createMockChapters(5))
  mockApi.seedData('currentUser', createMockUser())
  
  // Seed performance test data
  if (process.env.NODE_ENV === 'performance') {
    mockApi.seedData('chapters', createMockChapters(100))
  }
}

export const teardownTestData = (): void => {
  const mockApi = MockApiProvider.getInstance()
  mockApi.clearData()
}
```

## Backend Test Data Management

### 1. Database Fixtures

#### Pytest Fixtures
```python
# backend/tests/fixtures/database.py
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.models import User, Book, Chapter, Question

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///test.db", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(test_engine):
    """Create isolated database session for each test."""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    
    yield session
    
    # Cleanup after test
    session.rollback()
    session.close()

@pytest.fixture
def clean_db(db_session):
    """Ensure clean database state for each test."""
    # Clean all tables
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()
    
    yield db_session
```

#### Data Factory Classes
```python
# backend/tests/factories/models.py
import factory
from factory.alchemy import SQLAlchemyModelFactory
from app.models import User, Book, Chapter, Question, Response
from app.database import SessionLocal

class BaseFactory(SQLAlchemyModelFactory):
    class Meta:
        sqlalchemy_session = SessionLocal()
        sqlalchemy_session_persistence = "commit"

class UserFactory(BaseFactory):
    class Meta:
        model = User
    
    id = factory.Sequence(lambda n: f"user-{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.id}@example.com")
    name = factory.Faker("name")
    role = "author"
    created_at = factory.Faker("date_time")

class BookFactory(BaseFactory):
    class Meta:
        model = Book
    
    id = factory.Sequence(lambda n: f"book-{n}")
    title = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("text", max_nb_chars=200)
    user_id = factory.SubFactory(UserFactory)
    genre = factory.Faker("word")
    created_at = factory.Faker("date_time")

class ChapterFactory(BaseFactory):
    class Meta:
        model = Chapter
    
    id = factory.Sequence(lambda n: f"chapter-{n}")
    title = factory.Faker("sentence", nb_words=3)
    content = factory.Faker("text", max_nb_chars=1000)
    book_id = factory.SubFactory(BookFactory)
    order = factory.Sequence(lambda n: n)
    created_at = factory.Faker("date_time")

class QuestionFactory(BaseFactory):
    class Meta:
        model = Question
    
    id = factory.Sequence(lambda n: f"question-{n}")
    text = factory.Faker("sentence", nb_words=8)
    type = factory.Iterator(["open-ended", "multiple-choice", "yes-no"])
    chapter_id = factory.SubFactory(ChapterFactory)
    order = factory.Sequence(lambda n: n)
    created_at = factory.Faker("date_time")

class ResponseFactory(BaseFactory):
    class Meta:
        model = Response
    
    id = factory.Sequence(lambda n: f"response-{n}")
    content = factory.Faker("text", max_nb_chars=500)
    question_id = factory.SubFactory(QuestionFactory)
    created_at = factory.Faker("date_time")
```

### 2. Data Seeding Scripts

#### Development Data Seeder
```python
# backend/scripts/seed_dev_data.py
#!/usr/bin/env python3
"""Seed development database with test data."""

import asyncio
from sqlalchemy.orm import sessionmaker
from app.database import engine, Base
from tests.factories.models import (
    UserFactory, BookFactory, ChapterFactory, QuestionFactory
)

async def seed_development_data():
    """Seed database with development data."""
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Create test users
        users = UserFactory.create_batch(3)
        
        for user in users:
            # Create books for each user
            books = BookFactory.create_batch(2, user_id=user.id)
            
            for book in books:
                # Create chapters for each book
                chapters = ChapterFactory.create_batch(5, book_id=book.id)
                
                for chapter in chapters:
                    # Create questions for each chapter
                    QuestionFactory.create_batch(5, chapter_id=chapter.id)
        
        session.commit()
        print("✅ Development data seeded successfully")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error seeding data: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(seed_development_data())
```

#### Test Data Seeder
```python
# backend/scripts/seed_test_data.py
#!/usr/bin/env python3
"""Seed test database with specific test scenarios."""

import asyncio
from tests.factories.models import *

class TestDataSeeder:
    def __init__(self, session):
        self.session = session
    
    def create_basic_scenario(self):
        """Create basic test scenario with one user, book, and chapter."""
        user = UserFactory(id="test-user-1", email="test@example.com")
        book = BookFactory(id="test-book-1", user_id=user.id, title="Test Book")
        chapter = ChapterFactory(
            id="test-chapter-1", 
            book_id=book.id, 
            title="Test Chapter",
            content="This is test content for the chapter."
        )
        questions = QuestionFactory.create_batch(5, chapter_id=chapter.id)
        
        return {
            'user': user,
            'book': book,
            'chapter': chapter,
            'questions': questions
        }
    
    def create_performance_scenario(self):
        """Create large dataset for performance testing."""
        user = UserFactory(id="perf-user", email="perf@example.com")
        
        # Create multiple books
        books = BookFactory.create_batch(10, user_id=user.id)
        
        all_chapters = []
        all_questions = []
        
        for book in books:
            # Create many chapters per book
            chapters = ChapterFactory.create_batch(20, book_id=book.id)
            all_chapters.extend(chapters)
            
            for chapter in chapters:
                # Create many questions per chapter
                questions = QuestionFactory.create_batch(10, chapter_id=chapter.id)
                all_questions.extend(questions)
        
        return {
            'user': user,
            'books': books,
            'chapters': all_chapters,
            'questions': all_questions
        }
    
    def create_edge_case_scenarios(self):
        """Create edge case test data."""
        scenarios = {}
        
        # Empty content chapter
        scenarios['empty_chapter'] = ChapterFactory(
            id="empty-chapter",
            content="",
            title="Empty Chapter"
        )
        
        # Very long content chapter
        scenarios['long_chapter'] = ChapterFactory(
            id="long-chapter",
            content="Very long content. " * 1000,
            title="Long Chapter"
        )
        
        # Chapter with many questions
        chapter_many_q = ChapterFactory(id="many-questions-chapter")
        scenarios['many_questions'] = {
            'chapter': chapter_many_q,
            'questions': QuestionFactory.create_batch(50, chapter_id=chapter_many_q.id)
        }
        
        return scenarios

async def seed_test_data(scenario: str = "basic"):
    """Seed test data based on scenario."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    seeder = TestDataSeeder(session)
    
    try:
        if scenario == "basic":
            data = seeder.create_basic_scenario()
        elif scenario == "performance":
            data = seeder.create_performance_scenario()
        elif scenario == "edge_cases":
            data = seeder.create_edge_case_scenarios()
        else:
            raise ValueError(f"Unknown scenario: {scenario}")
        
        session.commit()
        print(f"✅ Test data seeded for scenario: {scenario}")
        return data
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error seeding test data: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    import sys
    scenario = sys.argv[1] if len(sys.argv) > 1 else "basic"
    asyncio.run(seed_test_data(scenario))
```

### 3. Cleanup Utilities

#### Database Cleanup
```python
# backend/tests/utils/cleanup.py
from sqlalchemy.orm import Session
from app.database import Base, engine
from app.models import User, Book, Chapter, Question, Response

class DatabaseCleaner:
    def __init__(self, session: Session):
        self.session = session
    
    def clean_all_tables(self):
        """Clean all tables in dependency order."""
        # Delete in reverse dependency order
        self.session.query(Response).delete()
        self.session.query(Question).delete()
        self.session.query(Chapter).delete()
        self.session.query(Book).delete()
        self.session.query(User).delete()
        self.session.commit()
    
    def clean_test_data(self):
        """Clean only test-specific data."""
        # Delete data with test prefixes
        self.session.query(User).filter(User.id.like("test-%")).delete()
        self.session.query(User).filter(User.email.like("%test%")).delete()
        self.session.commit()
    
    def reset_sequences(self):
        """Reset auto-increment sequences."""
        # For PostgreSQL
        if engine.dialect.name == 'postgresql':
            for table in Base.metadata.sorted_tables:
                self.session.execute(f"ALTER SEQUENCE {table.name}_id_seq RESTART WITH 1")
        
        # For SQLite, sequences are handled automatically
        self.session.commit()

# Pytest fixture for cleanup
@pytest.fixture(autouse=True)
def cleanup_after_test(db_session):
    """Automatically cleanup after each test."""
    yield
    cleaner = DatabaseCleaner(db_session)
    cleaner.clean_all_tables()
```

### 4. Environment-Specific Data Management

#### Environment Configuration
```python
# backend/config/test_environments.py
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class TestEnvironmentConfig:
    name: str
    database_url: str
    seed_data: bool
    cleanup_after_tests: bool
    data_size: str  # 'small', 'medium', 'large'
    
    def get_data_config(self) -> Dict[str, Any]:
        configs = {
            'small': {'users': 2, 'books_per_user': 1, 'chapters_per_book': 3},
            'medium': {'users': 5, 'books_per_user': 2, 'chapters_per_book': 5},
            'large': {'users': 10, 'books_per_user': 5, 'chapters_per_book': 10},
        }
        return configs.get(self.data_size, configs['small'])

# Environment configurations
ENVIRONMENTS = {
    'unit': TestEnvironmentConfig(
        name='unit',
        database_url='sqlite:///:memory:',
        seed_data=False,
        cleanup_after_tests=True,
        data_size='small'
    ),
    'integration': TestEnvironmentConfig(
        name='integration',
        database_url='sqlite:///integration_test.db',
        seed_data=True,
        cleanup_after_tests=True,
        data_size='medium'
    ),
    'performance': TestEnvironmentConfig(
        name='performance',
        database_url='postgresql://test:test@localhost/perf_test',
        seed_data=True,
        cleanup_after_tests=False,
        data_size='large'
    ),
}

def get_test_environment(env_name: str) -> TestEnvironmentConfig:
    return ENVIRONMENTS.get(env_name, ENVIRONMENTS['unit'])
```

## Data Management Scripts

### 1. Management CLI
```python
# backend/scripts/test_data_manager.py
#!/usr/bin/env python3
"""Test data management CLI."""

import click
import asyncio
from enum import Enum

class DataOperation(Enum):
    SEED = "seed"
    CLEAN = "clean"
    RESET = "reset"
    BACKUP = "backup"
    RESTORE = "restore"

@click.group()
def cli():
    """Test data management tools."""
    pass

@cli.command()
@click.option('--environment', '-e', default='unit', 
              help='Test environment (unit, integration, performance)')
@click.option('--scenario', '-s', default='basic',
              help='Data scenario (basic, performance, edge_cases)')
def seed(environment, scenario):
    """Seed test database with data."""
    click.echo(f"Seeding {environment} environment with {scenario} data...")
    # Implementation here

@cli.command()
@click.option('--environment', '-e', default='unit')
@click.option('--force', '-f', is_flag=True, help='Force cleanup without confirmation')
def clean(environment, force):
    """Clean test database."""
    if not force:
        if not click.confirm(f"Clean {environment} database?"):
            click.echo("Cancelled.")
            return
    
    click.echo(f"Cleaning {environment} database...")
    # Implementation here

@cli.command()
@click.option('--environment', '-e', default='unit')
def reset(environment):
    """Reset test database to initial state."""
    click.echo(f"Resetting {environment} database...")
    # Implementation here

@cli.command()
@click.option('--environment', '-e', default='unit')
@click.option('--file', '-f', help='Backup file path')
def backup(environment, file):
    """Backup test database."""
    backup_file = file or f"{environment}_backup.sql"
    click.echo(f"Backing up {environment} to {backup_file}...")
    # Implementation here

@cli.command()
@click.option('--environment', '-e', default='unit')
@click.option('--file', '-f', required=True, help='Backup file path')
def restore(environment, file):
    """Restore test database from backup."""
    click.echo(f"Restoring {environment} from {file}...")
    # Implementation here

if __name__ == '__main__':
    cli()
```

### 2. Package Scripts
Add to `package.json` and setup scripts:

#### Frontend Scripts
```json
{
  "scripts": {
    "test:seed": "node scripts/seedTestData.js",
    "test:clean": "node scripts/cleanTestData.js",
    "test:reset": "npm run test:clean && npm run test:seed"
  }
}
```

#### Backend Scripts
```bash
# backend/scripts/test_commands.sh
#!/bin/bash

# Seed test data
seed_test_data() {
    python scripts/test_data_manager.py seed --environment $1 --scenario $2
}

# Clean test data
clean_test_data() {
    python scripts/test_data_manager.py clean --environment $1 --force
}

# Reset test environment
reset_test_env() {
    python scripts/test_data_manager.py reset --environment $1
}

# Make functions available
export -f seed_test_data clean_test_data reset_test_env
```

## Usage Examples

### Frontend Test Data Usage
```typescript
// In a test file
import { MockApiProvider } from '../mocks/apiProvider'
import { createMockChapter, createQuestionBatch } from '../fixtures'

describe('ChapterQuestions', () => {
  beforeEach(() => {
    const mockApi = MockApiProvider.getInstance()
    
    // Seed test data for this test
    const chapter = createMockChapter({ id: 'test-chapter' })
    const questions = createQuestionBatch(5, chapter.id)
    
    mockApi.seedData('chapters', [chapter])
    mockApi.seedData('questions', questions)
  })
  
  afterEach(() => {
    MockApiProvider.getInstance().clearData()
  })
  
  it('should load chapter questions', async () => {
    // Test implementation
  })
})
```

### Backend Test Data Usage
```python
# In a test file
def test_generate_questions(clean_db):
    # Create test data
    chapter = ChapterFactory(
        content="This is a test chapter with enough content to generate questions."
    )
    
    # Test the functionality
    questions = generate_questions(chapter.id)
    
    assert len(questions) == 5
    assert all(q.chapter_id == chapter.id for q in questions)
```

## Best Practices

### 1. Data Isolation
- Use separate databases for different test types
- Clean data between tests
- Use transactions for rollback

### 2. Performance
- Use in-memory databases for unit tests
- Cache frequently used test data
- Optimize data generation for large datasets

### 3. Maintainability
- Use factories instead of fixtures when possible
- Keep test data close to tests that use it
- Version control test data schemas

### 4. Realism
- Use realistic data that reflects production scenarios
- Include edge cases and error conditions
- Test with different data volumes
