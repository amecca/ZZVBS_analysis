#!/usr/bin/env python3

import logging
import cmsstyle
import ROOT

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
    def __init__(self, name, fpaths: list[str], title: str, color: str,
                 kfactor: float=1.,
                 **kwargs):
        self.name = name
        self.title = title
        self.color = color
        self.fpaths = fpaths
        self.kfactor = kfactor


class SampleHandle(SampleInfo):
    '''
    A sample is made of one or more phisical files.
    It holds handles to one or more TFiles and information (e.g. title/label) on how to be ploted.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.files = []
        for fpath in self.fpaths:
            try:
                f = ROOT.TFile(fpath)
            except OSError as e:
                logging.warning('Could not open file %s', fpath)
            else:
                logging.debug('sample: %s: opened %s', self.name, fpath)
                self.files.append(f)
        # self.kfactor = kwargs.get('kfactor', 1.)

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

    def GetListOfKeys(self):
        logging.warning('TODO: use the get_keys_deep from utils.py')
        return set.union(*[{k for k in f.GetListOfKeys()} for f in self.files])



def get_samples(region: str='4P'):
    MC_names = ['qqZZ-EWK', 'qqZZ-1J', 'ggZZ', 'rare', 'ZX'] #, 'qqZZ-QCD', 'qqZZ-int', 'qqZZ-1J']
    MCs = [{'name':k, **SAMPLE_DICTS[k]} for k in MC_names]

    # AUTOMATIC COLORS #
    n_samples = len(MCs) - 1 #data
    palette = cmsstyle.getPettroffColorSet(n_samples)
    for i, v in enumerate(MCs):
        v['color'] = palette[i]

    return [DATA] + MCs
