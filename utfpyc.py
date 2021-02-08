import argparse
import dis
import struct

from importlib._bootstrap_external import MAGIC_NUMBER

par = argparse.ArgumentParser()
par.add_argument('--filename', help='set alternate co_filename', default='')
par.add_argument('infile', type=argparse.FileType('rb'))
par.add_argument('outfile', type=argparse.FileType('wb'))

arg = par.parse_args()

with arg.infile as fp:
    codeobj = compile(fp.read(), arg.filename, 'single').replace(co_lnotab=b'')

dis.dis(codeobj)
for x in dir(codeobj):
    if x[0] == 'c':
        print(x, getattr(codeobj, x))

places = {}
newcode = []
bcode = dis.Bytecode(codeobj)
for x in bcode:
    if x.opcode >= 0x80:  # thankfully all opcodes are currently < 0xc0
        val = 0xc3
        if x.arg and 0x80 <= x.arg < 0xc0:  # escape arg as well
            val = 0xe1
        if newcode[-1:] == [None]:
            newcode[-1] = val
        else:
            newcode.extend((dis.opmap['NOP'], 0, dis.opmap['NOP'], val))
    if newcode[-1:] == [None]:
        newcode[-1] = 0
    places[x.offset] = len(newcode)
    newcode.extend((x.opcode, x.arg))

if newcode[-1:] == [None]:
    newcode[-1] = 0

for x in bcode:
    if x.opcode in dis.hasjrel or x.opcode in dis.hasjabs:
        pl = places[x.offset]
        v = places[x.argval]
        if x.opcode in dis.hasjrel:
            v -= pl + 2
        newcode[pl + 1] = v
newcode = bytes(newcode)
print(repr(newcode.decode()))

codeobj = codeobj.replace(co_code=newcode)
dis.dis(codeobj)

class NorefMarshalDumper:
    single = {
        None: b'N',
    }

    def __init__(self, fp):
        self.fp = fp

    def u32(self, i):
        self.fp.write(struct.pack('<I', i))

    def u8(self, i):
        self.fp.write(struct.pack('<B', i))

    def dump(self, obj):
        if obj in self.single:
            self.fp.write(self.single[obj])
        else:
            getattr(self, 'dump_' + type(obj).__name__)(obj)

    def dump_int(self, i):
        self.fp.write(b'I')
        self.u32(i)

    def dump_str(self, s):
        self.fp.write(b'z')
        self.u8(len(s))
        self.fp.write(s.encode())

    def dump_bytes(self, b):
        self.fp.write(b's')
        self.u32(len(b))
        self.fp.write(b)

    def dump_tuple(self, t):
        self.fp.write(b')')
        self.u8(len(t))
        for x in t:
          self.dump(x)

    def dump_code(self, co):
        self.fp.write(b'c')
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


with arg.outfile as fp:
    fp.write(MAGIC_NUMBER)
    fp.truncate(16)
    fp.seek(16)
    # like marshal.dump(codeobj, fp), but no remembering and references
    NorefMarshalDumper(fp).dump(codeobj)
