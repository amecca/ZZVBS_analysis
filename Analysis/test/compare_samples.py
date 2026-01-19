#!/usr/bin/env python3

######################################################################
# Compare histograms from two MC samples (made of one or more files) #
#                                                                    #
# Author: Alberto Mecca (alberto.mecca@cern.ch)                      #
# Initial revision: 2025-11-13                                       #
######################################################################

import os
from argparse import ArgumentParser, Namespace
import logging
from math import log10, ceil, sqrt
import ROOT
import cmsstyle

from ZZVBS_analysis.Analysis.plotutils import VarInfo, SampleHandle, \
    TH1_integr_and_err, cmsDiCanvas_fromTH1, getTAxisLimits
from ZZVBS_analysis.Analysis.utils import lumi_dict


def main(args: Namespace):
    logging.debug('args = %s', args)
    ROOT.gROOT.SetBatch(True)

    cmsstyle.SetExtraText("Preliminary")
    cmsstyle.setCMSStyle()
    cmsstyle.SetEnergy(13.6)
    lumi_val = lumi_dict[args.year]['value']/1000.
    lumi_decimals = (3 - ceil(log10(lumi_val))) # 3 significative digits
    cmsstyle.SetLumi(lumi_val, run=args.year, round_lumi=lumi_decimals)

    sample1 = SampleHandle(name='sample1', title=args.title1, color=args.color1, fpaths=args.files1)
    sample2 = SampleHandle(name='sample2', title=args.title2, color=args.color2, fpaths=args.files2)

    os.makedirs(args.outdir, exist_ok=True)

    # Fast algorithm: search keys only in the first file
    # keys = [k.GetName() for k in sample1.files[0].GetListOfKeys()]
    # Slow algorithm: search keys in all files
    keys = {k.GetName() for f in sample1.files + sample2.files for k in f.GetListOfKeys()}

    for key in keys:
        plot_compare(key, sample1, sample2, **vars(args))

    return 0


def plot_compare(key:str, sample1:SampleHandle, sample2:SampleHandle, **kwargs):
    logging.info('Plotting %s', key)

    h1 = sample1.get_hist(key)
    h2 = sample2.get_hist(key)
    v1, e1 = TH1_integr_and_err(h1) if h1 is not None else (0, 0)
    v2, e2 = TH1_integr_and_err(h2) if h2 is not None else (0, 0)
    logging.debug('  1: %+.2f +- %.2f evts (%s)', v1, e1, sample1.title)
    logging.debug('  2: %+.2f +- %.2f evts (%s)', v2, e2, sample2.title)
    logging.debug(' ->: %+.1f +- %.1f %%', 100*(v2/v1-1), 100*sqrt( ((v1**2 * e2**2) + (v2**2 * e1**2))/v1**4 ))
    if(not (h1 and h2)): return None

    h1.SetTitle(sample1.title)
    h2.SetTitle(sample2.title)
    h1.SetLineColor(kwargs['color1'])
    h2.SetLineColor(kwargs['color2'])

    ratio = ROOT.TGraphAsymmErrors()
    ratio.SetName('ratio 2/1')
    ratio.GetYaxis().SetTitle(kwargs['title_r'])
    ratio.Divide(h2, h1, 'pois')

    # logging.debug('h1 (%d):', h1.GetNbinsX())
    # for n in range(h1.GetNbinsX()): logging.debug('  %2d: (%.3g, %.3g)', n, h1.GetXaxis().GetBinCenter(n), h1.GetBinContent(n))
    # logging.debug('ratio (%d):', ratio.GetN())
    # for n in range(ratio.GetN())  : logging.debug('  %2d: (%.3g, %.3g)', n, ratio.GetPointX(n), ratio.GetPointY(n))

    dicanvas_kwargs = dict(y_min=0, y_scale=1.5, min_hi_r=1.5, max_lo_r=0.5, range_include_err=True,
                           max_hi_r=4., min_lo_r=0.,
                           iPos=11)
    canvas = cmsDiCanvas_fromTH1(key, h1, ratio,
                                 **dicanvas_kwargs)

    ### Upper pad ###
    canvas.cd(1)

    # The legend needs to be created after the canvas, otherwise it won't be drawn
    leg_ymax = .875
    leg_ymin = leg_ymax - 0.05*(2)
    legend = cmsstyle.cmsLeg(.55, leg_ymin, .90, leg_ymax, textSize=.04)
    legend.AddEntry(h1, sample1.title, 'f')
    legend.AddEntry(h2, sample2.title, 'f')

    # Draw
    h1.Draw('SAMEHIST')
    h2.Draw("SAMEHIST")

    ### Lower pad ###
    canvas.cd(2)

    # Line y=1 in the ratio plot
    x_min, x_max = getTAxisLimits(h1.GetXaxis())
    logging.debug('x_min=%.3g, x_max=%.3g', x_min, x_max)
    ref_line = ROOT.TLine(x_min, 1, x_max, 1)
    cmsstyle.cmsDrawLine(ref_line, lcolor=ROOT.kBlack, lstyle=ROOT.kDotted)

    # Ratio
    ratio.SetLineColor(ROOT.kBlack)
    ratio.SetMarkerStyle(20)
    ratio.SetMarkerSize(.8)
    ratio.Draw('PE')

    for ext in ['png', 'pdf']:
        outfname = os.path.join(kwargs['outdir'], key+'.'+ext)
        canvas.SaveAs(outfname)


def parse_args():
    parser = ArgumentParser(description='Compare two samples histogram-by-histogram')
    parser.add_argument('-1', '--files1', nargs='+', required=True, metavar='FILE', help='List of files of sample 1')
    parser.add_argument('-2', '--files2', nargs='+', required=True, metavar='FILE')
    parser.add_argument(      '--color1', default='kRed'    , help='Default: %(default)s')
    parser.add_argument(      '--color2', default='kBlue'   , help='Default: %(default)s')
    parser.add_argument(      '--title1', default='Sample 1', help='Label in the legend (default: %(default)s)')
    parser.add_argument(      '--title2', default='Sample 2', help='Label in the legend (default: %(default)s)')
    parser.add_argument(      '--title-r',default='2/1'     , help='Y axis label in the ratio plot (default: %(default)s)')
    parser.add_argument('-o', '--outdir', default='comparesamples', metavar='DIR', help='Directory where plots will be saved. Default: %(default)s')
    parser.add_argument('-y', '--year', default='2022EE', help='Used to get lumi information')
    parser.add_argument('--log', dest='loglevel', metavar='LEVEL', default='WARNING', help='Level for the python logging module. Can be either a mnemonic string like DEBUG, INFO or WARNING or an integer (lower means more verbose).')

    args = parser.parse_args()
    args.color1 = getattr(ROOT, args.color1)
    args.color2 = getattr(ROOT, args.color2)
    return args


if __name__ == '__main__':
    args = parse_args()
    loglevel = args.loglevel.upper() if not args.loglevel.isdigit() else int(args.loglevel)
    logging.basicConfig(format='%(levelname)s:%(module)s:%(funcName)s: %(message)s', level=loglevel)

    exit(main(args))

