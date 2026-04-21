#!/usr/bin/env python3

import os
import sys
import logging
import cmsstyle
import ROOT

sys.path.append('../../.python')
from ZZVBS_analysis.Analysis.plotutils import TH1_integr_and_err, add_list_TObj
from ZZVBS_analysis.Analysis.utils import get_keys_deep

SAMPLE_DICTS = {
    'qqZZ-EWK': {'title': 'ZZjj EWK'                         , 'fnames':['ZZTo4l_2Jets_EW']},
    'qqZZ-int': {'title': 'ZZjj interf.'                     , 'fnames':['ZZTo4l_2Jets_EW_QCD']},
    'qqZZ-QCD': {'title': 'ZZjj QCD'                         , 'fnames':['ZZTo4l_2Jets_QCD']},
    'ggZZ'    : {'title': 'gg #rightarrow ZZ MCFM', 'fnames': ['ggTo%s_Contin_MCFM701'%(fs) for fs in ('4e','2e2mu','4mu')]},
    'rare'    : {'title': 'VVZ', 'fnames':['ZZZ','WZZ','WWZ']}, #ttZ "t#bar{t}Z" is missing!
    'qqZZ-1J' : {'title': 'q#bar{q} #rightarrow ZZ+1j MG'       , 'fnames':['ZZTo4l_1Jets']},
    'qqZZ'    : {'title': 'q#bar{q} #rightarrow ZZ Powheg'   , 'fnames':['ZZTo4l'], 'kfactor':1.2},
    'ZX'      : {'title': 'Z+X'                                                , 'fnames':['ZX']},
}

DATA = {'name': 'data', 'title': 'Data', 'fnames': ['data'], 'color': ROOT.kBlack}


class SampleInfo:
    '''
    Metadata about a sample: info about how to plot, which files to use, etc.
    '''
    def __init__(self, name, fnames: list[str], title: str, color: int,
                 kfactor: float=1.,
                 **kwargs):
        self.name = name
        self.title = title
        self.color = color
        self.fnames = fnames
        self.kfactor = kfactor


class SampleHandle(SampleInfo):
    '''
    A sample is made of one or more phisical files.
    It holds handles to one or more TFiles and information (e.g. title/label) on how to be ploted.
    '''
    def __init__(self, *args, dirpath:str, **kwargs):
        super().__init__(*args, **kwargs)
        self.dirpath = dirpath

        self.files = []
        for fname in self.fnames:
            fpath = os.path.join(self.dirpath, fname+'.root')
            try:
                f = ROOT.TFile(fpath)
            except OSError as e:
                logging.warning('Could not open file %s', fpath)
            else:
                logging.debug('sample: %s: opened %s', self.name, fpath)
                self.files.append(f)

    @classmethod
    def from_info(cls, info: SampleInfo, dirpath: str):
        return cls(**vars(info), dirpath=dirpath)

    def get_hist(self, hname):
        '''Try to get one histogram named "name" from each of the file, and Add() them together'''
        hlist = []
        for f in self.files:
            h = f.Get(hname)
            integr, error = TH1_integr_and_err(h)
            logging.debug('%-20.20s: %+.3g += %.3g',
                          os.path.basename(f.GetName()).replace('.root',''),
                          integr, error)
            hlist.append(h)

        res = add_list_TObj(*hlist)
        return res

    def get_keys(self):
        return set.union(*[{k for k in get_keys_deep(f)} for f in self.files]
                         , set()) # this last argument avoids crashing when no key can be retrieved

    def GetListOfKeys(self):
        return self.get_keys()


class InputDir():
    'Standardize how to find histograms'
    def __init__(self, basedir, year):
        self.basedir = basedir
        self.year = year

    def path(self):
        return os.path.join(self.basedir, self.year)


def get_samples_dicts(region: str='4P'):
    MC_names = ['qqZZ-EWK', 'qqZZ-1J', 'ggZZ', 'rare', 'ZX'] #, 'qqZZ-QCD', 'qqZZ-int', 'qqZZ-1J']
    MCs = [{'name':k, **SAMPLE_DICTS[k]} for k in MC_names]

    # AUTOMATIC COLORS #
    n_samples = len(MCs) - 1 #data
    palette = cmsstyle.getPettroffColorSet(n_samples)
    for i, v in enumerate(MCs):
        v['color'] = palette[i]

    return DATA, MCs


def get_samples_info(region: str='4P'):
    d_data, d_MCs = get_samples_dicts(region)
    data = SampleInfo(**d_data)
    MCs = [SampleInfo(**d_MC) for d_MC in d_MCs]
    return data, MCs
