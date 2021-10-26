from fastapi import APIRouter, status, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from fastapi.responses import RedirectResponse
from starlette.responses import HTMLResponse

from jose import JWTError, jwt
from typing import Optional
from datetime import datetime, timedelta
from pymongo import ReturnDocument
from pydantic import BaseModel, Field

import os

from ..db.session import db
from ..schemas.users import User, UserInDB, UserLoginSchema

templates = Jinja2Templates(directory="front/templates")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

users_collection = db.users

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db, username: str):
    user = db.find_one({"username": username})
    if user:
        return UserInDB(**user)


def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(users_collection, username=token_data.username)
    if not user:
        raise credentials_exception
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(users_collection, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.post("/login", response_class=HTMLResponse)
def login(request: Request, user: UserLoginSchema = Depends(get_current_active_user)):
    return templates.TemplateResponse(
        "index.html", {"request": request, "username": user.username}
    )


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
    users_collection.insert_one(user.dict())
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
