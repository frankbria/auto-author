#!/usr/bin/env python3
"""Test data management CLI for MongoDB."""

import click
import asyncio
import os
import sys
from pathlib import Path
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient

# Add app to path
sys.path.append(str(Path(__file__).parent.parent))

from tests.factories.models import (
    UserFactory, BookFactory, ChapterFactory, QuestionFactory, ResponseFactory,
    clean_mongodb_test_data, seed_mongodb_test_data, get_test_data_config
)

class TestDataManager:
    def __init__(self, database_url: str, database_name: str = "auto-author-test"):
        self.database_url = database_url
        self.database_name = database_name
        self.sync_client = MongoClient(database_url)
        self.sync_db = self.sync_client[database_name]
    
    def close(self):
        """Close database connections."""
        self.sync_client.close()
    
    def clean_data(self):
        """Clean all data from collections."""
        try:
            clean_mongodb_test_data(self.sync_db)
            click.echo("✅ Successfully cleaned all test data")
        except Exception as e:
            click.echo(f"❌ Error cleaning data: {e}")
            raise
    
    def seed_basic_data(self):
        """Seed basic test data."""
        try:
            count = seed_mongodb_test_data(self.sync_db, environment="unit")
            click.echo(f"✅ Basic test data seeded successfully ({count} users created)")
        except Exception as e:
            click.echo(f"❌ Error seeding basic data: {e}")
            raise
    
    def seed_performance_data(self):
        """Seed large dataset for performance testing."""
        try:
            # Create performance test user
            user = UserFactory(
                id="perf-user",
                email="perf@example.com",
                name="Performance Test User"
            )
            session.add(user)
            
            # Create multiple books
            for book_idx in range(5):
                book = BookFactory(
                    id=f"perf-book-{book_idx+1}",
                    title=f"Performance Book {book_idx+1}",
                    user_id=user.id
                )
                session.add(book)
                
                # Create many chapters per book
                for chapter_idx in range(10):
                    chapter = ChapterFactory(
                        id=f"perf-chapter-{book_idx+1}-{chapter_idx+1}",
                        title=f"Chapter {chapter_idx+1}",
                        book_id=book.id,
                        order=chapter_idx+1,
                        content="Performance test content. " * 100
                    )
                    session.add(chapter)
                    
                    # Create many questions per chapter
                    for question_idx in range(20):
                        question = QuestionFactory(
                            id=f"perf-question-{book_idx+1}-{chapter_idx+1}-{question_idx+1}",
                            text=f"Performance question {question_idx+1}?",
                            chapter_id=chapter.id,
                            order=question_idx+1
                        )
                        session.add(question)
            
            session.commit()
            click.echo("✅ Performance test data seeded successfully")
            
        except Exception as e:
            session.rollback()
            click.echo(f"❌ Error seeding performance data: {e}")
            raise
        finally:
            session.close()
    
    def seed_edge_case_data(self):
        """Seed edge case test data."""
        session = self.SessionLocal()
        try:
            user = UserFactory(
                id="edge-user",
                email="edge@example.com",
                name="Edge Case User"
            )
            session.add(user)
            
            book = BookFactory(
                id="edge-book",
                title="Edge Case Book",
                user_id=user.id
            )
            session.add(book)
            
            # Empty content chapter
            empty_chapter = ChapterFactory(
                id="empty-chapter",
                title="Empty Chapter",
                book_id=book.id,
                content="",
                order=1
            )
            session.add(empty_chapter)
            
            # Very long content chapter
            long_chapter = ChapterFactory(
                id="long-chapter",
                title="Long Chapter",
                book_id=book.id,
                content="Very long content. " * 1000,
                order=2
            )
            session.add(long_chapter)
            
            # Chapter with many questions
            many_q_chapter = ChapterFactory(
                id="many-questions-chapter",
                title="Chapter with Many Questions",
                book_id=book.id,
                content="Chapter content for many questions.",
                order=3
            )
            session.add(many_q_chapter)
            
            # Create many questions
            for i in range(50):
                question = QuestionFactory(
                    id=f"edge-question-{i+1}",
                    text=f"Edge case question {i+1}?",
                    chapter_id=many_q_chapter.id,
                    order=i+1
                )
                session.add(question)
            
            session.commit()
            click.echo("✅ Edge case test data seeded successfully")
            
        except Exception as e:
            session.rollback()
            click.echo(f"❌ Error seeding edge case data: {e}")
            raise
        finally:
            session.close()

