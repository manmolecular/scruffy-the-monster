from pydantic import BaseModel, Field
from typing import List

from config.defaults import UserDefaults, MonsterDefaults


class UserBase(BaseModel):
    username: str = Field(..., min_length=5, max_length=10)
    health: int = Field(UserDefaults.HEALTH, ge=0, le=100)
    strength: int = Field(UserDefaults.STRENGTH, ge=0, le=20)
    hits: int = Field(UserDefaults.HITS, ge=0, le=5)


class UserCreate(UserBase):
    password: str = Field(..., min_length=5, max_length=10)


class UserLogin(UserBase):
    password: str = Field(..., min_length=5, max_length=10)


class MonsterBase(BaseModel):
    monstername: str = Field(MonsterDefaults.MONSTERNAME, max_length=10)
    health: int = Field(MonsterDefaults.HEALTH, ge=0, le=100)
    strength: int = Field(MonsterDefaults.STRENGTH, ge=0, le=50)
    hits: int = Field(MonsterDefaults.HITS, ge=0, le=100)


class MonsterCreate(MonsterBase):
    pass


class Monster(MonsterBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True


class User(UserCreate):
    id: int
    items: List[Monster] = []

    class Config:
        orm_mode = True
