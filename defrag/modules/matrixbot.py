# Defrag - centralized API for the openSUSE Infrastructure
# Copyright (C) 2021 openSUSE contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from os import environ as env
import asyncio
from nio import AsyncClient, SyncResponse, RoomMessageText

__MOD_NAME__ = "matrixbot"


async def login():
    client = AsyncClient("https://matrix.opensuse.org",
                         "@nycticorax:opensuse.org")
    login_methods = await client.login_info()
    if "m.login.token" in login_methods.__dict__["flows"]:
        print("Proceeding with token-based flow...")
        response = await client.login(token=env["OS_MATRIX_BOT_TOKEN"])
        print(response)
    await client.close()


if __name__ == "__main__":
    asyncio.run(login())
