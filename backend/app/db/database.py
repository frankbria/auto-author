from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from bson.objectid import ObjectId
from app.core.config import settings
import os
from typing import Optional, List, Dict, Any

# Initialize MongoDB connection
client = AsyncIOMotorClient(settings.DATABASE_URI)
database = client[settings.DATABASE_NAME]

# Collections
users_collection = database.get_collection("users")


async def get_collection(collection_name: str):
    return database[collection_name]


# User-related database operations
async def get_user_by_clerk_id(clerk_id: str) -> Optional[Dict]:
    """Get a user by their Clerk ID"""
    user = await users_collection.find_one({"clerk_id": clerk_id})
    return user


async def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Get a user by their database ID"""
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    return user


async def get_user_by_email(email: str) -> Optional[Dict]:
    """Get a user by their email address"""
    user = await users_collection.find_one({"email": email})
    return user


async def create_user(user_data: Dict) -> Dict:
    """Create a new user in the database"""
    result = await users_collection.insert_one(user_data)
    created_user = await get_user_by_id(str(result.inserted_id))
    return created_user


async def update_user(clerk_id: str, user_data: Dict) -> Optional[Dict]:
    """Update an existing user"""
    updated_user = await users_collection.find_one_and_update(
        {"clerk_id": clerk_id}, {"$set": user_data}, return_document=True
    )
    return updated_user


async def delete_user(clerk_id: str) -> bool:
    """Delete a user from the database"""
    result = await users_collection.delete_one({"clerk_id": clerk_id})
    return result.deleted_count > 0
