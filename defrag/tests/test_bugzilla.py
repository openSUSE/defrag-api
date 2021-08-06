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

from defrag import app
from fastapi.testclient import TestClient
import defrag.modules.bugs  # otherwise the module is not loaded


def test_get_bug_info():
    client = TestClient(app)
    response = client.get("/bugs/bug/?id=1178338")
    response = client.get("/bugs/bug/?id=1178338")
    expected = {
        "id": 1178338,
        "url": "https://bugzilla.opensuse.org/show_bug.cgi?id=1178338",
        "product": "openSUSE Tumbleweed",
        "component": "Installation",
        "status": "CONFIRMED",
        "summary": "[installation-images] Support for 64-bit processors on motherboards with 32-bit UEFI (mixed-mode support)"
    }
    assert response.json() == expected
