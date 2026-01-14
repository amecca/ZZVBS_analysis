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
import ROOT
import cmsstyle

import sys
sys.path.append('../python')
from plotutils import VarInfo, SampleInfo, SampleHandle, \
    TH1_integr_and_err, cmsDiCanvas_fromTH1, getTAxisLimits
from utils import lumi_dict


### To be moved to a separate configuration file?
variable_dicts = [
    {'name':'ZZ_mass'  , 'xtitle':'m_{ZZ} [GeV]'},
    {'name':'absdetajj', 'xtitle':'|#Delta#eta(j1,j2)|', 'logy':True}
]

sample_dicts = {
    'qqZZ': {'title': 'qq #rightarrow ZZ #rightarrow 4l', 'fnames':['ZZTo4l']},
    'ggZZ': {'title': 'gg #rightarrow ZZ #rightarrow 4l', 'fnames':[f+'_Contin_MCFM701' for f in ['ggTo4e', 'ggTo2e2mu', 'ggTo4mu']]},
    'data': {'title': 'Data', 'fnames': ['data'], 'color': ROOT.kBlack},
}

### AUTOMATIC COLORS ###
n_samples = len(sample_dicts) - 1 #data
palette = cmsstyle.getPettroffColorSet(n_samples)
for i, [k, v] in enumerate(sample_dicts.items()):
    if(k == 'data' or v is None): continue
    v['color'] = palette[i]
###


def main(args: Namespace):
    ROOT.gROOT.SetBatch(True)

    if(not os.path.exists(args.inputdir)):
        raise RuntimeError('Could not find "%s"', args.inputdir)

    # Create a list of VarInfo objects, which sets some defaults in the constructor
    # and simplify the code doing the plotting
    variables = [VarInfo(**k) for k in variable_dicts]

    # Open the files that contain the histograms to be plotted
    samples_MC = []
    sample_data = None
    for name, v in sample_dicts.items():
        # Put the absolute path
        v['fpaths'] = [os.path.join(args.inputdir, f+'.root') for f in v['fnames']]

        if(v is None):
            logging.warning('Missing sample "%s"', name)
            continue

        s = SampleHandle(name=name, **v)
        if name == 'data': sample_data = s
        else: samples_MC.append(s)

    # Customize style
    cmsstyle.SetExtraText("Preliminary")
    cmsstyle.setCMSStyle()
    cmsstyle.SetEnergy(13.6)
    lumi_val = lumi_dict[args.year]['value']/1000.
    lumi_decimals = (3 - ceil(log10(lumi_val))) # 3 significative digits
    cmsstyle.SetLumi(lumi_val, run=args.year, round_lumi=lumi_decimals)
    # ROOT.gStyle.SetLabelSize(0.045, "X")

    os.makedirs(args.outdir, exist_ok=True)

    for var in variables:
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
        if(h is None):
            logging.warning('No histogram for sample %s', sample.name)
            continue
        h.SetFillColor(sample.color)
        h.SetLineColor(ROOT.kBlack)
        if(logging.getLogger().isEnabledFor(logging.DEBUG)):
            i, e = TH1_integr_and_err(h)
            logging.debug('Add %s: %+7.5g +- %+7.5g', sample.name, i, e)
        stack.Add(h)
        refs_for_legend.append([h, sample.title])

    if(stack.GetNhists() == 0):
        logging.error('No MC histograms for %s', var.name)
        return 1

    hdata = None #sample_data.get_hist(var.name)
    is_asimov = False
    # Empty data (blind plots or we don't have the data)
    if(hdata is None):
        is_asimov = True
        hdata = stack.GetStack().Last().Clone('data_asimov')
        # for b in range(0, hdata.GetNbinsX()+2):
        #     hdata.SetBinContent(b, 0)
        #     hdata.SetBinError  (b, 0)
    hdata.GetXaxis().SetTitle(var.xtitle)

    # Ratio
    ratio = ROOT.TGraphAsymmErrors()
    ratio.SetName('ratio')
    logging.debug('data: %s', hdata)
    logging.debug('MC  : %s', stack.GetStack().Last())
    ratio.Divide(hdata, stack.GetStack().Last(), 'pois')

    # Canvas creation
    dicanvas_kwargs = dict(y_min=0, y_scale=1.5, min_hi_r=2., max_lo_r=0., range_include_err=True,
                           nameXaxis=var.xtitle, nameYaxis=var.ytitle, nameRatio='Data/Pred.',
                           iPos=11)
    if(args.y_max is not None): dicanvas_kwargs['y_max'] = args.y_max
    if(args.r_max is not None): dicanvas_kwargs['r_max'] = args.r_max
    canvas = cmsDiCanvas_fromTH1(var.name, stack.GetStack().Last(), ratio,
                                 **dicanvas_kwargs)
    canvas.cd()

    # The legend needs to be created after the canvas, otherwise it won't be drawn
    leg_ymax = .92
    leg_ymin = leg_ymax - 0.05*(len(samples_MC)+2)  # +2: MC stat, data
    legend = cmsstyle.cmsLeg(.55, leg_ymin, .90, leg_ymax, textSize=.03)
    for h, title in refs_for_legend:
        legend.AddEntry(h, title, 'f')

    ### Upper pad ###
    canvas.cd(1)

    # Error band in the upper canvas
    hMCErr = deepcopy(stack.GetStack().Last())

    hMCErr.SetFillStyle(3005)
    hMCErr.SetMarkerStyle(1)
    hMCErr.SetFillColor(ROOT.kBlack)
    legend.AddEntry(hMCErr, "Stat. only", "f")

    # Style data
    if(hdata is not None):
        hdata.SetLineColor(ROOT.kBlack)
        hdata.SetMarkerStyle(20)
        hdata.SetMarkerSize(.8)
        hdata.SetBinErrorOption(ROOT.TH1.kPoisson)
        legend.AddEntry(hdata, 'data Asimov', 'lpe')

    # Draw
    stack.Draw('SAMEHIST')
    hMCErr.Draw("SAMEE2")
    if(hdata is not None):
        hdata.Draw('SAMEPE0X0')

    ### Lower pad ###
    canvas.cd(2)

    # Line y=1 in the ratio plot
    x_min, x_max = getTAxisLimits(hdata.GetXaxis())
    logging.debug('x_min=%.3g, x_max=%.3g', x_min, x_max)
    ref_line = ROOT.TLine(x_min, 1, x_max, 1)
    cmsstyle.cmsDrawLine(ref_line, lcolor=ROOT.kBlack, lstyle=ROOT.kDotted)

    # Ratio
    ratio.SetLineColor(ROOT.kBlack)
    ratio.SetMarkerStyle(20)
    ratio.SetMarkerSize(.8)
    ratio.Draw('PE')

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
    parser.add_argument('--log', dest='loglevel', metavar='LEVEL', default='WARNING', help='Level for the python logging module. Can be either a mnemonic string like DEBUG, INFO or WARNING or an integer (lower means more verbose).')

    args = parser.parse_args()
    args.y_max = None
    args.r_max = None
    return args


if __name__ == '__main__':
    args = parse_args()
    loglevel = args.loglevel.upper() if not args.loglevel.isdigit() else int(args.loglevel)
    logging.basicConfig(format='%(levelname)s:%(module)s:%(funcName)s: %(message)s', level=loglevel)

    exit(main(args))
