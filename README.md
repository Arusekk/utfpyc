# UTFPYC

Why not make .pyc files that are valid UTF-8 by the way?

Note: this only works best-effort and assumes you don't use
constants and literals that are not possible to encode this way.
It just makes sure that the code for code objects is a little better,
while longer and hopefully not changing its semantics.
It also clears the lnotab (line number information), because who needs it anyway.
In future versions it might be possible to build a useful lnotab
for debugging.

The code here is intended for use with CPython 3.9,
but should work with CPython 3.8-3.11 with no changes,
and with older wordcode CPythons just by tweaking the marshaller.

If necessary, it will be rewritten using the excellent [xdis] library.

[xdis]: https://github.com/rocky/python-xdis
