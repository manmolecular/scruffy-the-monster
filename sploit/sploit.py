#!/usr/bin/env python3

import asyncio
import aiohttp
from json import dumps
from asyncio_pool import AioPool
from random import randrange


_session = None


async def get_session():
    global _session
    if _session is None:
        # https://github.com/aio-libs/aiohttp/issues/1183
        _session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))
    return _session


class DefaultProxy:
    PROXY = "http://127.0.0.1:8080"


class DefaultValues:
    HOST = "127.0.0.1"
    PORT = 9001
    USERNAME = "test"
    PASSWORD = USERNAME
    POOL_SIZE = 10
    REQUESTS_QUANTITY = 50
    RAND_RANGE = 99


class PrepareHits:
    def __init__(
        self, session, host: str = DefaultValues.HOST, port: int = DefaultValues.PORT
    ):
        self.host = host
        self.port = str(port)
        self.base_url = f"http://{self.host}:{self.port}"
        self.session = session
        self.random = str(randrange(DefaultValues.RAND_RANGE))

    async def register(
        self,
        username: str = DefaultValues.USERNAME,
        password: str = DefaultValues.PASSWORD,
    ):
        payload = {
            "username": f"{username}-{self.random}",
            "password": f"{password}-{self.random}",
        }
        async with self.session.post(
            f"{self.base_url}/register", data=dumps(payload).encode()
        ) as resp:
            print(resp.status, await resp.json())

    async def login(
        self,
        username: str = DefaultValues.USERNAME,
        password: str = DefaultValues.PASSWORD,
    ):
        payload = {
            "username": f"{username}-{self.random}",
            "password": f"{password}-{self.random}",
        }
        async with self.session.post(
            f"{self.base_url}/login", data=dumps(payload).encode()
        ) as resp:
            print(resp.status, await resp.json())

    async def make_hit(self):
        async with self.session.get(f"{self.base_url}/hit") as resp:
            return resp.status, await resp.json()


async def main():
    async with await get_session() as session:
        preparation_steps = PrepareHits(session)
        await preparation_steps.register()
        await preparation_steps.login()
        futures = []
        async with AioPool(size=DefaultValues.POOL_SIZE) as pool:
            try:
                for _ in range(DefaultValues.REQUESTS_QUANTITY):
                    future = await pool.spawn(preparation_steps.make_hit())
                    futures.append(future)
                for fut in futures:
                    print(*fut.result())
            except asyncio.InvalidStateError:
                return


if __name__ == "__main__":
    asyncio.run(main())
