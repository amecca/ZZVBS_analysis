#!/usr/bin/env python3

import os
import sys
import re
from math import log10, ceil, sqrt
import json
from collections.abc import Mapping # py3 only
from argparse import ArgumentParser
import logging
import ROOT
import cmsstyle

sys.path.append('../../.python')
from ZZVBS_analysis.Analysis.samples import get_samples_info, SampleInfo, SampleHandle, InputDir
from ZZVBS_analysis.Analysis.plotutils import TH1_integr_and_err, get_range_tga\
    , clamp_expnd_r, getTAxisLimits
from ZZVBS_analysis.Analysis.utils import lumi_dict


class SystDB:
    def __init__(self, fname=None):
        if(fname is not None):
            self.load(fname)
        else:
            self.db_ = {}

    def __len__(self):
        return len(self.db_)

    def set(self, value, region, var, sample, syst):
        self.db_\
            .setdefault(region, {})\
            .setdefault(var, {})\
            .setdefault(sample, {})\
            [syst] = value

    @staticmethod
    def deep_update_(orig, new):
        'Merge data from another dictionary'
        for k, v in new.items():
            if isinstance(v, Mapping):
                orig[k] = SystDB.deep_update_(orig.get(k, {}), v)
            else:
                orig[k] = v
        return orig

    def deep_update(self, new):
        self.deep_update_(self.db_, new.db_)

    def dump(self, fname):
        with open(fname, 'w') as f:
            json.dump(self.db_, f, indent=2)
        logging.info('wrote systematics to "%s"', fname)

    def load(self, fname):
        with open(fname) as f:
            self.db_ = json.load(f)
        logging.info('loaded previous dict from "%s"', fname)


def main(args):
    logging.debug('args = %s', args)

    if(args.do_plots):
        set_style()
        os.makedirs('plots/systematics/%s/%s'%(args.region, args.year), exist_ok=True)

    hists_basep = args.inputdir
    logging.debug('hists_basep: %s', hists_basep)

    systDBfname = os.path.join(args.output, '%s.json'%(args.year))
    systDB = SystDB()
    try:
        datadir = os.path.dirname(systDBfname)
        logging.debug('datadir: %s', datadir)
        os.makedirs(datadir, exist_ok=True)
        systDB.load(systDBfname)
    except (IOError, OSError, ValueError):
        logging.info('Could not retrieve existing dictionary from "%s". Starting from a new one', systDBfname)

    argsdict = vars(args)

    # Get the file list for this region
    _, s_info_MC = get_samples_info(args.region)
    s_dicts_MC = [SampleInfo(name='qqZZ-EWK', title='ZZjj EWK', fnames=['ZZTo4l_2Jets_EW'], color=ROOT.kBlack)]
    logging.warning('restore the line above')

    for s_info in s_info_MC:
        if(args.sample_regex and not args.sample_regex.search(s_info.name)):
            logging.debug('skipping sample "%s"', s_info.name)
            continue
        # Get the full path to the file(s) with the histograms

        logging.debug('files: %s', s_info.fnames)
        # Open the files
        try:
            s = SampleHandle.from_info(s_info, dirpath=hists_basep)
            new = doSystOnSample(s, **argsdict)
            systDB.deep_update(new)
        except OSError as e:
            # A sample is missing
            logging.error('%s', e)

    # Write the (updated) systematic info to the DB file
    if(args.do_update):
        systDB.dump(systDBfname)

    return 0


def parse_args():
    parser = ArgumentParser(description='Calculate systematic variations from rootfiles produced by VVGammaAnalyzer')
    parser.add_argument('inputdir', metavar='DIR')
    parser.add_argument('-p', '--plots', dest='do_plots', action='store_true')
    parser.add_argument('-y', '--year', default='2024', help='Default: %(default)s')
    parser.add_argument('-o', '--output', default='data/systematics', help='Output directory (default: %(default)s)')
    # parser.add_argument('-r', '--region', default='SR4P', help='Default: %(default)s')
    parser.add_argument('-S', '--syst-regex'  , default=None, type=re.compile, help='Filter systematics with a regular expression')
    parser.add_argument('-s', '--sample-regex', default=None, type=re.compile, help='Filter samples by name with a regex')
    parser.add_argument('-t', '--var-regex'   , default=None, type=re.compile, help='Filter variables with a regular expression')
    parser.add_argument(      '--no-update', action='store_false', dest='do_update', help='Do not write back to the syst DB file')
    parser.add_argument('--log', dest='loglevel', metavar='LEVEL', default='INFO')
    args = parser.parse_args()
    args.region = '4P'

    return args


