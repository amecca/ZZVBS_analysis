#!/usr/bin/env python3

################################################################
# Make data/MC plots with histograms from ROOT files           #
#                                                              #
# Author: Alberto Mecca (alberto.mecca@cern.ch)                #
# Initial revision: 2025-11-13                                 #
################################################################

import os
from argparse import ArgumentParser, Namespace
import logging
from subprocess import run
from copy import deepcopy
from math import log10, ceil
import re
import ROOT
import cmsstyle

import sys
sys.path.append('../python')
from plotutils import VarInfo, SampleInfo, SampleHandle, \
    TH1_integr_and_err, cmsDiCanvas_fromTH1, getTAxisLimits
from utils import lumi_dict
from samples import get_samples


### To be moved to a separate configuration file?
variable_dicts = [
    {'name': 'ratio_EW_EWpQCD', 'blind':True, 'logy': True},
    {'name':'absdetajj', 'xtitle':'|#Delta#eta(j1,j2)|', 'logy':True, 'rebin':4, 'y_scale': 1e7},
    {'name':'nJets', 'logy':True, 'y_scale': 1e6},
    {'name':'FSLFO'}
]

def main(args: Namespace):
    ROOT.gROOT.SetBatch(True)

    if(not os.path.exists(args.inputdir)):
        raise RuntimeError('Could not find "%s"', args.inputdir)

    # Create a list of VarInfo objects, which sets some defaults in the constructor
    # and simplify the code doing the plotting
    # variables = [VarInfo(**k) for k in variable_dicts]
    variables = []
    for k in variable_dicts:
        tmp = dict(**k)
        for prefix in ('', 'VBSincl-', 'mZZ180-mjj400-', 'VBSloose-', 'VBStight-'):
            tmp['name'] = prefix+k['name']
            variables.append(VarInfo(**tmp))

    # Open the files that contain the histograms to be plotted
    sample_dicts = get_samples(region='4P') # [{data}, {MC0}, {MC1}, ...]
    samples_MC = []
    sample_data = None
    for v in sample_dicts:
        # Put the absolute path
        v['fpaths'] = [os.path.join(args.inputdir, f+'.root') for f in v['fnames']]

        if(v is None):
            logging.warning('Missing sample "%s"', name)
            continue

        s = SampleHandle(**v)
        if v['name'] == 'data': sample_data = s
        else: samples_MC.append(s)

    # Defaults for non-customized vars:
    all_keys = {k.GetName() for k in samples_MC[0].files[0].GetListOfKeys()} #for f in samples_MC[0].files for k in f.GetListOfKeys()
    new_keys = all_keys - {v.name for v in variables}
    variables.extend([VarInfo(name=n) for n in new_keys])

    # Customize style
    cmsstyle.SetExtraText("Preliminary")
    cmsstyle.setCMSStyle()
    cmsstyle.SetEnergy(13.6)
    lumi_val = lumi_dict[args.year]['value']/1000.
    lumi_decimals = (3 - ceil(log10(lumi_val))) # 3 significative digits
    cmsstyle.SetLumi(lumi_val, run=args.year, round_lumi=lumi_decimals)
    # ROOT.gStyle.SetLabelSize(0.045, "X")

    os.makedirs(args.outdir, exist_ok=True)

    # Plot only variables matching the requested pattern
    if(args.regex_incl is not None):
        variables = [v for v in variables if args.regex_incl.search(v.name)]
    if(args.regex_excl is not None):
        variables = [v for v in variables if not args.regex_excl.search(v.name)]

    for var in variables:
        if(var.name.startswith(('VBSloose', 'VBStight'))):
            var.blind = True
        plot_var(var, sample_data, samples_MC, args)

    return 0


