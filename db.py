import pymongo
import uuid


class MongoDBClient:
    def __init__(self, uri="mongodb://localhost/", db_name="", collection_name=""):
        self.client = pymongo.MongoClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def insert_document(self, document):
        try:
            document["_id"] = str(uuid.uuid4())  # Add a unique ID to the document
            self.collection.insert_one(document)
        except Exception as e:
            print(e)

    def find_documents(self, query, projection=None):
        return self.collection.find(query, projection)

    def is_data_exists(self, query, projection=None):
        documents = self.find_documents(query, projection)
        return len(list(documents)) > 0
