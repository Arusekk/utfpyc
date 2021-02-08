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


def invalid(bytestring):
    try:
        bytestring.decode()
    except UnicodeDecodeError:
        return True
    return False


ANY_ASCII = ord('S')


def transcode(codeobj, force=False, verbose=False):
    places = {}
    newcode = []

    bcode = dis.Bytecode(codeobj)
    nextcode = iter(bcode)
    next(nextcode)

    state = U8.ascii
    for x, nextx in zip_longest(bcode, nextcode):
        startlen = len(newcode)

        if not nextx:
            nextx = dis.Instruction(opname=None, opcode=None, arg=None, argval=None, argrepr=None, offset=None, starts_line=None, is_jump_target=None)

        opcode, arg, nextopcode, nextarg = map(u8char,
            (x.opcode, x.arg, nextx.opcode, nextx.arg))

        need_close = (   state >= U8.start2 and not opcode.cont
                      or state >= U8.start3 and not arg.cont
                      or state == U8.start2 and arg.cont)
        need_ignore = False

        if verbose > 2:
            print(f'{x=}, {state=}, {need_close=}')
        if need_close and state >= U8.start2:
            if state == U8.start2:
                newcode.extend((dis.EXTENDED_ARG, 0))
                state = U8.ascii
            elif state == U8.start3:
                newcode.extend((dis.EXTENDED_ARG, 0x80))
                need_ignore = True
                state = U8.cont
            elif state == U8.start4:
                newcode.extend((dis.EXTENDED_ARG, 0x80, dis.EXTENDED_ARG, 0))
                need_ignore = True
                state = U8.ascii

        if opcode.cont and state < U8.start2:  # thankfully all opcodes are currently < 0xc0
            val = 0xc3
            if arg.cont:
                val = 0xe1  # escape arg as well
                if nextopcode.cont and not nextarg.cont:
                    val = 0xf1  # escape next opcode as well
            if newcode[-1:] == [None]:
                newcode[-1] = val
            else:
                newcode.extend((dis.opmap['NOP'], val))
                need_ignore = False
            state = u8char(val).type

        if need_ignore and x.opcode >= dis.HAVE_ARGUMENT:
            newcode.extend((dis.opmap['NOP'], None))

        if newcode[-1:] == [None]:
            newcode[-1] = ANY_ASCII

        places[x.offset] = startlen, len(newcode)
        newcode.extend((x.opcode, x.arg))

        if not arg:
            state = U8.ascii
        elif arg.start:
            state = arg.type
        elif opcode.start:  # impossible
            state = opcode.type - 1
        elif state >= U8.start2:
            state -= 2

    if newcode[-1:] == [None]:
        newcode[-1] = ANY_ASCII

    for x in bcode:
        if x.opcode in dis.hasjrel or x.opcode in dis.hasjabs:
            _, pl = places[x.offset]
            vmin, vmax = places[x.argval]
            if x.opcode in dis.hasjrel:
                vmin -= pl + 2
                vmax -= pl + 2
            newcode[pl + 1] = vmin

    # adjust code length
    while invalid(struct.pack('<I', len(newcode))):
        newcode.append(ANY_ASCII)
    newcode = bytes(newcode)

    # adjust stacksize
    co_stacksize = codeobj.co_stacksize
    while invalid(struct.pack('<I', co_stacksize)):
        co_stacksize += 1

    codeobj = codeobj.replace(co_code=newcode, co_lnotab=b'', co_stacksize=co_stacksize)
    if verbose:
        if verbose > 1:
            dis.dis(codeobj)
        print(repr(newcode))
        print(repr(newcode.decode()))

    assert force or newcode.decode()  # make sure UTF-8 magic really worked

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
        self.u32(i)

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
        co = transcode(co, self.force, self.verbose)
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
    par.add_argument('--filename', help='set alternate co_filename', default=None)
    par.add_argument('--mode', help='set alternate compile mode', default='exec', choices=['single', 'exec'])
    par.add_argument('-v', '--verbose', default=0, action='count')
    par.add_argument('-f', '--force', action='store_true', help='force write even if UTF-8 cannot be fully acheived')
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
