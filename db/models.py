from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from db.database import Base
from config.defaults import UserDefaults, MonsterDefaults


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    health = Column(Integer, default=UserDefaults.HEALTH)
    strength = Column(Integer, default=UserDefaults.STRENGTH)
    hits = Column(Integer, default=UserDefaults.HITS)

    monsters = relationship("Monster", back_populates="owner")


class Monster(Base):
    __tablename__ = "monsters"

    id = Column(Integer, primary_key=True, index=True)
    monstername = Column(
        String, unique=False, index=True, default=MonsterDefaults.MONSTERNAME
    )
    health = Column(Integer, default=MonsterDefaults.HEALTH)
    strength = Column(Integer, default=MonsterDefaults.STRENGTH)
    hits = Column(Integer, default=MonsterDefaults.HITS)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="monsters")
