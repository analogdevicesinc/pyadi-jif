# flake8: noqa
"""Bindings for the D2 Compiler"""

import ctypes
import os

loc = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(loc, "d2lib.so")

if not os.path.exists(lib_path):
    raise FileNotFoundError(f"Could not find {lib_path}")

library = ctypes.cdll.LoadLibrary(lib_path)

runme = library.runme
runme.argtypes = [ctypes.c_char_p]
runme.restype = ctypes.c_char_p


def compile(code: str) -> str:
    try:
        graph_bytes = runme(code.encode("utf-8"))
        return graph_bytes.decode("utf-8")
    except Exception as e:
        print(e)
        return None
