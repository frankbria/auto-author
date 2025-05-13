from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import os
from app.core.config import DATABASE_URI, DATABASE_NAME

client = AsyncIOMotorClient(DATABASE_URI)
database = client[DATABASE_NAME]

async def get_collection(collection_name: str):
    return database[collection_name]