from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.responses import RedirectResponse
from typing import Optional, Literal
from pymongo import ReturnDocument
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from bson.objectid import ObjectId

from ..dependencies import get_token_header

import pymongo
import os
import requests

load_dotenv()
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
DATABASE = os.getenv("DATABASE")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

router = APIRouter(
    prefix="/books",
    tags=["books"],
    responses={404: {"description": "Not found"}},
)


conn_str = f"mongodb://{USER}:{PASSWORD}@mongo:27017/"

# set a 5-second connection timeout
client = pymongo.MongoClient(conn_str, serverSelectionTimeoutMS=5000)

db = client.library
books_collection = db.books


response = requests.get(
    f"https://www.googleapis.com/books/v1/volumes?q=sisters+inauthor:pratchett&key={GOOGLE_API_KEY}"
)


class Book(BaseModel):

    title: str
    description: Optional[str]
    author: str = Field(..., max_length=100)
    status: Literal["available", "rented"] = "available"


@router.get("/")
def root():
    books = books_collection.find({})
    book_list = []
    for book in books:
        print(f"Book: {book}")
        book_list.append(Book(**book))
    for item in response.json()["items"]:
        book_list.append(item)
    return book_list


@router.post("/")
def add_book(book: Book):
    books_collection.insert_one(book.dict())
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{book_id}/rent")
def rent_a_book(book_id):
    print(type(book_id))
    result = books_collection.find_one_and_update(
        {"_id": ObjectId(book_id)}, {"$set": {"status": "rented"}}
    )
    if result:
        return RedirectResponse(url="/")
    return {"message": "Failure!!!"}


@router.get("/{book_id}/return")
def return_a_book(book_id):
    result = books_collection.find_one_and_update(
        {"_id": ObjectId(book_id)},
        {"$set": {"status": "available"}},
        return_document=ReturnDocument.AFTER,
    )
    if result:
        return RedirectResponse(url="/")
    return {"message": "failure"}


@router.get("/{book_id}/delete")
def delete_a_book(book_id):
    result = books_collection.delete_one(
        {"_id": ObjectId(book_id)},
    )
    if result:
        return RedirectResponse(url="/")
    return {"message": "failure"}
