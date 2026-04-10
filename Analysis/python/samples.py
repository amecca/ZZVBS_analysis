#!/usr/bin/env python3

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

def get_samples(region: str='4P'):
    MC_names = ['qqZZ-EWK', 'qqZZ-1J', 'ggZZ', 'rare', 'ZX'] #, 'qqZZ-QCD', 'qqZZ-int', 'qqZZ-1J']
    MCs = [{'name':k, **SAMPLE_DICTS[k]} for k in MC_names]

    # AUTOMATIC COLORS #
    n_samples = len(MCs) - 1 #data
    palette = cmsstyle.getPettroffColorSet(n_samples)
    for i, v in enumerate(MCs):
        v['color'] = palette[i]

    return [DATA] + MCs