def analyze_syst(hCe, hUp, hDn, var='[var]', syst='[syst]', sample='[sample]', region='[region]', **kwargs):  # <TH1>, <TH1>, <TH1>, <dict> (modified), <str>, <str>, <str>, <str>
    formatInfo = dict(var=var, syst=syst, sample=sample, region=region, year=kwargs['year'])

    if(not hCe):
        logging.warning("hCe is null for %s", str(formatInfo))
        return SystDB()
    if(not hUp     ):
        logging.warning("hUp is null for %s", str(formatInfo))
        return SystDB()
    if(not hDn     ):
        logging.warning("hDn is null for %s", str(formatInfo))
        return SystDB()

    var_split = var.split('-')
    if(len(var_split) > 1):  # prompt/nonpro
        var = var_split[0]
        sample = '-'.join((sample, var_split[1]))

    integrCe, errorCe = TH1_integr_and_err(hCe)
    integrUp, errorUp = TH1_integr_and_err(hUp)
    integrDn, errorDn = TH1_integr_and_err(hDn)
    if(integrCe == 0):
        logging.error('integrCe is 0 for %s', formatInfo)
        logging.debug('\tintegrCe = %s', hCe.GetName())
        return dict()

    upVar = integrUp/integrCe - 1
    dnVar = integrDn/integrCe - 1
    # logging.debug('\t{var}_{syst}'.format(**formatInfo), ' Up: {:.1f} %  Dn: {:.1f} %'.format(100*upVar, 100*dnVar))

    ###################### Definition of the content of the syst entry #######################
    syst_values = SystDB()
    syst_values.set({'up':upVar, 'dn':dnVar, 'integr': integrCe, 'N': int(hCe.GetEntries())},
                    region=region, var=var, sample=sample, syst=syst)
    ##########################################################################################

    if(kwargs.get('do_plots')):
        yields = {'ce': (integrCe, errorCe),
                  'up': (integrUp, errorUp),
                  'dn': (integrDn, errorDn)}
        plot_syst(hCe, hUp, hDn, yields, formatInfo, **kwargs)
    return syst_values


