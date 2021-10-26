from typing import Optional, Literal
from pydantic import BaseModel, Field


class Book(BaseModel):

    title: str
    description: Optional[str]
    author: str = Field(..., max_length=100)
    status: Literal["available", "rented"] = "available"
