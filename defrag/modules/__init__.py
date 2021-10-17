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
from defrag import LOGGER, modules

pkgpath = os.path.dirname(modules.__file__)
discovered_modules = (name for _, name, _ in pkgutil.iter_modules([pkgpath]))
duplicates = [name for name, count in Counter(discovered_modules).items() if count > 1]
if duplicates:
    raise Exception(f"Two modules with the same name were declared: {str(duplicates)}")

ALL_MODULES = sorted(discovered_modules)
__all__ = ALL_MODULES + ["ALL_MODULES"]

LOGGER.info("Modules to load: %s", str(ALL_MODULES))