def plot_syst(hCe, hUp, hDn, yields, formatInfo, **kwargs):  # <TH1>, <TH1>, <TH1>, <dict> (modified), <str>, <str>, <str>, <str>
    c = ROOT.TCanvas('c_{region}_{sample}_{var}_{syst}'.format(**formatInfo), '{var}: {syst} ({region})'.format(**formatInfo), 1600, 900)
    c.cd()
    pad_histo = ROOT.TPad ('pad_histo', '', 0., 0.34, 1., 1.)
    pad_ratio = ROOT.TPad ('pad_ratio', '', 0., 0.0 , 1., 0.34)
    pad_histo.SetTopMargin   (0.1)
    pad_histo.SetBottomMargin(0.013)
    pad_ratio.SetTopMargin   (0.05)
    pad_ratio.SetBottomMargin(0.25)
    for pad in (pad_histo, pad_ratio):
        pad.SetRightMargin   (0.06)
        pad.SetLeftMargin    (0.10)
        c.cd()
        pad.Draw()

    legend = cmsstyle.cmsLeg(.60, .775, .90, .90, textSize=.027)

    # Upper pad
    pad_histo.cd()
    x_min, x_max = getTAxisLimits(hCe.GetXaxis())
    y_min = max(h.GetMinimum() for h in [hUp, hCe, hDn])
    y_max = max(h.GetMaximum() for h in [hUp, hCe, hDn])
    y_max += (y_max-y_min)*0.1
    frame = pad_histo.DrawFrame(x_min, y_min, x_max, y_max)

    # pad_histo.SetLogy()

    hCe.GetYaxis().SetLabelSize(0.045)

    upVarV = yields['up'][0]/yields['ce'][0] - 1
    dnVarV = yields['dn'][0]/yields['ce'][0] - 1
    upVarE = abs(upVarV) * sqrt((yields['up'][1]/yields['up'][0])**2 + (yields['ce'][1]/yields['ce'][0])**2)
    dnVarE = abs(dnVarV) * sqrt((yields['dn'][1]/yields['dn'][0])**2 + (yields['ce'][1]/yields['ce'][0])**2)
    legend.AddEntry(hUp, 'Up   : {:.3g} #pm {:.3g} ({:+.2f} #pm {:.2f}%)'.format(*yields['up'], 100*upVarV, 100*upVarE))
    legend.AddEntry(hCe, 'centr: {:.3g} #pm {:.3g}'                      .format(*yields['ce']))
    legend.AddEntry(hDn, 'Dn   : {:.3g} #pm {:.3g} ({:+.2f} #pm {:.2f}%)'.format(*yields['dn'], 100*dnVarV, 100*dnVarE))

    hCe.GetXaxis().SetLabelSize(0)  # remove x axis tick labels
    cmsstyle.cmsObjectDraw(hCe, "hist", LineWidth=2, LineColor=ROOT.kBlack, MarkerColor=ROOT.kBlack)
    cmsstyle.cmsObjectDraw(hUp, "hist", LineWidth=1, LineColor=ROOT.kRed  , MarkerColor=ROOT.kRed  , MarkerStyle=ROOT.kFullTriangleUp  )
    cmsstyle.cmsObjectDraw(hDn, "hist", LineWidth=1, LineColor=ROOT.kBlue , MarkerColor=ROOT.kBlue , MarkerStyle=ROOT.kFullTriangleDown)

    # ratio
    pad_ratio.cd()
    stat_method = 'pois'
    verbose = False #'muoFake' in syst
    if(verbose):
        stat_method = 'pois v'
    if(yields['ce'][0] < 0):
        hCe_forRatio = hCe.Clone('hCe_ratio')
        hUp_forRatio = hUp.Clone('hUp_ratio')
        hDn_forRatio = hDn.Clone('hDn_ratio')
        hCe_forRatio.Scale(-1)
        hUp_forRatio.Scale(-1)
        hDn_forRatio.Scale(-1)
    else:
        hCe_forRatio = hCe
        hUp_forRatio = hUp
        hDn_forRatio = hDn

    hRatioUp = ROOT.TGraphAsymmErrors(hUp_forRatio, hCe_forRatio, stat_method)
    hRatioDn = ROOT.TGraphAsymmErrors(hDn_forRatio, hCe_forRatio, stat_method)

    if(verbose):
        for i in range(hCe.GetNbinsX()):
            nc = hCe.GetBinContent(i)
            xc = hCe.GetBinCenter(i)
            nu = hUp.GetBinContent(i)
            nd = hDn.GetBinContent(i)
            if(nc != 0):
                logging.debug('>>> bin:{:d} ({:.0f}), nominal:{:+.3f}, up:{:+.3f} ({:+.3f}), dn:{:+.3f} ({:+.3f})'.format(i, xc, nc, nu, nu/nc, nd, nd/nc))
            else:
                logging.debug('>>> bin:{:d} ({:.0f}), nominal:{:+.3f}, up:{:+.3f} (  nan ), dn:{:.3f} (  nan )'.format(i, xc, nc, nu, nd))

    ymin_up, ymax_up = get_range_tga(hRatioUp, include_err=False)
    ymin_dn, ymax_dn = get_range_tga(hRatioDn, include_err=False)
    y_min_r, y_max_r = clamp_expnd_r(
        min(ymin_up, ymin_dn),
        max(ymax_up, ymax_dn),
        max_hi=2.
    )
    frame = pad_ratio.DrawFrame(x_min, y_min_r, x_max, y_max_r)
    x_axis_r = frame.GetXaxis()
    y_axis_r = frame.GetYaxis()
    x_axis_r.SetLabelSize(0.1)
    y_axis_r.SetLabelSize(0.08)
    x_axis_r.SetTitle(hCe.GetXaxis().GetTitle())
    x_axis_r.SetTitleSize(.1)

    # Line y=1 in the ratio plot
    ref_line = ROOT.TLine(x_min, 1, x_max, 1)
    cmsstyle.cmsDrawLine(ref_line, lwidth=1, lcolor=ROOT.kBlack, lstyle=ROOT.kDashed)

    cmsstyle.cmsObjectDraw(hRatioUp, "PE", MarkerSize=1., MarkerStyle=ROOT.kFullTriangleUp  , LineColor=ROOT.kRed , MarkerColor=ROOT.kRed )
    cmsstyle.cmsObjectDraw(hRatioDn, "PE", MarkerSize=1., MarkerStyle=ROOT.kFullTriangleDown, LineColor=ROOT.kBlue, MarkerColor=ROOT.kBlue)

    for ext in ('png', 'pdf'):
        formatInfo['var'] = formatInfo['var'].replace('/','-')
        c.SaveAs('plots/systematics/{region}/{year}/{sample}_{var}_{syst}.{ext}'.format(**formatInfo, ext=ext))
    del c


