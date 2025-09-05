from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to Mongo Atlas Cluster
mongo_client = MongoClient(os.getenv("MONGO_URL"))

# Access database
ecommerce_db = mongo_client["ecommerce_db"]

# Pick a collection to operate om
ecommerce_collection = ecommerce_db["ecommerce"]