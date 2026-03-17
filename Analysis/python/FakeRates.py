################################################################
# Wrapper around the C library FakeRates                       #
#                                                              #
# Author: Alberto Mecca (alberto.mecca@cern.ch)                #
# Initial revision: 2025-09-11                                 #
################################################################

import os

import warnings
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', category=UserWarning)
    # Suppress "No precompiled header available. This may affect performance"
    import cppyy

import libutils


_rootdir = libutils.find_root_dir()
_sopath = libutils.find_lib('FakeRates_cpp.so', rootdir=_rootdir)
_ZZAnalysis = os.path.join(_rootdir, '..',)
cppyy.add_include_path(os.path.join(_rootdir, 'Analysis/interface'))
cppyy.load_library(_sopath)


class FakeRates:
    '''Wrapper around the cppyy wrapper around the C++ object'''
    def __init__(self, year, method, dirname='$CMSSW_BASE/src/ZZAnalysis/AnalysisStep/data/FakeRates'):
        # TODO: pass debug to the C++ object (it doesn't lik Python's bools)
        dirname = os.path.expandvars(dirname)
        fname = 'FakeRates_{method}_{year}.root'.format(**locals())
        fpath = os.path.join(dirname, fname)
        self.obj = cppyy.gbl.FakeRates(fpath, method)

    def getFR(self, *args):
        val_err = self.obj.getFR(*args)
        return val_err.first, val_err.second

    def getFRlep(self, lep):
        return self.getFR(lep.pt, lep.eta, lep.id)


def test():
    import logging
    logging.basicConfig(format='%(levelname)s:%(module)s:%(funcName)s: %(message)s', level='DEBUG')

    frdir = os.path.join(_rootdir, '../ZZAnalysis/AnalysisStep/data/FakeRates')
    fr_obj_cppyy = cppyy.gbl.FakeRates(os.path.join(frdir, 'FakeRates_OS_2018.root'))
    fr_obj_wrap_OS = FakeRates(year=2018, method='OS')
    fr_obj_wrap_SS = FakeRates(year='2018', method='SS')
    print('FakeRates cppyy (OS):', fr_obj_cppyy)
    print('FakeRates wrap (OS) :', fr_obj_wrap_OS)

    fr_cppyy   = fr_obj_cppyy  .getFR(15, 1, 11)
    print('cppyy (OS) Ele eta=1, pt=15: [%.3f, %.3f]' %(fr_cppyy.first, fr_cppyy.second))
    print('wrap  (OS) Ele eta=1, pt=15: [%.3f, %.3f]' %fr_obj_wrap_OS.getFR(15, 1, 11))
    print('wrap  (SS) Ele eta=1, pt=15: [%.3f, %.3f]' %fr_obj_wrap_SS.getFR(15, 1, 11))
    print('wrap  (OS) Ele eta=2, pt=15: [%.3f, %.3f]' %fr_obj_wrap_OS.getFR(15, 2, 11))
    print('wrap  (OS) Muo eta=1, pt=15: [%.3f, %.3f]' %fr_obj_wrap_OS.getFR(15, 1, 13))
    print('wrap  (OS) Muo eta=2, pt=15: [%.3f, %.3f]' %fr_obj_wrap_OS.getFR(15, 2, 13))


if __name__ == '__main__':
    test()
