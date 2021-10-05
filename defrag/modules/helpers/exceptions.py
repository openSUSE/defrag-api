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

from typing import Any, Dict, List, Optional, Union


class DefragException(Exception):
    '''Base class for other exceptions'''

    def __init__(self, message=""):
        self.message = message
        super().__init__(self.message)


class BugzillaException(DefragException):
    '''Raised when a python-bugzilla error occures.'''
    pass


class ParsingException(DefragException):
    '''Raised when something goes wrong while parsing a webpage.'''
    pass


class NetworkException(DefragException):
    '''Raised when a network error occures.'''
    pass