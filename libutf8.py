
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


def invalid(bytestring):
    try:
        bytestring.decode()
    except UnicodeDecodeError:
        return True
    return False


def maybe_bigger(num):
    while invalidu32(num):
        num += 1
    return num
