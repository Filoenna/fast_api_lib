import os
import requests

from fastapi import APIRouter, status, Depends, HTTPException
from pymongo import ReturnDocument

from fastapi.responses import RedirectResponse
from bson.objectid import ObjectId

from ..dependencies import get_token_header
from ..db.session import db
from ..schemas.books import Book


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

router = APIRouter(
    prefix="/books",
    tags=["books"],
    responses={404: {"description": "Not found"}},
)


books_collection = db.books


response = requests.get(
    f"https://www.googleapis.com/books/v1/volumes?q=sisters+inauthor:pratchett&key={GOOGLE_API_KEY}"
)


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
