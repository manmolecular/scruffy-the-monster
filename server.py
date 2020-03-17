from aiohttp import web
from aiohttp_session import SimpleCookieStorage, session_middleware
from aiohttp_security import (
    check_authorized,
    remember,
    forget,
    SessionIdentityPolicy,
    setup,
)
from aiohttp_security.abc import AbstractAuthorizationPolicy
from aiohttp_swagger import *
from db.database import engine
from db import models
from handlers import crud, schemas
from config.defaults import RaceConditionRate
from asyncio import sleep
from json.decoder import JSONDecodeError
from pathlib import Path
from config.defaults import Config

routes = web.RouteTableDef()

MONSTERS = {}
USERS = {}


class AuthorizationPolicy(AbstractAuthorizationPolicy):
    async def authorized_userid(self, identity):
        return crud.get_user_id(username=identity)

    async def permits(self, identity, permission, context=None):
        pass


@routes.post("/register")
async def register(request):
    try:
        data = await request.json()
    except JSONDecodeError as invalid_json:
        return web.json_response(
            {
                "status": "error",
                "msg": "Request body is invalid. Use JSON with username/password",
            }
        )
    except Exception as unexp_err:
        return web.json_response({"status": "error", "msg": "Unexpected error"})

    try:
        user_schema = schemas.UserCreate(**data)
    except Exception as invalid_schema:
        return web.json_response(
            {
                "status": "error",
                "msg": "Username and password must be between 5 and 10 chars",
            }
        )

    try:
        return web.json_response(crud.create_user(user_schema))
    except Exception as create_user_err:
        return web.json_response(
            {"status": "error", "msg": "Can not create user, unexpected error"}
        )


@routes.post("/login")
async def login(request):
    try:
        data = await request.json()
    except JSONDecodeError as invalid_json:
        return web.json_response(
            {
                "status": "error",
                "msg": "Request body is invalid. Use JSON with username/password",
            }
        )
    except Exception as unexp_err:
        return web.json_response({"status": "error", "msg": "Unexpected error"})

    try:
        user_schema = schemas.UserLogin(**data)
    except Exception as invalid_schema:
        return web.json_response({"status": "error", "msg": "Invalid user schema"})

    try:
        success_login = crud.check_user_credentials(user_schema)
    except Exception as login_err:
        return web.json_response(
            {"status": "error", "msg": "Can not login, unexpected error"}
        )

    if not success_login:
        return web.json_response(
            {"status": "error", "msg": "wrong username or password"}
        )

    try:
        await remember(request, web.HTTPFound("/"), data.get("username"))
    except Exception as remember_user_err:
        return web.json_response(
            {
                "status": "error",
                "msg": "Can not remember user, problems with authentication",
            }
        )
    raise web.HTTPFound("/monster")


@routes.get("/monster", allow_head=False)
async def get_monster(request):
    user_id = await check_authorized(request)
    if not user_id:
        return web.json_response({"status": "error", "msg": "Not authorized"})
    try:
        crud.create_user_monster(monster=schemas.MonsterCreate(), user_id=user_id)
    except Exception as create_monster_err:
        return web.json_response(
            {
                "status": "error",
                "msg": "Can not create Monster for user! Try one more time?",
            }
        )
    return web.json_response(
        {"status": "success", "msg": "Arrrgh! Monster attacks you!"}
    )


@routes.get("/status", allow_head=False)
async def status(request):
    user_id = await check_authorized(request)
    if not user_id:
        return web.json_response({"status": "error", "msg": "You are not authorized"})
    user_stats = crud.get_user_stats(user_id)
    USERS.update({user_stats.get("id"): user_stats.get("health")})
    # What if monster is not created yet? Let user know about it
    try:
        monster_stats = crud.get_monster_stats(user_id)
        MONSTERS.update({monster_stats.get("id"): monster_stats.get("health")})
    except:
        return web.json_response(
            {
                "status": "error",
                "msg": "Everything is calm... Maybe you can find some monsters?",
            }
        )
    return web.json_response({"user_stats": user_stats, "monster_stats": monster_stats})


@routes.get("/flush", allow_head=False)
async def flush(request):
    user_id = await check_authorized(request)
    if not user_id:
        return web.json_response({"status": "error", "msg": "You are not authorized"})
    try:
        del USERS[user_id]
        del MONSTERS[crud.get_monster_id(user_id)]
    except Exception as del_err:
        return web.json_response(
            {
                "status": "error",
                "msg": "Can not clean-up after your monster... Or after you",
            }
        )
    return web.json_response(
        {"status": "success", "msg": "Your temporary information cleaned-up"}
    )


@routes.get("/logout", allow_head=False)
async def logout(request):
    await flush(request)
    try:
        await forget(request, web.HTTPFound("/"))
    except Exception as forget_user_err:
        return web.json_response(
            {
                "status": "error",
                "msg": "This user is unforgetable... No, really. Can not logout",
            }
        )
    raise web.json_response({"status": "success", "msg": "You are logged out"})


@routes.get("/hit", allow_head=False)
async def hit(request):
    user_id = await check_authorized(request)
    if not user_id:
        return web.json_response({"status": "error", "msg": "You are not authorized"})

    try:
        monster_stats = crud.get_monster_stats(user_id)
        user_stats = crud.get_user_stats(user_id)
    except Exception as get_stats_err:
        return web.json_response(
            {"status": "error", "msg": "Can not get stats - you are dead or alive!"}
        )

    monster_health = MONSTERS.get(monster_stats.get("id")) or monster_stats.get(
        "health"
    )
    user_health = USERS.get(user_stats.get("id")) or user_stats.get("health")

    monster_health -= user_stats.get("strength")
    if monster_health < 0:
        monster_health = 0
    user_health -= monster_stats.get("strength")
    if user_health < 0:
        user_health = 0

    try:
        MONSTERS.update({monster_stats.get("id"): monster_health})
        await sleep(RaceConditionRate.ATTACK_TIME)
        USERS.update({user_stats.get("id"): user_health})
        await sleep(RaceConditionRate.ATTACK_TIME)
    except Exception as update_health_err:
        return web.json_response(
            {"status": "error", "msg": "Some hits are missed! Take a breath, warrior!"}
        )

    try:
        crud.update_health_stats(user_id, monster_health, user_health)
    except:
        return web.json_response(
            {
                "status": "error",
                "msg": "Can not save new hits-stats in db. You are too fast",
            }
        )

    if monster_health == 0 and user_health > 0:
        return web.json_response(
            {"status": "win", "msg": "Congratulations! Monster is defeated!"}
        )
    if user_health == 0 and monster_health > 0:
        return web.json_response({"status": "fail", "msg": "Oh no! Monster eats you!"})
    if user_health == 0 and monster_health == 0:
        return web.json_response({"status": "finish", "msg": "Battle is over!"})
    return web.json_response(
        {"user_health": user_health, "monster_health": monster_health}
    )


@routes.get("/", allow_head=False)
async def main(request):
    raise web.HTTPFound("/doc")


async def _create_db_path():
    Path(Config.SQLALCHEMY_URL.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)


async def make_app():
    await _create_db_path()
    models.Base.metadata.create_all(bind=engine)
    middleware = session_middleware(SimpleCookieStorage())
    app = web.Application(middlewares=[middleware])
    app.add_routes(routes)

    policy = SessionIdentityPolicy()
    setup(app, policy, AuthorizationPolicy())

    setup_swagger(
        app,
        swagger_from_file="data/swagger/swagger.yml",
        swagger_url="/doc",
        ui_version=3,
    )

    return app


if __name__ == "__main__":
    web.run_app(make_app(), port=9000)
