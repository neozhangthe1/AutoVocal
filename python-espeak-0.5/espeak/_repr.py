# For internal usage only
# -*- coding: utf-8 -*-

#
# Python bindings for the eSpeak speech synthesizer
#
# Copyright © 2009 Siegfried-Angel Gevatter Pujals <rainct@ubuntu.com>
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

class Storage(object):
    """This is an empty class to store data in it."""
    
    def __init__(self, dict={}):
        for name, value in dict.items():
            setattr(self, name, value)
    
    def __repr__(self):
        return str(vars(self))

class Voice(Storage): pass
