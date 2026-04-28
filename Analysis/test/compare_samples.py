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

from ZZVBS_analysis.Analysis.plotutils import VarInfo, \
    TH1_integr_and_err, cmsDiCanvas_fromObjs, getTAxisLimits
from ZZVBS_analysis.Analysis.samples import SampleHandle
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

    sample1 = SampleHandle.from_abspath(name='sample1', title=args.title1, color=args.color1, fpaths=args.files1)
    sample2 = SampleHandle.from_abspath(name='sample2', title=args.title2, color=args.color2, fpaths=args.files2)

    os.makedirs(args.outdir, exist_ok=True)

    # Fast algorithm: search keys only in the first file
    # keys = [k.GetName() for k in sample1.files[0].GetListOfKeys()]
    # Slow algorithm: search keys in all files
    keys = {k.GetName() for k in sample1.get_keys()} & {k.GetName() for k in sample2.get_keys()}
    logging.debug('n keys: %d', len(keys))

    for key in keys:
        plot_compare(key, sample1, sample2, **vars(args))

    return 0


def plot_compare(key:str, sample1:SampleHandle, sample2:SampleHandle, **kwargs):
    logging.info('Plotting %s', key)

    h1 = sample1.get_hist(key)
    h2 = sample2.get_hist(key)
    
    if(not h1 or h1.Integral(0,-1) == 0 or not h2 or h2.Integral(0,-1) == 0):
        logging.info('- %s: one or both hists are empty; skipping', key)
        return

    if(kwargs.get('norm', False)):
        h1.Scale(1./h1.Integral(0,-1))
        h2.Scale(1./h2.Integral(0,-1))
        h1.GetYaxis().SetTitle('a.u.')
    else:
        h1.Scale(kwargs.get('scale1', 1.))
        h2.Scale(kwargs.get('scale2', 1.))
        h1.GetYaxis().SetTitle('Events')

    v1, e1 = TH1_integr_and_err(h1) if h1 is not None else (0, 0)
    v2, e2 = TH1_integr_and_err(h2) if h2 is not None else (0, 0)
    logging.debug('  1: %+.2f +- %.2f evts (%s)', v1, e1, sample1.title)
    logging.debug('  2: %+.2f +- %.2f evts (%s)', v2, e2, sample2.title)
    fr_diff_v = v2/v1-1 if v1 != 0 else float('nan')
    fr_diff_e = sqrt( ((v1**2 * e2**2) + (v2**2 * e1**2))/v1**4 ) if v1 != 0 else float('nan')
    logging.debug(' ->: %+.1f +- %.1f %%', 100*fr_diff_v, 100*fr_diff_e)
    if(not (h1 and h2)): return None

    h1.SetTitle(sample1.title)
    h2.SetTitle(sample2.title)
    h1.SetLineColor(kwargs['color1'])
    h2.SetLineColor(kwargs['color2'])
    if(key != 'FSLFO' and (not 'njets' in key.lower())):
        h1.Rebin(kwargs['rebin'])
        h2.Rebin(kwargs['rebin'])

    ratio = ROOT.TGraphAsymmErrors()
    ratio.SetName('ratio 2/1')
    ratio.GetYaxis().SetTitle(kwargs['title_r'])
    ratio.Divide(h2, h1, 'pois')

    # logging.debug('h1 (%d):', h1.GetNbinsX())
    # for n in range(h1.GetNbinsX()): logging.debug('  %2d: (%.3g, %.3g)', n, h1.GetXaxis().GetBinCenter(n), h1.GetBinContent(n))
    # logging.debug('ratio (%d):', ratio.GetN())
    # for n in range(ratio.GetN())  : logging.debug('  %2d: (%.3g, %.3g)', n, ratio.GetPointX(n), ratio.GetPointY(n))
    if(kwargs.get('logy', False)):
        y_scale = 10
        y_min = max(1e-2, h1.GetMinimum())/3
    else:
        y_scale = 1.5
        y_min = 0

    dicanvas_kwargs = dict(y_min=y_min, y_scale=y_scale, min_hi_r=1.1, max_lo_r=0.9, range_include_err=True,
                           max_hi_r=4, min_lo_r=0.,
                           iPos=11)
    canvas = cmsDiCanvas_fromObjs(key, h1, None, ratio,
                                 **dicanvas_kwargs)

    ### Upper pad ###
    canvas.cd(1)
    canvas.GetPad(1).SetLogy(kwargs.get('logy', False))

    # The legend needs to be created after the canvas, otherwise it won't be drawn
    leg_ymax = .875
    leg_ymin = leg_ymax - 0.05*(2)
    legend = cmsstyle.cmsLeg(.55, leg_ymin, .90, leg_ymax, textSize=.04)
    legend.AddEntry(h1, sample1.title, 'f') #+' (%+.1e +- %.1e)' %(v1, e1)
    legend.AddEntry(h2, sample2.title, 'f') #+' (%+.1e +- %.1e)' %(v2, e2)

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
    parser.add_argument(      '--scale1', default=1., type=float, help='global k-factor for sample 1')
    parser.add_argument(      '--scale2', default=1., type=float, help='global k-factor for sample 2')
    parser.add_argument(      '--norm'  , action='store_true', help='Normalize both 1 and 2 so that the integral is 1')
    parser.add_argument(      '--logy'  , action='store_true')
    parser.add_argument(      '--rebin' , type=int, default=1)
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

