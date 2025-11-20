# Utiltiies, constants and enums
from enum import Enum
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
    logging.debug('keys: %s', hdict.GetKeys())
    hcentr = hdict['nominal']
    hcentr.Write()
    basename = hcentr.GetName()
    for k in hdict.GetKeys():
        if(k == "nominal"):
            continue
        syst, updn = str(k).split(':')
        syst = syst.replace('_', '-')
        outn = '{basename}_{syst}_{updn}'.format(basename=basename, syst=syst, updn=updn)
        logging.debug('    %s -> (%s, %s) -> %s', k, syst, updn, outn)
        hdict[k].Write(outn)


def parse_syst_name(name):
    s = name.split('_')
    d = {
        'var' : '_'.join(s[:-2]),
        'syst': s[-2],
        'updn': s[-1]
        }
    return d
