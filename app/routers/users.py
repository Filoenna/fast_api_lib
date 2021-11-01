from fastapi import APIRouter, status, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from fastapi.responses import RedirectResponse
from starlette.responses import HTMLResponse


import os

from app.webapps.auth.forms import LoginForm

from ..db.session import db
from ..schemas.users import UserInDB
from ..core.security import (
    get_password_hash,
    login_for_access_token,
)

templates = Jinja2Templates(directory="front/templates")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

users_collection = db.users
template_directory = "auth/login.html"


@router.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse(template_directory, {"request": request})


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request):
    form = LoginForm(request)
    await form.load_data()
    if await form.is_valid():
        try:
            form.__dict__.update(msg="Login Succesfull :)")
            response = templates.TemplateResponse(template_directory, form.__dict__)
            login_for_access_token(response=response, form_data=form)
            return response
        except HTTPException:
            form.__dict__.update(msg="")
            form.__dict__.get("errors").append("Incorrect Email or Password")
            return templates.TemplateResponse(template_directory, form.__dict__)
    return templates.TemplateResponse(template_directory, form.__dict__)


@router.get("/")
def get_users():
    users = users_collection.find({})
    users_list = []
    for user in users:
        users_list.append(UserInDB(**user))
    return users_list


@router.post("/")
def create_user(user: UserInDB):
    user.hashed_password = get_password_hash(user.hashed_password)
    user.disabled = False
    if not user.email:
        user.email = ""
    users_collection.insert_one(user.dict())
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
