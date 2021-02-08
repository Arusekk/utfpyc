
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
