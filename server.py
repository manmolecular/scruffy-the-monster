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
from json.decoder import JSONDecodeError

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
    try:
        data = await request.json()
    except JSONDecodeError as invalid_json:
        return web.json_response({"status": "error", "msg": "Request body is invalid. Use JSON with username/password"})
    except Exception as unexp_err:
        return web.json_response({"status": "error", "msg": "Unexpected error"})

    try:
        user_schema = schemas.UserCreate(**data)
    except Exception as invalid_schema:
        return web.json_response({"status": "error", "msg": "Invalid user schema"})

    try:
        return web.json_response(crud.create_user(user_schema))
    except Exception as create_user_err:
        return web.json_response({"status": "error", "msg": "Can not create user, unexpected error"})


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
    try:
        data = await request.json()
    except JSONDecodeError as invalid_json:
        return web.json_response({"status": "error", "msg": "Request body is invalid. Use JSON with username/password"})
    except Exception as unexp_err:
        return web.json_response({"status": "error", "msg": "Unexpected error"})

    try:
        user_schema = schemas.UserLogin(**data)
    except Exception as invalid_schema:
        return web.json_response({"status": "error", "msg": "Invalid user schema"})

    try:
        success_login = crud.check_user_credentials(user_schema)
    except Exception as login_err:
        return web.json_response({"status": "error", "msg": "Can not login, unexpected error"})

    if not success_login:
        return web.json_response(
            {"status": "error", "msg": "wrong username or password"}
        )

    try:
        await remember(request, web.HTTPFound("/"), data.get("username"))
    except Exception as remember_user_err:
        return web.json_response({"status": "error", "msg": "Can not remember user, problems with authentication"})
    raise web.HTTPFound("/monster")


@routes.get("/monster", allow_head=False)
async def get_monster(request):
    """
    ---
    description: This endpoint creates monster for you
    tags:
    - Action
    produces:
    - application/json
    responses:
        "200":
            description: your current game monster
    """
    user_id = await check_authorized(request)
    if not user_id:
        return web.json_response({"status": "error", "msg": "Not authorized"})
    try:
        crud.create_user_monster(monster=schemas.MonsterCreate(), user_id=user_id)
    except Exception as create_monster_err:
        return web.json_response({"status": "error", "msg": "Can not create Monster for user! Try one more time?"})
    return web.json_response({"status": "success", "msg": "Arrrgh! Monster attacks you!"})


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
        return web.json_response({"status": "error", "msg": "You are not authorized"})
    user_stats = crud.get_user_stats(user_id)
    USERS.update({user_stats.get("id"): user_stats.get("health")})
    # What if monster is not created yet? Let user know about it
    try:
        monster_stats = crud.get_monster_stats(user_id)
        MONSTERS.update({monster_stats.get("id"): monster_stats.get("health")})
    except:
        return web.json_response({"status": "error", "msg": "Everything is calm... Maybe you can find some monsters?"})
    return web.json_response({"user_stats": user_stats, "monster_stats": monster_stats})


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
        return web.json_response({"status": "error", "msg": "You are not authorized"})
    try:
        del USERS[user_id]
        del MONSTERS[crud.get_monster_id(user_id)]
    except Exception as del_err:
        return web.json_response({"status": "error", "msg": "Can not clean-up after your monster... Or after you"})


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
    try:
        await forget(request, redirect_response)
    except Exception as forget_user_err:
        return web.json_response({"status": "error", "msg": "This user is unforgetable... No, really. Can not logout"})
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
        return web.json_response({"status": "error", "msg": "You are not authorized"})

    try:
        monster_stats = crud.get_monster_stats(user_id)
        user_stats = crud.get_user_stats(user_id)
    except Exception as get_stats_err:
        return web.json_response({"status": "error", "msg": "Can not get stats - you are dead or alive!"})

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
        return web.json_response({"status": "error", "msg": "Some hits are missed! Take a breath, warrior!"})

    try:
        crud.update_health_stats(user_id, monster_health, user_health)
    except:
        return web.json_response({"status": "error", "msg": "Can not save new hits-stats in db. You are too fast"})

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
        ui_version=1,
    )

    return app


if __name__ == "__main__":
    web.run_app(make_app(), port=9000)
