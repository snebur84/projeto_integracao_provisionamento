from django.conf import settings
from pymongo import MongoClient

def get_mongo_client():
    host = settings.MONGODB['HOST']
    port = settings.MONGODB['PORT']
    db_name = settings.MONGODB['DB_NAME']
    client = MongoClient(host, port)
    db = client[db_name]
    return db