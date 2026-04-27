# Utiltiies, constants and enums
from enum import Enum
import logging
import os
import ROOT

from ROOT.RDF import TH1DModel

class TFileContext(object):
    '''Allows using a TFile in a with satatement'''
    def __init__(self, *args):
        self.tfile = ROOT.TFile(*args)
        if(not (self.tfile and self.tfile.IsOpen())):
            raise FileNotFoundError(args[0] if len(args) > 0 else '')

    def __enter__(self):
        return self.tfile

    def __exit__(self, exc_type, exc_value, traceback):
        self.tfile.Close()


# https://twiki.cern.ch/twiki/bin/viewauth/CMS/PdmVRun3Analysis
# https://twiki.cern.ch/twiki/bin/view/CMS/LumiRecommendationsRun3
lumi_dict = {
    # Errors expressed as lnN parameters: e.g. 1.6% -> 1.016
    'Run2'       : {'value':137620  },
    '2022preEE'  : {'value':  7980.4},
    '2022EE'     : {'value': 26671.7},
    '2023preBPix': {'value': 18063  },
    '2023BPix'   : {'value':  9693  },
    '2024'       : {'value':109080  },
    'Run3'       : {'value':171488  },
}

# The Run3 correlation scheme is a bit different
lumi_unc_dict = {
    "2022&2023&2024": {
        "lumi_1": {
            "2022": 1.0138,
            "2023": 1.0017,
            "2024": 1.0020
        },
        "lumi_2": {
            "2023": 1.0127,
            "2024": 1.0068
        },
        "lumi_3": {
            "2024": 1.0144
        }
    }
}


class FinalState(Enum):
    fs4e = 0
    fs4mu = 1
    fs2e2mu = 2
    fs2mu2e = 3
    fs4l = 4


class Channel(Enum):
    NONE = 0
    ch4mu = 1
    ch4e = 2
    ch2e2mu = 3

    @classmethod
    def from_fs(cls, fs):
        if  (fs == FinalState.fs4mu): return cls(Channel.ch4mu)
        elif(fs == FinalState.fs4e ): return cls(Channel.ch4e )
        elif(fs==FinalState.fs2e2mu or fs==FinalState.fs2mu2e): return cls(Channel.ch2e2mu)
        else: return cls(Channel.NONE)


def clamp(v, lo, hi):
    return min(max(v, lo), hi)


def mkhist(df, *model_args, v=None, w='weight'):
    '''
    Wrapper around Histo1D that creates a TH1DModel with the name of the column
    and the default value for the weight
    '''
    # logging.debug('model_args: %s', model_args)
    model = TH1DModel(*model_args)
    column = model.fName if v is None else v
    return df.Histo1D(model, column, w)


def write_resultmap(hdict):
    '''
    Write every histogram in the RResultMap passed as argument to the currently
    opened TFile (assuming that cd() has already been called)
    '''
    tf_out = ROOT.TFile.CurrentFile()
    if(not tf_out):
        raise RuntimeError('No TFile is currently open')

    logging.debug('keys: %s', hdict.GetKeys())
    hcentr = hdict['nominal']
    hname = hcentr.GetName()
    path_elems = hname.split('/')
    basename = path_elems[-1]
    logging.debug('central name: %s -> %s', hname, path_elems)

    # Optional: create subdirectories in the tf
    path_elems.reverse()
    curdir = tf_out
    while(len(path_elems) > 1):
        dirname = path_elems.pop()
        if(curdir.cd(dirname)):
            continue
        logging.debug('    making dir "%s"', dirname)
        curdir = curdir.mkdir(dirname)
        curdir.cd()

    # Write histograms
    hcentr.Write('%s-nominal'%(basename))

    for k in hdict.GetKeys():
        if(k == "nominal"):
            continue
        syst, updn = str(k).split(':')
        outn = '{basename}-{syst}-{updn}'.format(basename=basename, syst=syst, updn=updn)
        logging.debug('    %s -> (%s, %s) -> %s', k, syst, updn, outn)
        hdict[k].Write(outn)

    # Reset the current directory
    tf_out.cd()


class TKeyDeep():
    'A TKey that returns its full path inside the TFile when using GetName()'
    def __init__(self, tkey, path: str=''):
        self.tkey = tkey
        self.path = path
        self.name_ = os.path.join(self.path, self.tkey.GetName())

    def GetName(self):
        return self.name_

    def ReadObj(self):
        return self.tkey.ReadObj()


def get_keys_deep(tf):
    'Recursively get all the keys in the TFile/TDirectory and it sub-directories'
    out = []
    for key in tf.GetListOfKeys():
        if(key.IsFolder()):
            out.extend([
                TKeyDeep(k, path=key.GetName())
                for k in get_keys_deep(key.ReadObj())
            ])
        else:
            out.append(key)
    return out


def parse_syst_name(name):
    s = name.split('-')
    d = {
        'var' : '-'.join(s[:-2]),
        'syst': s[-2],
        'updn': s[-1]
        }
    return d
