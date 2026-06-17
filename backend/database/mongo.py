import os
from pymongo import MongoClient
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "legal_ai")

if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set. Please configure .env file.")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
queries_collection = db["queries"]


@contextmanager
def get_db_session():
    """Context manager for database sessions"""
    try:
        yield db
    finally:
        pass


def verify_connection():
    """Verify MongoDB connection"""
    try:
        client.admin.command('ping')
        return True
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return False