def doSystematics(handle, var, syst, **kwargs):  # <TFile>, <str>, <str>, <dict> (is modified)
    formatInfo = dict(var=var, syst=syst, sample=handle.name)
    hCe = handle.get_hist('{var}-nominal'  .format(**formatInfo))
    hUp = handle.get_hist('{var}-{syst}-Up'.format(**formatInfo))
    hDn = handle.get_hist('{var}-{syst}-Dn'.format(**formatInfo))
    if((not hUp) or (not hDn)):
        logging.warning('var={var}, syst={syst} not found in sample={sample}'.format(**formatInfo))
        return SystDB()

    new_syst = analyze_syst(hCe, hUp, hDn, var=var, syst=syst, sample=handle.name, **kwargs)
    return new_syst


def doSystOnSample(handle, syst_regex=None, var_regex=None, **kwargs):  # <str>, <re.Pattern>
    syst_values = SystDB()

    logging.debug('sample = %s', handle.name)

    names = set()
    for key in handle.GetListOfKeys():
        name = key.GetName()
        if(name.count('-') >= 2):
            names.add(name)

    logging.debug('\tfound %d hists that look like systematics (+nominal)', len(names))

    variables   = set([n.split('-')[0] for n in names])
    if(var_regex  is not None):
        logging.debug('\toriginal variables (%d): %s', len(variables), variables)
        logging.debug('\tregex for variables: %s', var_regex.pattern)
        variables   = {s for s in variables   if  var_regex.search(s)}
        logging.debug('\tfiltered variables (%d): %s', len(variables), variables)
    systematics = set([n.split('-')[-2] for n in names]) - {'nominal'}
    if(syst_regex is not None):
        logging.debug('\toriginal systematics (%d): %s', len(systematics), systematics)
        systematics = {s for s in systematics if syst_regex.search(s)}
        logging.debug('\tregex for systematic: %s', syst_regex.pattern)
        logging.debug('\tfiltered systematics (%d): %s', len(systematics), systematics)

    for var in variables:
        syst_empty = set()
        for syst in systematics: #- {'nominal'}
            new_syst = doSystematics(handle, var, syst, **kwargs)
            if(len(new_syst) == 0): syst_empty.add(syst)
            syst_values.deep_update(new_syst)
        if(len(systematics - syst_empty) == 0): # - {'nominal'}
            logging.error('All the systematics for variable "%s" are empty!!!\n', var)

    return syst_values


def set_style():
    cmsstyle.setCMSStyle()
    cmsstyle.SetExtraText("Preliminary")
    cmsstyle.SetEnergy(13.6)
    lumi_val = lumi_dict[args.year]['value']/1000.
    lumi_decimals = (3 - ceil(log10(lumi_val))) # 3 significative digits
    cmsstyle.SetLumi(lumi_val, run=args.year, round_lumi=lumi_decimals)
    # ROOT.gStyle.SetOptStat('0000')
    ROOT.gROOT.SetBatch(True)


if __name__ == '__main__':
    args = parse_args()
    loglevel = args.loglevel.upper() if not args.loglevel.isdigit() else int(args.loglevel)
    logging.basicConfig(format='%(levelname)s:%(module)s:%(funcName)s: %(message)s', level=loglevel)
    exit(main(args))
