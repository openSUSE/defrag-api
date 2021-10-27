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

import os
import pkgutil
from collections import Counter
from typing import List
from defrag import LOGGER, modules

def discover_modules(path: str) -> List[str]:
    pkgpath = os.path.dirname(path)
    discovered_modules = [name.lower() for _, name, _ in pkgutil.iter_modules([pkgpath])]
    duplicates = [name for name, count in Counter(discovered_modules).items() if count > 1]
    if duplicates:
        raise Exception(f"Two modules with the same name were declared: {str(duplicates)}")
    return discovered_modules

ALL_MODULES = sorted(discover_modules(modules.__file__))
TO_INCLUDE = []
LOADED = TO_INCLUDE or ALL_MODULES
LOGGER.info("Modules to load: %s", str(LOADED))