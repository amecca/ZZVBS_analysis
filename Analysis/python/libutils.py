# Helpers to load code from shared libraries into ROOT

import os
import logging
import ROOT


def load_lib(path):
    err = ROOT.gInterpreter.Load(path)
    if(err != 0):
        raise RuntimeError('Error %s loading shared library "%s"', err, path)
    logging.debug('Loaded library %s', path)


def find_lib(name, libdir='../lib'):
    for ext in ('.so', '_c.so', '_cpp.so'):
        p = os.path.join(libdir, name+ext)
        if(os.path.exists(p)):
            break
    else:
        raise FileNotFoundError('Could not .so named "%s" in "%s"', name, libdir)
    return p


def find_load_lib(name, **kwargs):
    load_lib(find_lib(name, **kwargs))
