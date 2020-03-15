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
from database import engine
import models
import crud
import schemas
from defaults import RaceConditionRate
from asyncio import sleep

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
    """
    ---
    description: This endpoint allows you to register in this game.
    tags:
    - Action
    produces:
    - application/json
    responses:
        "200":
            description: successful registration or information about error
    """
    data = await request.json()
    return web.json_response(crud.create_user(user=schemas.UserCreate(**data)))


@routes.post("/login")
async def login(request):
    """
    ---
    description: This endpoint allows you to login into this game. You need to be registered first.
    tags:
    - Action
    produces:
    - application/json
    responses:
        "200":
            description: successful login or information about error
    """
    data = await request.json()
    success_login = crud.check_user_credentials(user=schemas.UserLogin(**data))
    if not success_login:
        return web.json_response(
            {"status": "error", "msg": "wrong username or password"}
        )
    await remember(request, web.HTTPFound("/"), data.get("username"))
    user_id = crud.get_user_id(data.get("username"))
    crud.create_user_monster(monster=schemas.MonsterCreate(), user_id=user_id)
    raise web.HTTPFound("/status")


@routes.get("/status", allow_head=False)
async def status(request):
    """
    ---
    description: This endpoint returns your current stats
    tags:
    - Action
    produces:
    - application/json
    responses:
        "200":
            description: your current game stats
    """
    user_id = await check_authorized(request)
    if not user_id:
        return web.json_response({"status": "error", "msg": "not authorized"})
    user_stats = crud.get_user_stats(user_id)
    monster_stats = crud.get_monster_stats(user_id)
    MONSTERS.update({monster_stats.get("id"): monster_stats.get("health")})
    USERS.update({user_stats.get("id"): user_stats.get("health")})
    return web.json_response({"user": user_stats, "monster": monster_stats})


@routes.get("/flush", allow_head=False)
async def flush(request):
    """
    ---
    description: This endpoint allows you clear your temp information from memory
    tags:
    - Action
    produces:
    - application/json
    responses:
        "200":
            description: successful clean-up
    """
    user_id = await check_authorized(request)
    if not user_id:
        return web.json_response({"status": "error", "msg": "not authorized"})
    del USERS[user_id]
    del MONSTERS[crud.get_monster_id(user_id)]


@routes.get("/logout", allow_head=False)
async def logout(request):
    """
    ---
    description: This endpoint logs you out of this game
    tags:
    - Action
    produces:
    - application/json
    responses:
        "200":
            description: successful logout
    """
    await flush(request)
    redirect_response = web.HTTPFound("/")
    await forget(request, redirect_response)
    raise redirect_response


@routes.get("/hit", allow_head=False)
async def hit(request):
    """
    ---
    description: This endpoint allows you to hit your monster!
    tags:
    - Action
    produces:
    - application/json
    responses:
        "200":
            description: you successfully hit your monster
    """
    user_id = await check_authorized(request)
    if not user_id:
        return web.json_response({"status": "error", "msg": "not authorized"})

    monster_stats = crud.get_monster_stats(user_id)
    user_stats = crud.get_user_stats(user_id)

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

    MONSTERS.update({monster_stats.get("id"): monster_health})
    await sleep(RaceConditionRate.ATTACK_TIME)
    USERS.update({user_stats.get("id"): user_health})
    await sleep(RaceConditionRate.ATTACK_TIME)

    crud.update_health_stats(user_id, monster_health, user_health)

    if monster_health == 0 and user_health > 0:
        return web.json_response(
            {"status": "win", "msg": "Congratulations! Monster is defeated!"}
        )
    if user_health == 0 and monster_health >= 0:
        return web.json_response({"status": "fail", "msg": "Oh no! Monster eats you!"})
    return web.json_response(
        {"user_health": user_health, "monster_health": monster_health}
    )


@routes.get("/", allow_head=False)
async def main(request):
    """
    ---
    description: This endpoint just redirects you to documentation
    tags:
    - Documentation
    produces:
    - text/plain
    responses:
        "200":
            description: successful operation
    """
    raise web.HTTPFound("/doc")


async def make_app():
    models.Base.metadata.create_all(bind=engine)
    middleware = session_middleware(SimpleCookieStorage())
    app = web.Application(middlewares=[middleware])
    app.add_routes(routes)

    policy = SessionIdentityPolicy()
    setup(app, policy, AuthorizationPolicy())

    setup_swagger(
        app,
        description="Hello, stranger! "
        "You need to defeat that scary monster or he will eats you! "
        "Hit him as hard as you can!",
        title="Scruffy The Monster",
        api_version="1.0.0",
        contact="",
        swagger_url="/doc",
        ui_version=2,
    )

    return app


if __name__ == "__main__":
    web.run_app(make_app(), port=9000)
