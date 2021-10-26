from pydantic import BaseModel
from typing import Optional


class User(BaseModel):

    username: str
    email: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str


class UserLoginSchema(BaseModel):
    username: str
    password: str
