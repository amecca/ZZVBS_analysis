#!/usr/bin/env python3

import cmsstyle
import ROOT

SAMPLE_DICTS = {
    'qqZZ-EWK': {'title': 'qq #rightarrow ZZjj #rightarrow 4l 2j EWK'    , 'fnames':['ZZTo4l_2Jets_EW']},
    'qqZZ-int': {'title': 'qq #rightarrow ZZjj #rightarrow 4l 2j interf.', 'fnames':['ZZTo4l_2Jets_EW_QCD']},
    'qqZZ-QCD': {'title': 'qq #rightarrow ZZjj #rightarrow 4l 2j QCD'    , 'fnames':['ZZTo4l_2Jets_QCD']},
    'ggZZ'    : {'title': 'gg #rightarrow ZZ #rightarrow 4l MCFM', 'fnames': ['ggTo%s_Contin_MCFM701'%(fs) for fs in ('4e','2e2mu','4mu')]},
    'rare'    : {'title': 'VVZ', 'fnames':['ZZZ','WZZ','WWZ']}, #ttZ "t#bar{t}Z" is missing!
    'qqZZ-1J' : {'title': 'qq #rightarrow ZZ+1j #rightarrow 4l j'        , 'fnames':['ZZTo4l_1Jets']},
}

DATA = {'name': 'data', 'title': 'Data', 'fnames': ['data'], 'color': ROOT.kBlack}

def get_samples(region: str='4P'):
    MC_names = ['qqZZ-EWK', 'qqZZ-int', 'qqZZ-QCD', 'ggZZ', 'rare'] #, 'qqZZ-1J']
    MCs = [{'name':k, **SAMPLE_DICTS[k]} for k in MC_names]

    # AUTOMATIC COLORS #
    n_samples = len(MCs) - 1 #data
    palette = cmsstyle.getPettroffColorSet(n_samples)
    for i, v in enumerate(MCs):
        v['color'] = palette[i]

    return [DATA] + MCs
