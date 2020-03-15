from sqlalchemy.orm import Session
from database import SessionLocal
from typing import AnyStr

import models
import schemas


def create_user(user: schemas.UserCreate, session: Session = SessionLocal()):
    db_user = models.User(**user.dict())
    session.add(db_user)
    msg = {"status": "success", "msg": f"user {user.username} created"}
    try:
        session.commit()
        session.refresh(db_user)
    except Exception:
        session.rollback()
        msg = {"status": "error", "msg": f"username {user.username} already taken"}
    finally:
        session.close()
        return msg


def get_user_id(username: AnyStr, session: Session = SessionLocal()):
    return (
        session.query(models.User).filter(models.User.username == username).first().id
    )


def check_user_credentials(user: schemas.UserLogin, session: Session = SessionLocal()):
    db_user = (
        session.query(models.User).filter(models.User.username == user.username).first()
    )
    if not db_user:
        return
    return user.username == db_user.username and user.password == db_user.password


def get_user_stats(user_id: int, session: Session = SessionLocal()):
    user = session.query(models.User).filter(models.User.id == user_id).first()
    return {
        "id": int(user.id),
        "health": int(user.health),
        "hits": int(user.hits),
        "strength": int(user.strength),
    }


def get_monster_stats(user_id: int, session: Session = SessionLocal()):
    monster = (
        session.query(models.Monster).filter(models.Monster.owner_id == user_id).first()
    )
    return {
        "id": int(monster.id),
        "health": int(monster.health),
        "hits": int(monster.hits),
        "strength": int(monster.strength),
    }


def update_health_stats(
    user_id: int,
    monster_health: int,
    user_health: int,
    session: Session = SessionLocal(),
):
    session.query(models.Monster).filter(models.Monster.owner_id == user_id).update(
        {"health": monster_health}
    )
    session.query(models.User).filter(models.User.id == user_id).update(
        {"health": user_health}
    )
    try:
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def get_monster_id(user_id: int, session: Session = SessionLocal()):
    return (
        session.query(models.Monster)
        .filter(models.Monster.owner_id == user_id)
        .first()
        .id
    )


def create_user_monster(
    monster: schemas.MonsterCreate, user_id: int, session: Session = SessionLocal()
):
    db_monster = models.Monster(**monster.dict(), owner_id=user_id)
    session.add(db_monster)
    msg = {"status": "success", "msg": f"monster {monster.monstername} created"}
    try:
        session.commit()
        session.refresh(db_monster)
    except Exception:
        session.rollback()
        msg = {
            "status": "error",
            "msg": f"can not create monster {monster.monstername}",
        }
    finally:
        session.close()
        return msg
