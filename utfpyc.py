#!/usr/bin/env python3

import dis
import os
import struct

from enum import IntEnum
from itertools import zip_longest
from importlib._bootstrap_external import MAGIC_NUMBER


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
    bytestring = struct.pack('<I', num)
    try:
        bytestring.decode()
    except UnicodeDecodeError:
        return True
    return False


def maybe_bigger(num):
    while invalidu32(num):
        num += 1
    return num


ANY_ASCII = ord('S')
empty_instr = dis.Instruction(
    opname=None, opcode=None, arg=None, argval=None, argrepr=None,
    offset=None, starts_line=None, is_jump_target=None)


class Transcoder:
    def __init__(self, codeobj, force=False, verbose=False):
        self.bcode = dis.Bytecode(codeobj)
        self.places = {}
        self.newcode = []
        self.codeobj = codeobj
        self.force = force
        self.verbose = verbose
        self.state = U8.ascii
        self.was_extended_arg = False
        self.nextcode = list(self.bcode)[1:]

    def maybe_insert_cont(self):
        if self.was_extended_arg:
            print('Warn: insert after ext arg would change semantics (1)')
        if self.state == U8.start2:
            self.newcode.extend((dis.EXTENDED_ARG, 0))
            self.state = U8.ascii
        if self.state == U8.start3:
            self.newcode.extend((dis.EXTENDED_ARG, 0x80))
            self.state = U8.cont
            self.need_ignore = True
        if self.state == U8.start4:
            self.newcode.extend((dis.EXTENDED_ARG, 0x80,
                                 dis.EXTENDED_ARG, 0))
            self.state = U8.ascii
            self.need_ignore = True

    def maybe_insert_start(self, val):
        if self.newcode[-1:] == [None]:
            self.newcode[-1] = val
        elif self.was_extended_arg:
            print('Warn: insert after ext arg would change semantics (2)')
            val = 0
        else:
            self.newcode.extend((dis.opmap['NOP'], val))
            self.need_ignore = False
        self.state = u8char(val).type

    def process(self, x, nextx):
        startlen = len(self.newcode)

        opcode, arg, nextopcode, nextarg = map(
            u8char,
            (x.opcode, x.arg, nextx.opcode, nextx.arg)
        )

        need_close = (self.state >= U8.start2 and not opcode.cont
                      or self.state >= U8.start3 and not arg.cont
                      or self.state == U8.start2 and arg.cont)
        self.need_ignore = False

        if self.verbose > 2:
            print(f'{x=}, {self.state=}, {need_close=}')

        if need_close and self.state >= U8.start2:
            self.maybe_insert_cont()

        # thankfully all opcodes are currently < 0xc0
        if opcode.cont and self.state < U8.start2:
            val = 0xc3
            if arg.cont:
                val = 0xe1  # escape arg as well
                if nextopcode.cont and not nextarg.cont:
                    val = 0xf1  # escape next opcode as well
            self.maybe_insert_start(val)

        if self.need_ignore and x.opcode >= dis.HAVE_ARGUMENT:
            self.newcode.extend((dis.opmap['NOP'], None))

        if self.newcode[-1:] == [None]:
            self.newcode[-1] = ANY_ASCII

        self.places[x.offset] = startlen, len(self.newcode)
        self.newcode.extend((x.opcode, x.arg))

        self.was_extended_arg = opcode == dis.EXTENDED_ARG

        if not arg:
            self.state = U8.ascii
        elif arg.start:
            self.state = arg.type
        elif opcode.start:  # impossible
            self.state = opcode.type - 1
        elif self.state >= U8.start2:
            self.state -= 2

    def adjumps(self):
        for x in self.bcode:
            if x.opcode in dis.hasjrel or x.opcode in dis.hasjabs:
                _, pl = self.places[x.offset]
                vmin, vmax = self.places[x.argval]
                if x.opcode in dis.hasjrel:
                    vmin -= pl + 2
                    vmax -= pl + 2
                if x.arg < vmin:
                    v = vmin
                elif x.arg > vmax:
                    v = vmax
                else:
                    continue

                oldrep = x.arg.to_bytes(4, 'little')
                newrep = v.to_bytes(4, 'little')
                while True:
                    self.newcode[pl + 1] = newrep[0]
                    oldrep = oldrep[1:]
                    newrep = newrep[1:]
                    if oldrep == newrep:
                        break
                    if not any(oldrep):
                        print('does not converge! try to tweak '
                              f'{self.codeobj.co_name} in '
                              f'{self.codeobj.co_filename}'
                              f':{self.codeobj.co_firstlineno}')
                        break
                    pl -= 2
                    assert self.newcode[pl] == dis.EXTENDED_ARG

    def transcode(self):
        for x, nextx in zip_longest(self.bcode, self.nextcode,
                                    fillvalue=empty_instr):
            self.process(x, nextx)

        if self.newcode[-1:] == [None]:
            self.newcode[-1] = ANY_ASCII

        self.adjumps()

        # adjust code length
        while invalidu32(len(self.newcode)):
            self.newcode.append(ANY_ASCII)
        newcode = bytes(self.newcode)

        # adjust stacksize
        co_stacksize = maybe_bigger(self.codeobj.co_stacksize)

        codeobj = self.codeobj.replace(co_code=newcode, co_lnotab=b'',
                                       co_stacksize=co_stacksize)
        if self.verbose:
            if self.verbose > 1:
                dis.dis(codeobj)
            print(repr(newcode))
            print(repr(newcode.decode()))

        # make sure UTF-8 magic really worked
        assert self.force or newcode.decode()

        return codeobj


