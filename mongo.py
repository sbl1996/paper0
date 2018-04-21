from pymongo import MongoClient

client = MongoClient()
db = client.test_database
coll = db.test_collection