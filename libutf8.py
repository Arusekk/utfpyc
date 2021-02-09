# libutf8.py - routines for object-oriented UTF-8 manipulation
# Copyright (C) 2021  Arusekk
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import struct
from enum import IntEnum


class U8(IntEnum):
    ascii, cont, start2, start3, start4, invalid = range(6)


class u8char(int):
    def __new__(cls, val):
        if val is not None:
            return int.__new__(cls, val)

    @property
    def type(self):
        if self < 0x80:
            return U8.ascii
        if self < 0xc0:
            return U8.cont
        if self < 0xe0:
            return U8.start2
        if self < 0xf0:
            return U8.start3
        if self < 0xf8:
            return U8.start4
        return U8.invalid

    @property
    def ascii(self):
        return self.type == U8.ascii

    @property
    def cont(self):
        return self.type == U8.cont

    @property
    def start(self):
        return self.type >= U8.start2

    @property
    def start2(self):
        return self.type == U8.start2

    @property
    def start3(self):
        return self.type >= U8.start3

    @property
    def start4(self):
        return self.type == U8.start4


def invalidu32(num):
    return invalid(struct.pack('<I', num))


def hexdump(bs):
    print(''.join(hexdump_iter(bs)))


def hexdump_iter(bs):
    line = ["  "] * 16
    for i, x in enumerate(bs):
        x = u8char(x)
        line[i & 15] = f'\33[1;3{x.type + 1}m{x:02x}\33[m'
        if i % 16 == 15:
            yield f'{i//16:07x}0 {" ".join(line)}\n'
            line = ["  "] * 16
    yield f'{(i+1)//16:07x}0 {" ".join(line)}\n'


def invalid(bytestring, debug=False):
    try:
        bytestring.decode()
    except UnicodeDecodeError:
        if debug:
            hexdump(bytestring)
        return True
    return False


def maybe_bigger(num):
    while invalidu32(num):
        num += 1
    return num
