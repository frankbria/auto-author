"""
Load testing script for Auto-Author API using Locust.

This script simulates realistic user behavior for performance testing:
- User authentication
- Chapter operations
- Question generation and response
- File operations
- Concurrent user scenarios
"""

from locust import HttpUser, task, between, events
import json
import random
import time
from typing import Dict, Any

class AutoAuthorUser(HttpUser):
    """Simulates a typical Auto-Author user."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Initialize user session."""
        self.client.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Authenticate user
        self.authenticate()
        
        # Cache for created resources
        self.user_books = []
        self.user_chapters = []
        self.chapter_questions = {}
        
    def authenticate(self):
        """Authenticate the user and store auth token."""
        login_data = {
            "email": f"loadtest{random.randint(1, 1000)}@example.com",
            "password": "testpassword123"
        }
        
        response = self.client.post("/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {token}"})
        else:
            # Create new user if login fails
            self.create_test_user(login_data)
    
    def create_test_user(self, user_data: Dict[str, str]):
        """Create a test user for load testing."""
        response = self.client.post("/auth/register", json=user_data)
        if response.status_code == 201:
            # Login with new user
            login_response = self.client.post("/auth/login", json=user_data)
            if login_response.status_code == 200:
                token = login_response.json().get("access_token")
                self.client.headers.update({"Authorization": f"Bearer {token}"})
    
    @task(3)
    def view_dashboard(self):
        """View user dashboard - most common action."""
        self.client.get("/api/dashboard")
    
    @task(2)
    def create_book(self):
        """Create a new book."""
        book_data = {
            "title": f"Load Test Book {random.randint(1, 10000)}",
            "description": "This is a book created during load testing.",
            "genre": random.choice(["fiction", "non-fiction", "mystery", "romance"])
        }
        
        response = self.client.post("/api/books", json=book_data)
        if response.status_code == 201:
            book = response.json()
            self.user_books.append(book)
    
    @task(4)
    def list_books(self):
        """List user's books."""
        self.client.get("/api/books")
    
    @task(3)
    def create_chapter(self):
        """Create a new chapter if user has books."""
        if not self.user_books:
            self.create_book()
            return
        
        book = random.choice(self.user_books)
        chapter_data = {
            "title": f"Chapter {random.randint(1, 20)}",
            "content": self.generate_chapter_content(),
            "book_id": book["id"],
            "order": random.randint(1, 10)
        }
        
        response = self.client.post("/api/chapters", json=chapter_data)
        if response.status_code == 201:
            chapter = response.json()
            self.user_chapters.append(chapter)
    
    @task(5)
    def generate_questions(self):
        """Generate questions for a chapter."""
        if not self.user_chapters:
            self.create_chapter()
            return
        
        chapter = random.choice(self.user_chapters)
        chapter_id = chapter["id"]
        
        # Generate questions
        question_data = {
            "chapter_id": chapter_id,
            "question_count": random.randint(3, 8),
            "question_types": ["open-ended", "multiple-choice"]
        }
        
        with self.client.post(
            f"/api/chapters/{chapter_id}/questions/generate",
            json=question_data,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                questions = response.json().get("questions", [])
                self.chapter_questions[chapter_id] = questions
                response.success()
            else:
                response.failure(f"Failed to generate questions: {response.status_code}")
    
    @task(4)
    def submit_question_response(self):
        """Submit response to a question."""
        if not self.chapter_questions:
            self.generate_questions()
            return
        
        chapter_id = random.choice(list(self.chapter_questions.keys()))
        questions = self.chapter_questions[chapter_id]
        
        if questions:
            question = random.choice(questions)
            response_data = {
                "question_id": question["id"],
                "content": self.generate_response_content(),
                "time_taken": random.randint(30, 300)
            }
            
            self.client.post("/api/responses", json=response_data)
    
    @task(2)
    def get_chapter_progress(self):
        """Check progress for a chapter."""
        if not self.user_chapters:
            return
        
        chapter = random.choice(self.user_chapters)
        self.client.get(f"/api/chapters/{chapter['id']}/progress")
    
    @task(1)
    def export_chapter(self):
        """Export chapter data."""
        if not self.user_chapters:
            return
        
        chapter = random.choice(self.user_chapters)
        self.client.get(f"/api/chapters/{chapter['id']}/export")
    
    @task(1)
    def upload_file(self):
        """Upload a file (simulated)."""
        # Simulate file upload with small content
        files = {
            'file': ('test.txt', 'This is test file content for load testing.', 'text/plain')
        }
        
        self.client.post("/api/upload", files=files)
    
    def generate_chapter_content(self) -> str:
        """Generate realistic chapter content for testing."""
        paragraphs = [
            "This is the beginning of an interesting chapter that explores various themes and character development.",
            "The narrative progresses with compelling dialogue and vivid descriptions that engage the reader.",
            "Character interactions reveal deeper motivations and conflicts that drive the plot forward.",
            "The setting provides an atmospheric backdrop that enhances the emotional impact of the story.",
            "Plot developments introduce new challenges and opportunities for character growth and resolution."
        ]
        
        # Return 2-4 random paragraphs
        selected_paragraphs = random.sample(paragraphs, random.randint(2, 4))
        return " ".join(selected_paragraphs)
    
    def generate_response_content(self) -> str:
        """Generate realistic response content."""
        responses = [
            "This is a thoughtful response that analyzes the key themes and character motivations in depth.",
            "The response explores the relationship between different elements and their significance to the overall narrative.",
            "This analysis considers multiple perspectives and provides evidence to support the main arguments presented.",
            "The interpretation demonstrates understanding of literary devices and their effectiveness in the context.",
            "This response connects the specific details to broader themes and universal human experiences."
        ]
        
        return random.choice(responses)

class IntensiveUser(AutoAuthorUser):
    """Simulates a power user with intensive usage patterns."""
    
    wait_time = between(0.5, 1.5)  # Faster actions
    
    @task(10)
    def rapid_question_generation(self):
        """Generate questions rapidly."""
        if not self.user_chapters:
            self.create_chapter()
            return
        
        chapter = random.choice(self.user_chapters)
        for _ in range(3):  # Generate multiple batches quickly
            question_data = {
                "chapter_id": chapter["id"],
                "question_count": 5,
                "question_types": ["open-ended"]
            }
            self.client.post(f"/api/chapters/{chapter['id']}/questions/generate", json=question_data)
            time.sleep(0.1)  # Small delay between requests
    
    @task(8)
    def bulk_responses(self):
        """Submit multiple responses in sequence."""
        if not self.chapter_questions:
            self.rapid_question_generation()
            return
        
        chapter_id = random.choice(list(self.chapter_questions.keys()))
        questions = self.chapter_questions[chapter_id]
        
        # Submit responses to multiple questions
        for question in questions[:3]:  # Respond to first 3 questions
            response_data = {
                "question_id": question["id"],
                "content": self.generate_response_content(),
                "time_taken": random.randint(10, 60)  # Faster responses
            }
            self.client.post("/api/responses", json=response_data)

class CasualUser(AutoAuthorUser):
    """Simulates a casual user with slower, more deliberate actions."""
    
    wait_time = between(3, 8)  # Longer waits between actions
    
    @task(8)
    def browse_content(self):
        """Browse existing content more than creating new content."""
        self.client.get("/api/books")
        time.sleep(1)
        
        if self.user_chapters:
            chapter = random.choice(self.user_chapters)
            self.client.get(f"/api/chapters/{chapter['id']}")
    
    @task(2)
    def slow_question_generation(self):
        """Generate questions less frequently."""
        super().generate_questions()
    
    @task(3)
    def thoughtful_responses(self):
        """Submit longer, more thoughtful responses."""
        if not self.chapter_questions:
            return
        
        chapter_id = random.choice(list(self.chapter_questions.keys()))
        questions = self.chapter_questions[chapter_id]
        
        if questions:
            question = random.choice(questions)
            # Longer response content
            response_content = " ".join([self.generate_response_content() for _ in range(2)])
            response_data = {
                "question_id": question["id"],
                "content": response_content,
                "time_taken": random.randint(300, 900)  # 5-15 minutes
            }
            
            self.client.post("/api/responses", json=response_data)

# Event handlers for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Log custom metrics for specific endpoints."""
    if name.startswith("/api/chapters/") and "questions/generate" in name:
        # Track question generation performance
        if response_time > 5000:  # More than 5 seconds
            print(f"Slow question generation: {response_time}ms")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test environment."""
    print("Starting Auto-Author load test...")
    print(f"Target host: {environment.host}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Cleanup after test completion."""
    print("Load test completed.")
    
    # Print summary statistics
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time}ms")

