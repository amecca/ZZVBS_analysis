# Helpers to load code from shared libraries into ROOT

import os
import logging
import ROOT


_ROOT_DIR_NAME = 'ZZVBS_analysis'


def find_root_dir():
    '''Find the top level directory of the project (ZZVBS_analysis)'''
    # Try CMSSW_BASE
    if('CMSSW_BASE' in os.environ):
        p = os.path.join(os.path.expandvars('$CMSSW_BASE'), 'src', _ROOT_DIR_NAME)
        if(os.path.exists(p)): return p

    # Try the current working directory path (for local installations)
    pwd_split = os.getcwd().split(os.sep)
    try:
        idx = pwd_split.index(_ROOT_DIR_NAME)
        p = '/'+os.path.join(*pwd_split[:idx+1])
        if(os.path.exists(p)): return p
    except ValueError: pass

    # Raise an error
    raise FileNotFoundError(_ROOT_DIR_NAME)


def load_lib(path):
    err = ROOT.gInterpreter.Load(path)
    if(err != 0):
        raise RuntimeError('Error %s loading shared library "%s"', err, path)
    logging.debug('Loaded library %s', path)


def find_lib(name, libdir=None, rel_libdir='Analysis/lib', rootdir=None):
    if libdir is None:
        if(rootdir is None): rootdir = find_root_dir()
        libdir = os.path.join(rootdir, rel_libdir)

    for ext in ('', '.so', '_c.so', '_cpp.so'):
        p = os.path.join(libdir, name+ext)
        if(os.path.exists(p)):
            return p
        else: logging.debug('path does not exist: %s', p)

    raise FileNotFoundError('Could not find .so named "%s" in "%s"' %(name, libdir))


def find_load_lib(name, **kwargs):
    load_lib(find_lib(name, **kwargs))
