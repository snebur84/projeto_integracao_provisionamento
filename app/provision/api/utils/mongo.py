from django.conf import settings
from pymongo import MongoClient
import threading
import logging

logger = logging.getLogger(__name__)

# Thread-safe lazy singleton for MongoDB DB instance
_client_lock = threading.Lock()
_db_instance = None

def get_mongo_client():
    """
    Return a cached/persistent pymongo database handle.
    Uses credentials from settings.MONGODB if provided.
    """
    global _db_instance
    if _db_instance is not None:
        return _db_instance

    host = settings.MONGODB.get('HOST', 'localhost')
    port = settings.MONGODB.get('PORT', 27017)
    db_name = settings.MONGODB.get('DB_NAME')
    user = settings.MONGODB.get('USER') or ''
    password = settings.MONGODB.get('PASSWORD') or ''

    try:
        with _client_lock:
            if _db_instance is not None:
                return _db_instance

            if user and password:
                # Use a connection string with user/pass when provided
                uri = f"mongodb://{user}:{password}@{host}:{port}/{db_name}"
                client = MongoClient(uri)
            else:
                client = MongoClient(host, port)

            _db_instance = client[db_name]
            logger.info("Connected to MongoDB database '%s' at %s:%s", db_name, host, port)
            return _db_instance
    except Exception as exc:
        logger.exception("Failed to create MongoDB client: %s", exc)
        raise