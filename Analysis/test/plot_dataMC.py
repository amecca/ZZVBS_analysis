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
from plotutils import VarInfo, \
    DRAW_STYLE, \
    TH1_integr_and_err, cmsDiCanvas_fromObjs, getTAxisLimits
from utils import lumi_dict
from samples import SampleInfo, SampleHandle, get_samples_info


### To be moved to a separate configuration file?
variable_dicts = [
    {'name': 'ratio_EW_EWpQCD', 'blind':True, 'logy': True, 'y_scale': 1e3},
    {'name':'absdetajj', 'xtitle':'|#Delta#eta(j1,j2)|', 'logy':True, 'rebin':4, 'y_scale': 1e7},
    {'name':'nJets', 'logy':True, 'y_scale': 1e6},
    *[{'name': Zxlx+'_eta'    , 'y_scale': 3, 'rebin':5} for Zxlx in ('Z1l1','Z1l2','Z2l1','Z2l2')],
    *[{'name': Zxlx+'_phinorm', 'y_scale': 3, 'rebin':5} for Zxlx in ('Z1l1','Z1l2','Z2l1','Z2l2')],
    # {'name': 'ZZ_mass', 'blind':True},
    {'name': 'ZZ_Muon_minmvaLowPt', 'logy':True, 'y_min': 1e-2},
    # {'name': 'ZZ_leadingMu_eta', 'rebin':1},
    # {'name': 'ZZ_subleadMu_eta', 'rebin':1},
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
    info_data, infos_MCs = get_samples_info(region='4P')
    sample_data = SampleHandle.from_info(info_data, dirpath=args.inputdir)

    samples_MC = []
    for v in infos_MCs:
        if(v is None):
            logging.warning('Missing sample "%s"', name)
            continue

        s = SampleHandle.from_info(v, dirpath=args.inputdir)
        samples_MC.append(s)

    # Defaults for non-customized vars:
    all_keys = {k.GetName() for k in samples_MC[0].get_keys()}
    print('\t'+'\n\t'.join(sorted(all_keys)))
    all_keys = {k for k in all_keys if not k.endswith(('-Up', '-Dn'))}
    new_keys = all_keys - {v.name for v in variables}
    variables.extend([VarInfo(name=n, rebin=args.rebin) for n in new_keys])

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
        if  (var.name.startswith('VBSloose-ratio')):
            var.extra['y_min'] = 1e-2
        if  (var.name.startswith('VBStight-ratio')):
            var.extra['y_min'] = 1e-3
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
        h.Scale(sample.kfactor)
        if(var.rebin is not None): h.Rebin(var.rebin)
        i, e = TH1_integr_and_err(h)
        logging.debug('Add %s: %+7.5g +- %+7.5g', sample.name, i, e)
        stack.Add(h)
        leg_title = sample.title
        if(args.add_yield):
            if(abs(sample.kfactor-1) > 1e-6):
                leg_title += ' x%s'%(sample.kfactor)
            leg_title += ' (%.3g)'%(i)
        refs_for_legend.append([h, leg_title])

    if(stack.GetNhists() == 0):
        logging.error('No MC histograms for %s', var.name)
        return 1

    last_stack = stack.GetStack().Last()
    if(var.xtitle is None): var.xtitle = last_stack.GetXaxis().GetTitle()

    ### DATA ###
    is_unblind = args.unblind or (not var.blind)
    if(is_unblind):
        hdata = sample_data.get_hist(var.name)
        if(var.rebin is not None): hdata.Rebin(var.rebin)
    else:
        hdata = last_stack.Clone('data_asimov')
        hdata.SetTitle('data (blind)')
        for b in range(0, hdata.GetNbinsX()+2):
            hdata.SetBinContent(b, 0)
            hdata.SetBinError  (b, 0)

    # Ratio
    ratio = ROOT.TGraphAsymmErrors()
    ratio.SetName('ratio')
    logging.debug('data: %s', hdata)
    logging.debug('MC  : %s', last_stack)
    if(is_unblind):
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
        dicanvas_kwargs['y_min'  ] = var.extra.get('y_min'  , 1e-1)
    else:
        dicanvas_kwargs['y_scale'] = var.extra.get('y_scale', 2)
        dicanvas_kwargs['y_min'  ] = var.extra.get('y_min'  , 0)
    canvas = cmsDiCanvas_fromObjs(var.name, last_stack, hdata, ratio,
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
        leg_title = DRAW_STYLE['labels']['data']
        if(args.add_yield):
            i, _ = TH1_integr_and_err(hdata)
            leg_title += ' (%.3g)'%(i)
        legend.AddEntry(hdata, leg_title, 'lpe')

    # Error band in the upper canvas
    hMCErr = deepcopy(last_stack)
    legend.AddEntry(hMCErr, DRAW_STYLE['labels']['MCerr'], "f")

    # Fill legend
    for h, title in refs_for_legend:
        legend.AddEntry(h, title, 'f')

    # Region label
    split = var.name.split('-')
    if(args.region_label and split[0].startswith('VBS')):
        logging.debug('Adding TPaveText -> %s', split[0])
        pave_text = ROOT.TPaveText(
            ROOT.gPad.GetLeftMargin() + 0.025,
            1 - ROOT.gPad.GetTopMargin() - 0.15,
            0.6,
            1 - ROOT.gPad.GetTopMargin() - 0.22,
            "NB NDC"
        )
        pave_text.AddText(split[0].replace('VBS', 'ZZjj ').replace('incl', 'inclusive'))
        pave_text.SetTextAlign(ROOT.ETextAlign.kHAlignLeft + ROOT.ETextAlign.kVAlignTop)
    else:
        logging.debug('No TPaveText for %s', var.name)
        pave_text = None

    # Draw
    if(pave_text is not None):
        cmsstyle.cmsObjectDraw(pave_text, TextSize=.05, FillColor=ROOT.kWhite)
    cmsstyle.cmsObjectDraw(stack, 'HIST')
    cmsstyle.cmsObjectDraw(hMCErr, **DRAW_STYLE['MCerr'])
    if(hdata is not None):
        cmsstyle.cmsObjectDraw(hdata, **DRAW_STYLE['data'])

    ### Lower pad ###
    canvas.cd(2)

    # Line y=1 in the ratio plot
    x_min, x_max = getTAxisLimits(hdata.GetXaxis())
    logging.debug('x_min=%.3g, x_max=%.3g', x_min, x_max)
    ref_line = ROOT.TLine(x_min, 1, x_max, 1)
    cmsstyle.cmsDrawLine(ref_line, lcolor=ROOT.kBlack, lstyle=ROOT.kDotted)

    # Gray area representing MC error
    pred_ratio = last_stack.Clone('pred_ratio')
    pred_ratio.Divide(stack.GetStack().Last())
    cmsstyle.cmsObjectDraw(pred_ratio, **DRAW_STYLE['MCerr'])

    # Ratio
    if(is_unblind):
        cmsstyle.cmsObjectDraw(ratio, **DRAW_STYLE['ratio'])
    else:
        x_start = (x_min + x_max)/2 - (x_max - x_min)/8
        text = ROOT.TText(x_start, 1.2, "BLINDED")
        text.SetTextSize(.12)
        text.Draw("same")

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
    parser.add_argument(      '--yield'  , dest='add_yield' , action='store_true', help='Write the yield of each process in the legend')
    parser.add_argument(      '--rebin'  , default=1, type=int, help='A default value for plots that do not specify one (default: %(default)d)')
    parser.add_argument(      '--region-label', action='store_true')
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
