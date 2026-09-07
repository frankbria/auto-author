import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timezone

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")

FAKE_USER_EMAIL = "seed-user@example.invalid"
# Local seed fixture only. Real authentication goes through better-auth, which
# owns its own collections - nothing reads this field to sign anyone in, and
# the value was never hashed despite the field name. Kept non-credential so a
# public repo carries no usable password (#599).
FAKE_USER_PASSWORD = os.getenv("SEED_USER_PASSWORD", "not-a-real-hash")
now = datetime.now(timezone.utc)

FAKE_BOOKS = [
    {
        "title": "The Complete Guide to Machine Learning",
        "subtitle": "From Basics to Advanced",
        "description": "A comprehensive overview of ML concepts, algorithms, and practical applications.",
        "genre": "Technology",
        "target_audience": "Students",
        "created_at": now,
        "updated_at": now,
    },
    {
        "title": "Understanding Modern Philosophy",
        "subtitle": "Ideas from Enlightenment to Now",
        "description": "Exploring philosophical ideas from the Enlightenment to contemporary thought.",
        "genre": "Philosophy",
        "target_audience": "General",
        "created_at": now,
        "updated_at": now,
    },
    {
        "title": "History of Ancient Civilizations",
        "subtitle": "A Journey Through Time",
        "description": "A journey through the great ancient civilizations and their lasting impact.",
        "genre": "History",
        "target_audience": "Enthusiasts",
        "created_at": now,
        "updated_at": now,
    },
]


def get_or_create_user(db):
    users = db["users"]
    user = users.find_one({"email": FAKE_USER_EMAIL})
    if not user:
        user = {
            "email": FAKE_USER_EMAIL,
            "hashed_password": FAKE_USER_PASSWORD,
            "auth_id": "550e8400-e29b-41d4-a716-446655440000",  # better-auth user ID (UUID)
            "role": "admin",
            "first_name": "Seed",
            "last_name": "User",
            "display_name": "Seed User",
        }
        user_id = users.insert_one(user).inserted_id
        user["_id"] = user_id
    return user


def create_fake_books(db, user):
    books = db["books"]
    for book_data in FAKE_BOOKS:
        existing = books.find_one(
            {"title": book_data["title"], "owner_id": user["_id"]}
        )
        if not existing:
            book = {
                **book_data,
                "owner_id": "550e8400-e29b-41d4-a716-446655440000",  # better-auth user ID
            }
            books.insert_one(book)


def main():
    if not DATABASE_URL or not DATABASE_NAME:
        print("DATABASE_URL or DATABASE_NAME not set in environment.")
        return
    client = MongoClient(DATABASE_URL)
    db = client[DATABASE_NAME]
    user = get_or_create_user(db)
    create_fake_books(db, user)
    print(f"Populated MongoDB with fake books for user: {user['email']}")
    client.close()


if __name__ == "__main__":
    main()
