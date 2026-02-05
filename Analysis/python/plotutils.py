import os
from ctypes import c_double
import logging
import ROOT
import cmsstyle

class VarInfo:
    '''
    Information related to a vertain variable to be plotted:
    * name: a name associated to the variable
    * xtitle: title of the x axis (default: "")
    * histpattern: list of names of `TH1`s to get from ROOT files (default: name).
      The names can be patterns that a SampleInfo will fill, e.g. to have
      only mll_prompt from sampleA and mll_prompt+mll_nonprompt from sampleB
    * ytitle: title of the y axis (default: Events)
    '''
    def __init__(self, name: str, xtitle: str,
                 ytitle: str="Events", logy: bool=False):
        self.name = name
        self.xtitle = xtitle
        self.ytitle = ytitle
        self.logy = logy


class SampleInfo:
    '''
    Metadata about a sample: info about how to plot, which files to use, etc.
    '''
    def __init__(self, name, fpaths: list[str], title: str, color: str,
                 **kwargs):
        self.name = name
        self.title = title
        self.color = color
        self.fpaths = fpaths


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

    def __del__(self):
        try:
            for f in self.files:
                if(f and f.IsOpen()): f.Close()
        except AttributeError: pass


def add_list_TObj(*args):
    '''
    Add() a list of TObjects, starting from the first non-None
    '''
    result = None
    for a in [ a for a in args if a is not None ]:
        if(result is None):
            result = a
        else:
            result.Add(a)
    return result


def cmsDiCanvas_fromTH1(name, h, r, y_scale=1, range_include_err=False, **kwargs):
    '''Helper that defines reasonable ranges when creating a cmsDiCanvas object'''
    cmsargs = dict()
    x_min, x_max = getTAxisLimits(h.GetXaxis())
    cmsargs['x_min'] = kwargs.get('x_min', x_min)
    cmsargs['x_max'] = kwargs.get('x_max', x_max)

    cmsargs['y_min'] = kwargs.get('y_min', h.GetMinimum())
    cmsargs['y_max'] = kwargs.get('y_max', h.GetMaximum()*y_scale)

    if(not ('r_min' in kwargs and 'r_max' in kwargs)):
        for argname in ('y_scale', 'min_lo', 'max_lo', 'min_hi', 'max_hi'):
            # massage arg names for clamp_expnd_r()
            if(argname+'_r' in kwargs): kwargs[argname] = kwargs.pop(argname+'_r')
        if(r.GetN() > 0):
            r_min, r_max = get_range_tga(r, include_err=range_include_err)
            r_min, r_max = clamp_expnd_r(r_min, r_max, **kwargs)
        else:
            r_min, r_max = 0, 2
    r_min = kwargs.get('r_min', r_min)
    r_max = kwargs.get('r_max', r_max)

    cmsargs['nameXaxis'] = kwargs.get('nameXaxis', h.GetXaxis().GetTitle())
    cmsargs['nameYaxis'] = kwargs.get('nameYaxis', h.GetYaxis().GetTitle())
    cmsargs['nameRatio'] = kwargs.get('nameRatio', r.GetYaxis().GetTitle())
    if('iPos' in kwargs): cmsargs['iPos'] = kwargs['iPos']

    c = cmsstyle.cmsDiCanvas('canvas_%s' %(name), r_min=r_min, r_max=r_max, **cmsargs)

    return c


def getTAxisLimits(axis):
    return \
        axis.GetBinLowEdge(1), \
        axis.GetBinLowEdge(axis.GetNbins()+1)


def get_range_tga(g, include_err=False):
    '''Get the y range needed to draw a TGraphAsymmErrors'''
    name = g.GetName()

    if(include_err):
        np = g.GetN()
        y_max = max( p for p in (g.GetPointY(i)+g.GetErrorYhigh(i) for i in range(np)) )
        y_min = min( p for p in (g.GetPointY(i)-g.GetErrorYlow (i) for i in range(np)) )
    else:
        buf = array('d', g.GetY())
        y_max = max( buf )
        y_min = min( buf )
    logging.debug('%s range (raw): [%.3g, %.3g]', name, y_min, y_max)

    return y_min, y_max


def getTAxisLimits(axis):
    return \
        axis.GetBinLowEdge(1), \
        axis.GetBinLowEdge(axis.GetNbins()+1)


def clamp_expnd_r(lo, hi, y_scale=0.1, min_lo=0., max_lo=0.9, min_hi=1.1, max_hi=100, name='[range]', **kwargs):
    '''
    Massage the range [lo, hi]: enlarge it by (hi-lo)*y_scale, 
    and clamp both (lo|hi) between [min_(lo|hi), max_(lo|hi)]
    '''

    def clamp(v, min_y, max_y):
        return min(max(v, min_y), max_y)

    delta = hi - lo
    lo = clamp(lo - y_scale * delta, min_lo, max_lo)
    hi = clamp(hi + y_scale * delta, min_hi, max_hi)
    logging.debug('%s range (fix): [%.3g, %.3g]', name, lo, hi)

    return lo, hi


def TH1_integr_and_err(h, binx1=0, binx2=-1):
    e = c_double(0.)
    i = h.IntegralAndError(binx1, binx2, e) if h else 0.
    return i, e.value


def TH1_get_max_rigth(h):
    '''Return the value of the highest bin after the middle (where the legend should be)'''
    n = h.GetNbinsX()
    return max(h.GetBinContent(i) for i in range(n//2, n+1))