def plot_var(var: VarInfo, sample_data: SampleHandle, samples_MC: list[SampleHandle], args: Namespace):
    '''Actually plot a single histogram'''
    logging.info('Plotting %s', var.name)

    # Fill the MC stack and the legend
    stack = ROOT.THStack("MCstack", "MCstack")
    refs_for_legend = []
    for sample in samples_MC:
        h = sample.get_hist(var.name)
        if(not h):
            logging.warning('No histogram for sample %s', sample.name)
            continue
        h.SetFillColor(sample.color)
        h.SetLineColor(ROOT.kBlack)
        if(var.rebin is not None): h.Rebin(var.rebin)
        if(logging.getLogger().isEnabledFor(logging.DEBUG)):
            i, e = TH1_integr_and_err(h)
            logging.debug('Add %s: %+7.5g +- %+7.5g', sample.name, i, e)
        stack.Add(h)
        refs_for_legend.append([h, sample.title])

    if(stack.GetNhists() == 0):
        logging.error('No MC histograms for %s', var.name)
        return 1

    last_stack = stack.GetStack().Last()
    if(var.xtitle is None): var.xtitle = last_stack.GetXaxis().GetTitle()

    ### DATA ###
    is_unblind = args.unblind or (not var.blind)
    if(is_unblind):
        hdata = sample_data.get_hist(var.name)
        hdata.SetTitle('data')
        if(var.rebin is not None): hdata.Rebin(var.rebin)
    else:
        hdata = last_stack.Clone('data_asimov')
        hdata.SetTitle('data Asimov')
        # for b in range(0, hdata.GetNbinsX()+2):
        #     hdata.SetBinContent(b, 0)
        #     hdata.SetBinError  (b, 0)

    # Ratio
    ratio = ROOT.TGraphAsymmErrors()
    ratio.SetName('ratio')
    logging.debug('data: %s', hdata)
    logging.debug('MC  : %s', last_stack)
    ratio.Divide(hdata, last_stack, 'pois')

    # Canvas creation
    dicanvas_kwargs = dict(y_min=0, min_hi_r=1.2, max_lo_r=0.8, range_include_err=True,
                           max_hi_r=4., min_lo_r=0.,
                           nameXaxis=var.xtitle, nameYaxis=var.ytitle, nameRatio='Data/Pred.',
                           iPos=11)
    if(args.y_max is not None): dicanvas_kwargs['y_max'] = args.y_max
    if(args.r_max is not None): dicanvas_kwargs['r_max'] = args.r_max
    if(var.logy):
        dicanvas_kwargs['y_scale'] = var.extra.get('y_scale', 1e6 )
        dicanvas_kwargs['y_min'  ] = var.extra.get('y_min'  , 1e-2)
    else:
        dicanvas_kwargs['y_scale'] = var.extra.get('y_scale', 2)
        dicanvas_kwargs['y_min'  ] = var.extra.get('y_min'  , 0)
    canvas = cmsDiCanvas_fromTH1(var.name, last_stack, ratio,
                                 **dicanvas_kwargs)
    canvas.cd()

    # The legend needs to be created after the canvas, otherwise it won't be drawn
    leg_ymax = .92
    leg_ymin = leg_ymax - 0.04*(len(samples_MC)+2)  # +2: MC stat, data
    legend = cmsstyle.cmsLeg(.55, leg_ymin, .90, leg_ymax, textSize=.025)

    ### Upper pad ###
    canvas.cd(1)
    canvas.GetPad(1).SetLogy(var.logy)

    # Style data
    if(hdata is not None):
        hdata.SetBinErrorOption(ROOT.TH1.kPoisson)
        legend.AddEntry(hdata, hdata.GetTitle(), 'lpe')

    # Error band in the upper canvas
    hMCErr = deepcopy(last_stack)
    legend.AddEntry(hMCErr, "Stat. only", "f")

    # Fill legend
    for h, title in refs_for_legend:
        legend.AddEntry(h, title, 'f')

    # Draw
    cmsstyle.cmsObjectDraw(stack, 'HIST')
    cmsstyle.cmsObjectDraw(hMCErr, 'E2', FillStyle=3005, MarkerStyle=1, FillColor=ROOT.kBlack)
    if(hdata is not None):
        cmsstyle.cmsObjectDraw(hdata, 'PE0X0', MarkerStyle=20, MarkerSize=1, LineColor=ROOT.kBlack)

    ### Lower pad ###
    canvas.cd(2)

    # Line y=1 in the ratio plot
    x_min, x_max = getTAxisLimits(hdata.GetXaxis())
    logging.debug('x_min=%.3g, x_max=%.3g', x_min, x_max)
    ref_line = ROOT.TLine(x_min, 1, x_max, 1)
    cmsstyle.cmsDrawLine(ref_line, lcolor=ROOT.kBlack, lstyle=ROOT.kDotted)

    # Ratio
    cmsstyle.cmsObjectDraw(ratio, 'PE', LineColor=ROOT.kBlack, MarkerStyle=20, MarkerSize=1)

    for ext in ['png', 'pdf']:
        outfname = os.path.join(args.outdir, var.name+'.'+ext)
        canvas.SaveAs(outfname)
        # campaign = 'Test' # TODO: use the inputdir
        # cmd = ['exiftool', '-overwrite_original', '-Keywords=%s'%(campaign), outfname]
        # logging.debug('running: %s', ' '.join(cmd))
        # run(cmd) # subprocess; willingly ignore errors

    return


def parse_args():
    parser = ArgumentParser('Make data/MC plots')
    parser.add_argument('inputdir', metavar='DIR', help='Folder containing the ROOT files with the histograms to be plotted')
    parser.add_argument('-o', '--outdir', default='latest', metavar='DIR', help='Directory where plots will be saved. Default: %(default)s')
    parser.add_argument('-y', '--year', default='2022EE')
    parser.add_argument('-p', '--plot'   , dest='regex_incl', type=re.compile, default=None)
    parser.add_argument(      '--exclude', dest='regex_excl', type=re.compile, default=None)
    parser.add_argument('--log', dest='loglevel', metavar='LEVEL', default='WARNING', help='Level for the python logging module. Can be either a mnemonic string like DEBUG, INFO or WARNING or an integer (lower means more verbose).')
    parser.add_argument(      '--unblind', action='store_true', help='Force unblind all blinded plots')

    args = parser.parse_args()
    args.y_max = None
    args.r_max = None
    return args


if __name__ == '__main__':
    args = parse_args()
    loglevel = args.loglevel.upper() if not args.loglevel.isdigit() else int(args.loglevel)
    logging.basicConfig(format='%(levelname)s:%(module)s:%(funcName)s: %(message)s', level=loglevel)

    exit(main(args))