def get_database_url(environment: str) -> str:
    """Get database URL for environment."""
    urls = {
        'unit': 'sqlite:///test_unit.db',
        'integration': 'sqlite:///test_integration.db',
        'performance': 'sqlite:///test_performance.db',
        'e2e': 'sqlite:///test_e2e.db',
    }
    return urls.get(environment, urls['unit'])

@click.group()
def cli():
    """Test data management tools for Auto-Author."""
    pass

@cli.command()
@click.option('--environment', '-e', default='unit', 
              help='Test environment (unit, integration, performance, e2e)')
@click.option('--scenario', '-s', default='basic',
              help='Data scenario (basic, performance, edge_cases)')
def seed(environment, scenario):
    """Seed test database with data."""
    database_url = get_database_url(environment)
    manager = TestDataManager(database_url)
    
    click.echo(f"Seeding {environment} environment with {scenario} data...")
    click.echo(f"Database: {database_url}")
    
    # Create tables if they don't exist
    manager.create_tables()
    
    if scenario == 'basic':
        manager.seed_basic_data()
    elif scenario == 'performance':
        manager.seed_performance_data()
    elif scenario == 'edge_cases':
        manager.seed_edge_case_data()
    else:
        click.echo(f"❌ Unknown scenario: {scenario}")
        sys.exit(1)

@cli.command()
@click.option('--environment', '-e', default='unit')
@click.option('--force', '-f', is_flag=True, help='Force cleanup without confirmation')
def clean(environment, force):
    """Clean test database."""
    database_url = get_database_url(environment)
    manager = TestDataManager(database_url)
    
    if not force:
        if not click.confirm(f"Clean {environment} database ({database_url})?"):
            click.echo("Cancelled.")
            return
    
    click.echo(f"Cleaning {environment} database...")
    manager.clean_data()
    click.echo("✅ Database cleaned successfully")

@cli.command()
@click.option('--environment', '-e', default='unit')
def reset(environment):
    """Reset test database to initial state."""
    database_url = get_database_url(environment)
    manager = TestDataManager(database_url)
    
    click.echo(f"Resetting {environment} database...")
    manager.drop_tables()
    manager.create_tables()
    click.echo("✅ Database reset successfully")

@cli.command()
@click.option('--environment', '-e', default='unit')
def status(environment):
    """Show test database status."""
    database_url = get_database_url(environment)
    manager = TestDataManager(database_url)
    
    try:
        session = manager.SessionLocal()
        
        # Count records in each table
        user_count = session.execute(text("SELECT COUNT(*) FROM users")).scalar()
        book_count = session.execute(text("SELECT COUNT(*) FROM books")).scalar()
        chapter_count = session.execute(text("SELECT COUNT(*) FROM chapters")).scalar()
        question_count = session.execute(text("SELECT COUNT(*) FROM questions")).scalar()
        response_count = session.execute(text("SELECT COUNT(*) FROM responses")).scalar()
        
        click.echo(f"Database Status: {environment}")
        click.echo(f"URL: {database_url}")
        click.echo("="*40)
        click.echo(f"Users:     {user_count}")
        click.echo(f"Books:     {book_count}")
        click.echo(f"Chapters:  {chapter_count}")
        click.echo(f"Questions: {question_count}")
        click.echo(f"Responses: {response_count}")
        
        session.close()
        
    except Exception as e:
        click.echo(f"❌ Error checking status: {e}")

@cli.command()
def init():
    """Initialize all test environments."""
    environments = ['unit', 'integration', 'performance', 'e2e']
    
    for env in environments:
        click.echo(f"Initializing {env} environment...")
        database_url = get_database_url(env)
        manager = TestDataManager(database_url)
        manager.create_tables()
    
    click.echo("✅ All test environments initialized")

if __name__ == '__main__':
    cli()
