from fastapi import FastAPI, status, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.hash import bcrypt
from bson.objectid import ObjectId
from typing import Optional, Literal
from pymongo import ReturnDocument
from pydantic import BaseModel, Field
from dotenv import load_dotenv

import pymongo
import os
import requests
import jwt

load_dotenv()
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
DATABASE = os.getenv("DATABASE")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")

conn_str = f"mongodb+srv://{USER}:{PASSWORD}@learning.g5nb0.mongodb.net/{DATABASE}?retryWrites=true&w=majority"

# set a 5-second connection timeout
client = pymongo.MongoClient(conn_str, serverSelectionTimeoutMS=5000)

db = client.library
books_collection = db.books_collection
users_collection = db.users_collection
app = FastAPI()


response = requests.get(
    f"https://www.googleapis.com/books/v1/volumes?q=sisters+inauthor:pratchett&key={GOOGLE_API_KEY}"
)


class Book(BaseModel):

    title: str
    description: Optional[str]
    author: str = Field(..., max_length=100)
    status: Literal["available", "rented"] = "available"


class User(BaseModel):

    username: str = Field(unique=True)
    password_hash: str

    @classmethod
    def get_user(cls, username):
        return cls.get(username=username)

    def verify_password(self, password):
        return bcrypt.verify(password, self.password_hash)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def authenticate_user(username: str, password: str):
    user = User(**users_collection.find_one({"username": username}))
    if not user:
        return False
    if not user.verify_password(password):
        return False
    return user


@app.post("/token")
def generate_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        return {"error": "Invalid credentials"}
    token = jwt.encode(user.dict(), JWT_SECRET)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/")
def root():
    books = books_collection.find({})
    book_list = []
    for book in books:
        print(f"Book: {book}")
        book_list.append(Book(**book))
    for item in response.json()["items"]:
        book_list.append(item)
        print(item)
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    return book_list


@app.post("/users")
def create_user(user: User):
    existing_user = users_collection.find({"username": user.username})
    if existing_user:
        return "User already exists"
    user.password_hash = bcrypt.hash(user.password_hash)
    users_collection.insert_one(user.dict())
    return user


@app.get("/users")
def get_users():
    users = users_collection.find({})
    user_list = []
    for user in users:
        user_list.append(User(**user))
    return user_list


@app.post("/book")
def add_book(book: Book):
    books_collection.insert_one(book.dict())
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/book/{book_id}/rent")
def rent_a_book(book_id):
    print(type(book_id))
    result = books_collection.find_one_and_update(
        {"_id": ObjectId(book_id)}, {"$set": {"status": "rented"}}
    )
    if result:
        return RedirectResponse(url="/")
    return {"message": "Failure!!!"}


@app.get("/book/{book_id}/return")
def return_a_book(book_id):
    result = books_collection.find_one_and_update(
        {"_id": ObjectId(book_id)},
        {"$set": {"status": "available"}},
        return_document=ReturnDocument.AFTER,
    )
    if result:
        return RedirectResponse(url="/")
    return {"message": "failure"}


@app.get("/book/{book_id}/delete")
def delete_a_book(book_id):
    result = books_collection.delete_one(
        {"_id": ObjectId(book_id)},
    )
    if result:
        return RedirectResponse(url="/")
    return {"message": "failure"}
