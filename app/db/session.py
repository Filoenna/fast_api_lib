import pymongo
import os

from dotenv import load_dotenv

USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
DATABASE = os.getenv("DATABASE")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# "driver://USER:PASSWORD@host:port"
conn_str = f"mongodb://{USER}:{PASSWORD}@mongo:27017/"
client = pymongo.MongoClient(conn_str, serverSelectionTimeoutMS=5000)

db = client.library