# Custom user classes for different load patterns
class MixedUserPattern(AutoAuthorUser):
    """Mixed user pattern that changes behavior over time."""
    
    def on_start(self):
        super().on_start()
        self.phase = 1  # Start in phase 1
        self.actions_count = 0
    
    def choose_task(self):
        """Choose task based on current phase."""
        self.actions_count += 1
        
        # Change phases every 20 actions
        if self.actions_count % 20 == 0:
            self.phase = (self.phase % 3) + 1
        
        if self.phase == 1:
            # Setup phase: create content
            return random.choice([self.create_book, self.create_chapter])
        elif self.phase == 2:
            # Active phase: generate questions and respond
            return random.choice([self.generate_questions, self.submit_question_response])
        else:
            # Review phase: browse and export
            return random.choice([self.view_dashboard, self.get_chapter_progress, self.export_chapter])

# Stress test scenarios
class StressTestUser(AutoAuthorUser):
    """User for stress testing with aggressive patterns."""
    
    wait_time = between(0.1, 0.5)  # Very fast actions
    
    @task(20)
    def stress_question_generation(self):
        """Stress test question generation endpoint."""
        if not self.user_chapters:
            self.create_chapter()
            return
        
        chapter = random.choice(self.user_chapters)
        question_data = {
            "chapter_id": chapter["id"],
            "question_count": 10,  # Request many questions
            "question_types": ["open-ended", "multiple-choice", "yes-no"]
        }
        
        with self.client.post(
            f"/api/chapters/{chapter['id']}/questions/generate",
            json=question_data,
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Stress test failed: {response.status_code}")
            elif response.elapsed.total_seconds() > 10:
                response.failure("Response too slow for stress test")
            else:
                response.success()

# Load test configuration examples
"""
Example Locust commands:

# Basic load test
locust -f locustfile.py --host=http://localhost:8000 --users=10 --spawn-rate=2 --run-time=60s

# Stress test
locust -f locustfile.py AutoAuthorUser --host=http://localhost:8000 --users=50 --spawn-rate=5 --run-time=300s

# Mixed user patterns
locust -f locustfile.py MixedUserPattern --host=http://localhost:8000 --users=20 --spawn-rate=3 --run-time=180s

# Intensive users only
locust -f locustfile.py IntensiveUser --host=http://localhost:8000 --users=5 --spawn-rate=1 --run-time=120s

# Casual users only
locust -f locustfile.py CasualUser --host=http://localhost:8000 --users=15 --spawn-rate=2 --run-time=240s
"""