class NorefMarshalDumper:
    single = {
        None: b'N',
        True: b'T',
        False: b'F',
        StopIteration: b'S',
        ...: b'.',
    }

    def __init__(self, fp, force=False, verbose=0):
        self.fp = fp
        self.verbose = verbose
        self.force = force

    def u32(self, i):
        self.write(struct.pack('<I', i))

    def s32(self, i):
        self.write(struct.pack('<i', i))

    def u8(self, i):
        self.write(struct.pack('<B', i))

    def write(self, bs):
        if not self.force:
            bs.decode()
        self.fp.write(bs)

    def dump(self, obj):
        if obj in self.single:
            self.write(self.single[obj])
        else:
            getattr(self, 'dump_' + type(obj).__name__)(obj)

    def dump_int(self, i):
        self.fp.write(b'i')
        self.s32(i)

    def dump_str(self, s):
        self.fp.write(b'z')
        self.u8(len(s))
        self.fp.write(s.encode())

    def dump_bytes(self, b):
        self.fp.write(b's')
        self.u32(len(b))
        self.write(b)

    def dump_tuple(self, t):
        self.fp.write(b')')
        self.u8(len(t))
        for x in t:
            self.dump(x)

    def dump_code(self, co):
        self.fp.write(b'c')
        co = Transcoder(co, self.force, self.verbose).transcode()
        self.u32(co.co_argcount)
        self.u32(co.co_posonlyargcount)
        self.u32(co.co_kwonlyargcount)
        self.u32(co.co_nlocals)
        self.u32(co.co_stacksize)
        self.u32(co.co_flags)
        self.dump(co.co_code)
        self.dump(co.co_consts)
        self.dump(co.co_names)
        self.dump(co.co_varnames)
        self.dump(co.co_freevars)
        self.dump(co.co_cellvars)
        self.dump(co.co_filename)
        self.dump(co.co_name)
        self.u32(co.co_firstlineno)
        self.dump(co.co_lnotab)


def main():
    import argparse

    par = argparse.ArgumentParser()
    par.add_argument('--filename', default=None,
                     help='set alternate co_filename')
    par.add_argument('--mode', default='exec', choices=['single', 'exec'],
                     help='set alternate compile mode')
    par.add_argument('-v', '--verbose', default=0, action='count')
    par.add_argument('-f', '--force', action='store_true',
                     help='force write even if UTF-8 cannot be fully acheived')
    par.add_argument('infile', type=argparse.FileType('rb'))
    par.add_argument('outfile', type=argparse.FileType('wb'))

    args = par.parse_args()

    if args.filename is None:
        args.filename = os.path.abspath(args.infile.name)

    with args.infile as fp:
        codeobj = compile(fp.read(), args.filename, args.mode)

    with args.outfile as fp:
        fp.write(MAGIC_NUMBER)
        fp.truncate(16)
        fp.seek(16)
        # like marshal.dump(codeobj, fp), but no remembering and references;
        # it also fixes up code whenever it can be made more UTF-8 valid
        NorefMarshalDumper(fp, args.force, args.verbose).dump(codeobj)


if __name__ == "__main__":
    main()
