#!/usr/bin/env python3
"""Factory classes for generating test data for MongoDB collections."""

import factory
from datetime import datetime, timezone
import random
import string
from bson import ObjectId
from typing import Dict, Any, List
from faker import Faker

fake = Faker()

class MongoFactory(factory.Factory):
    """Base factory for MongoDB documents."""

    class Meta:
        abstract = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Create and return a MongoDB document."""
        return kwargs

    @classmethod
    def create_in_db(cls, collection, **kwargs):
        """Create document and insert into MongoDB collection."""
        doc = cls.create(**kwargs)
        doc['_id'] = ObjectId()
        doc['id'] = str(doc['_id'])
        result = collection.insert_one(doc)
        doc['_id'] = result.inserted_id
        return doc

class UserFactory(MongoFactory):
    """Factory for User documents."""

    auth_id = factory.LazyFunction(lambda: str(__import__('uuid').uuid4()))
    email = factory.LazyAttribute(lambda obj: f"test_{fake.user_name()}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    display_name = factory.LazyAttribute(lambda obj: f"{obj.first_name} {obj.last_name}")
    avatar_url = factory.LazyFunction(lambda: fake.image_url() if random.choice([True, False]) else None)
    bio = factory.LazyFunction(lambda: fake.text(max_nb_chars=200) if random.choice([True, False]) else None)
    role = factory.Iterator(["user", "admin", "moderator"])
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    books = factory.LazyFunction(list)  # Empty list by default

    @factory.lazy_attribute
    def preferences(self):
        """Generate user preferences."""
        return {
            "theme": random.choice(["light", "dark", "system"]),
            "email_notifications": random.choice([True, False]),
            "marketing_emails": random.choice([True, False]),
        }

    @factory.lazy_attribute
    def metadata(self):
        """Generate user metadata."""
        return {
            "signup_source": random.choice(["web", "mobile", "api"]),
            "last_login": datetime.now(timezone.utc),
            "login_count": random.randint(1, 100)
        }

class BookFactory(MongoFactory):
    """Factory for Book documents."""

    title = factory.Faker("sentence", nb_words=4)
    subtitle = factory.LazyFunction(lambda: fake.sentence(nb_words=6) if random.choice([True, False]) else None)
    description = factory.Faker("text", max_nb_chars=500)
    genre = factory.Iterator([
        "Fiction", "Non-Fiction", "Science Fiction", "Fantasy", "Mystery",
        "Romance", "Thriller", "Biography", "History", "Science", "Technology"
    ])
    target_audience = factory.Iterator(["General", "Young Adult", "Children", "Academic", "Professional"])
    status = factory.Iterator(["draft", "in_progress", "completed", "published"])
    owner_id = factory.LazyFunction(lambda: str(ObjectId()))  # Will be overridden in tests
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    chapters = factory.LazyFunction(list)  # Empty list by default

    @factory.lazy_attribute
    def metadata(self):
        """Generate book metadata."""
        return {
            "word_count": random.randint(1000, 100000),
            "page_count": random.randint(50, 500),
            "estimated_reading_time": random.randint(30, 600),  # minutes
            "language": "en",
            "isbn": fake.isbn13() if random.choice([True, False]) else None
        }

class ChapterFactory(MongoFactory):
    """Factory for Chapter documents."""

    title = factory.Faker("sentence", nb_words=3)
    content = factory.Faker("text", max_nb_chars=2000)
    order = factory.Sequence(lambda n: n + 1)
    status = factory.Iterator(["draft", "in_progress", "completed"])
    book_id = factory.LazyFunction(lambda: str(ObjectId()))  # Will be overridden in tests
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    @factory.lazy_attribute
    def metadata(self):
        """Generate chapter metadata."""
        return {
            "word_count": random.randint(100, 5000),
            "estimated_reading_time": random.randint(5, 30),  # minutes
            "last_edited_by": str(ObjectId()),
            "version": 1
        }

class QuestionFactory(MongoFactory):
    """Factory for Question documents."""

    text = factory.LazyFunction(lambda: fake.sentence() + "?")
    question_type = factory.Iterator([
        "open-ended", "multiple-choice", "yes-no", "scale", "reflection"
    ])
    category = factory.Iterator([
        "character_development", "plot", "setting", "theme", "style", "audience"
    ])
    order = factory.Sequence(lambda n: n + 1)
    chapter_id = factory.LazyFunction(lambda: str(ObjectId()))  # Will be overridden in tests
    book_id = factory.LazyFunction(lambda: str(ObjectId()))  # Will be overridden in tests
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    @factory.lazy_attribute
    def options(self):
        """Generate options for multiple choice questions."""
        if hasattr(self, 'question_type') and self.question_type == "multiple-choice":
            return [fake.sentence(nb_words=4) for _ in range(4)]
        elif hasattr(self, 'question_type') and self.question_type == "scale":
            return {"min": 1, "max": 10, "step": 1}
        return None

    @factory.lazy_attribute
    def metadata(self):
        """Generate question metadata."""
        return {
            "difficulty": random.choice(["easy", "medium", "hard"]),
            "estimated_time": random.randint(2, 15),  # minutes
            "ai_generated": random.choice([True, False])
        }

class ResponseFactory(MongoFactory):
    """Factory for Response documents."""

    content = factory.Faker("text", max_nb_chars=1000)
    question_id = factory.LazyFunction(lambda: str(ObjectId()))  # Will be overridden in tests
    user_id = factory.LazyFunction(lambda: str(ObjectId()))  # Will be overridden in tests
    chapter_id = factory.LazyFunction(lambda: str(ObjectId()))  # Will be overridden in tests
    time_taken = factory.LazyFunction(lambda: random.randint(30, 900))  # seconds
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    @factory.lazy_attribute
    def metadata(self):
        """Generate response metadata."""
        content_text = getattr(self, 'content', '') or ''
        return {
            "word_count": len(content_text.split()) if content_text else 0,
            "character_count": len(content_text) if content_text else 0,
            "edit_count": random.randint(0, 10),
            "auto_saved": random.choice([True, False])
        }

class AuditLogFactory(MongoFactory):
    """Factory for Audit Log documents."""

    action = factory.Iterator([
        "user.created", "user.updated", "user.deleted",
        "book.created", "book.updated", "book.deleted",
        "chapter.created", "chapter.updated", "chapter.deleted",
        "question.created", "question.answered", "response.updated"
    ])
    user_id = factory.LazyFunction(lambda: str(ObjectId()))
    resource_type = factory.Iterator(["user", "book", "chapter", "question", "response"])
    resource_id = factory.LazyFunction(lambda: str(ObjectId()))
    timestamp = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    @factory.lazy_attribute
    def details(self):
        """Generate audit log details."""
        return {
            "ip_address": fake.ipv4(),
            "user_agent": fake.user_agent(),
            "session_id": fake.uuid4(),
            "changes": {
                "field": "value",
                "old_value": "old",
                "new_value": "new"
            }
        }

# Utility functions for test data generation

def generate_realistic_book_content(word_count: int = 1000) -> str:
    """Generate realistic book content with proper paragraph structure."""
    paragraphs = []
    words_per_paragraph = random.randint(50, 150)
    current_word_count = 0

    while current_word_count < word_count:
        paragraph_words = min(words_per_paragraph, word_count - current_word_count)
        paragraph = fake.text(max_nb_chars=paragraph_words * 6)  # Rough estimate
        paragraphs.append(paragraph)
        current_word_count += len(paragraph.split())

    return "\n\n".join(paragraphs)

def generate_interview_questions(category: str, count: int = 5) -> List[Dict[str, Any]]:
    """Generate interview-style questions for a specific category."""
    question_templates = {
        "character_development": [
            "Who is your main character and what drives them?",
            "What is your protagonist's biggest fear?",
            "How does your main character change throughout the story?",
            "What makes your character unique and memorable?",
            "What internal conflicts does your character face?"
        ],
        "plot": [
            "What is the central conflict of your story?",
            "How does your story begin and what hooks the reader?",
            "What is the climax of your book?",
            "How do you resolve the main conflict?",
            "What unexpected twists occur in your story?"
        ],
        "setting": [
            "Where and when does your story take place?",
            "How does the setting influence your characters?",
            "What makes your story's world unique?",
            "How do you describe the atmosphere of your story?",
            "What role does the environment play in your plot?"
        ],
        "theme": [
            "What is the main message of your book?",
            "What themes do you explore in your story?",
            "What do you want readers to learn or feel?",
            "How do your characters embody your themes?",
            "What questions does your book raise?"
        ]
    }

    questions = question_templates.get(category, question_templates["character_development"])
    selected_questions = random.sample(questions, min(count, len(questions)))

    return [
        QuestionFactory.create(
            text=q,
            category=category,
            question_type="open-ended",
            order=i+1
        ) for i, q in enumerate(selected_questions)
    ]

def create_test_user_with_books(
    user_count: int = 1,
    books_per_user: int = 2,
    chapters_per_book: int = 3,
    questions_per_chapter: int = 5
) -> List[Dict[str, Any]]:
    """Create a complete test dataset with users, books, chapters, and questions."""
    users = []

    for _ in range(user_count):
        user = UserFactory.create()
        user_books = []

        for _ in range(books_per_user):
            book = BookFactory.create(owner_id=user.get('id', str(ObjectId())))
            book_chapters = []

            for chapter_order in range(1, chapters_per_book + 1):
                chapter = ChapterFactory.create(
                    book_id=book.get('id', str(ObjectId())),
                    order=chapter_order,
                    content=generate_realistic_book_content(random.randint(500, 2000))
                )

                # Generate questions for this chapter
                categories = ["character_development", "plot", "setting", "theme"]
                chapter_questions = []

                for q_order in range(1, questions_per_chapter + 1):
                    category = random.choice(categories)
                    question = QuestionFactory.create(
                        chapter_id=chapter.get('id', str(ObjectId())),
                        book_id=book.get('id', str(ObjectId())),
                        category=category,
                        order=q_order
                    )
                    chapter_questions.append(question)

                chapter['questions'] = chapter_questions
                book_chapters.append(chapter)

            book['chapters'] = book_chapters
            user_books.append(book)

        user['books'] = user_books
        users.append(user)

    return users

# Data seeding configurations for different test environments

TEST_DATA_CONFIGS = {
    "unit": {
        "users": 2,
        "books_per_user": 1,
        "chapters_per_book": 2,
        "questions_per_chapter": 3
    },
    "integration": {
        "users": 5,
        "books_per_user": 2,
        "chapters_per_book": 3,
        "questions_per_chapter": 5
    },
    "performance": {
        "users": 50,
        "books_per_user": 3,
        "chapters_per_book": 5,
        "questions_per_chapter": 10
    },
    "e2e": {
        "users": 10,
        "books_per_user": 2,
        "chapters_per_book": 4,
        "questions_per_chapter": 8
    }
}

def get_test_data_config(environment: str = "unit") -> Dict[str, int]:
    """Get test data configuration for specific environment."""
    return TEST_DATA_CONFIGS.get(environment, TEST_DATA_CONFIGS["unit"])

# MongoDB-specific utilities

def clean_mongodb_test_data(db, collections: List[str] = None):
    """Clean test data from MongoDB collections."""
    if collections is None:
        collections = ["users", "books", "chapters", "questions", "responses", "audit_logs"]

    for collection_name in collections:
        collection = db.get_collection(collection_name)
        collection.delete_many({})

def seed_mongodb_test_data(db, environment: str = "unit"):
    """Seed MongoDB with test data for specified environment."""
    config = get_test_data_config(environment)
    users = create_test_user_with_books(**config)

    # Insert users and related data into MongoDB
    users_collection = db.get_collection("users")
    books_collection = db.get_collection("books")
    chapters_collection = db.get_collection("chapters")
    questions_collection = db.get_collection("questions")

    for user in users:
        # Insert user
        user_doc = {k: v for k, v in user.items() if k != 'books'}
        user_doc['_id'] = ObjectId()
        user_doc['id'] = str(user_doc['_id'])
        users_collection.insert_one(user_doc)

        # Insert books and chapters
        for book in user.get('books', []):
            book_doc = {k: v for k, v in book.items() if k != 'chapters'}
            book_doc['_id'] = ObjectId()
            book_doc['id'] = str(book_doc['_id'])
            book_doc['owner_id'] = user_doc['id']
            books_collection.insert_one(book_doc)

            # Insert chapters and questions
            for chapter in book.get('chapters', []):
                chapter_doc = {k: v for k, v in chapter.items() if k != 'questions'}
                chapter_doc['_id'] = ObjectId()
                chapter_doc['id'] = str(chapter_doc['_id'])
                chapter_doc['book_id'] = book_doc['id']
                chapters_collection.insert_one(chapter_doc)

                # Insert questions
                for question in chapter.get('questions', []):
                    question_doc = dict(question)
                    question_doc['_id'] = ObjectId()
                    question_doc['id'] = str(question_doc['_id'])
                    question_doc['chapter_id'] = chapter_doc['id']
                    question_doc['book_id'] = book_doc['id']
                    questions_collection.insert_one(question_doc)

    return len(users)
