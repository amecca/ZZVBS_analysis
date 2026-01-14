#!/usr/bin/env python3

################################################################
# Run the VBS ZZ analysis on NanoAOD files                     #
#                                                              #
# Author: Alberto Mecca (alberto.mecca@cern.ch)                #
# Initial revision: 2025-07-09                                 #
################################################################

import os
import sys
from argparse import ArgumentParser, Namespace
import logging
from time import time

import ROOT

from ZZAnalysis.NanoAnalysis.tools import setConf

from ZZVBS_analysis.Analysis.utils import TFileContext, mkhist, FinalState
from ZZVBS_analysis.Analysis.libutils import find_load_lib


def main(args):
    logging.debug('args: %s', args)

    if(args.multithread):
        ROOT.EnableImplicitMT()

    # Get the Events tree
    df = ROOT.RDataFrame(
        'Events'
        # 'ZZTree/candTree'
        , args.fname_in)

    if(args.list_columns):
        print(df.Describe())
        return 0

    # Load shared libraries
    ROOT.gInterpreter.AddIncludePath('../interface')
    find_load_lib('cConstants')

    # Run the analysis
    t_start = time()
    histograms = analyze(df, args)
    t_end = time()
    logging.info('Time elapsed: %g s', t_end-t_start)

    # Write histograms
    with TFileContext(args.fname_out, 'RECREATE') as tf_out:
        for hist in histograms:
            hname = hist.GetName()

            path_elems = hname.split('/')
            path_elems.reverse()
            curdir = tf_out
            logging.debug('h name: %s -> %s', hname, path_elems)
            while(len(path_elems) > 1):
                dirname = path_elems.pop()
                logging.debug('    making dir "%s"', dirname)
                curdir = curdir.mkdir(dirname)
                curdir.cd()
            basename = path_elems.pop()

            if('FSLFO' in hname): fix_xlabels_FSLFO(hist)
    
            hist.Write(basename)
            logging.debug('wrote "%s"', basename)
            tf_out.cd()
    logging.info('wrote %d histograms to "%s"', len(histograms), args.fname_out)

    ROOT.RDF.SaveGraph(df, './nano2hists.dot')

    return 0


def main_fromdict(**kwargs):
    '''Utility to call the main from another script with keyword arguments'''
    main(Namespace(kwargs))


def parse_args():
    parser = ArgumentParser('Run the VBS ZZjj analysis on a NanoAOD file from ZZ (Run 3)',
                            epilog='outputs ROOT files with histograms. For efficiency, '
                            'the fancy plot formatting is in a separate step')
    parser.add_argument('fname_in', metavar='FILE', help='Input: (post-processed) NanoAOD file')
    parser.add_argument('-o', '--output', default=None, dest='fname_out', metavar='FILE', help='Default: %(default)s')
    parser.add_argument(      '--list', dest='list_columns', action='store_true', help='List the columns present in the input file and exit')
    parser.add_argument('-n', '--max-entries', type=int, default=0, metavar='N', help='Process a maximum of N entries (disables multithreading)')
    # parser.add_argument(      '--mt'   , dest='multithread', action='store_true' , help='Enable ROOT implicit multithread (default)', default=True)
    parser.add_argument(      '--no-mt', dest='multithread', action='store_false', help='Disable ROOT implicit multithread (output entries will not be ordered)')
    parser.add_argument('--log', dest='loglevel', metavar='LEVEL', default='WARNING', help='Level for the python logging module. Can be either a mnemonic string like DEBUG, INFO or WARNING or an integer (lower means more verbose).')
    args = parser.parse_args()

    if(args.max_entries > 0):
        args.multithread = False
    if(args.fname_out is None):
        split = os.path.splitext(args.fname_in)
        args.fname_out = split[0]+'_hists' + split[1]

    return args


def analyze(df, args):
    tot_entries = df.Count().GetValue()
    logging.info(    'Total entries   : %d', tot_entries)

    if(args.max_entries > 0):
        max_entries = min(args.max_entries, tot_entries)
        df = df.Range(0, max_entries)
        logging.info('Filtered entries: %d', max_entries)

    futures = [] # <ROOT.RDF.RResultPtr>
    histograms = [] # <ROOT.TH1F>

    # Aliases
    df = df.Alias('weight', 'overallEventWeight')
    df = df.Define('ZZ_mass', 'ZZCand_mass[bestCandIdx]')
    df = df.Define('ZZ_KD'  , 'ZZCand_KD[bestCandIdx]')
    df = df.Define('j1_eta', 'Jet_eta[JetLeadingIdx]')
    df = df.Define('j2_eta', 'Jet_eta[JetSubleadingIdx]')
    df = df.Define('absdetajj', 'fabs(j1_eta-j2_eta)')
    df = df.Define('Z1flav', 'ZZCand_Z1flav[bestCandIdx]')
    df = df.Define('Z2flav', 'ZZCand_Z2flav[bestCandIdx]')
    df = df.Define('FSLFO', 'get_FSLFO(Z1flav, Z2flav)') # Final State, Lepton Flavour Order (ie 2e2mu != 2mu2e)

    # Selection
    df = df.Filter(*['ZZ_mass > 100']*2)
    df = df.Filter(*['nJet >= 2'    ]*2)
    df = df.Filter(*['absdetajj > 1']*2)

    # Request some histograms
    futures.append(mkhist(df, 'ZZ_mass', ';m_{ZZ} [GeV]', 60,0,600))
    futures.append(mkhist(df, 'ZZ_KD'  , ';KD', 50,0,1))
    futures.append(mkhist(df, 'absdetajj', ';|#Delta #eta_{jj}|', 60,0,6))
    futures.append(mkhist(df, 'FSLFO', ';Final state', 4,0,4))

    # Histograms by channel
    for fs in FinalState:
        if fs == FinalState.fs4l: continue
        df_ch = df.Filter('FSLFO==%d' %(fs.value))
        fsname = fs.name.replace('fs','')
        fstitle= fsname.replace('mu','#mu').strip()
        futures.append(mkhist(df_ch, 'ZZ_mass_%s'%(fsname), ';m_{ZZ} [GeV], %s'%(fstitle), 60,0,600, v='ZZ_mass'))

    # MELA probabilities (automatic from the branch names)
    branches = [str(b) for b in df.GetColumnNames()]
    branches_prob = [b for b in branches if b.startswith('ZZCand_P_')]
    probs = [p[len('ZZCand_P_'):] for p in branches_prob]
    logging.debug('MELA probs (%d): %s', len(probs), probs)
    for prob in probs:
        value = 'ZZCand_P_{0}[bestCandIdx]'.format(prob)
        logging.debug('%s: %s', prob, value)
        df = df.Define(prob, value)
        df = df.Define(prob+'_log', 'log(%s)'%(prob))
        if  (prob == 'JJVBF_BKG_MCFM_JECNominal'): title = 'EW'
        elif(prob == 'JJQCD_BKG_MCFM_JECNominal'): title = 'QCD'
        else: title = prob
        futures.append(mkhist (df, 'MELA_'+prob       , ';P(%s)'     %(title), 50, 0 , 1, v=prob))
        futures.append(mkhist (df, 'MELA_'+prob+'_log', ';log(P(%s))'%(title), 50,-50, 0, v=prob+'_log'))

    # Mela ratio
    if(all(p in probs for p in ('JJVBF_BKG_MCFM_JECNominal', 'JJQCD_BKG_MCFM_JECNominal'))):
        df = df.Define('P_EWK', 'ZZCand_P_{0}[bestCandIdx]'.format('JJVBF_BKG_MCFM_JECNominal'))
        df = df.Define('P_QCD', 'ZZCand_P_{0}[bestCandIdx]'.format('JJQCD_BKG_MCFM_JECNominal'))
        df = df.Define('ratio_EW_EWpQCD', 'P_EWK/(P_EWK+P_QCD)')
        futures.append(mkhist (df, 'ratio_EW_EWpQCD', ';P_{EW}/(P_{EW}+P_{QCD})', 51, 0, 1+1./50))
    else:
        df = df.Define('P_EWK', '0').Define('P_QCD', '0')

    zeroMELA = df.Filter("P_EWK == 0 && P_QCD == 0")
    n_zeroMELA = zeroMELA.Count()
    n_total = df.Count()

    logging.info("Finished setting up the analysis")

    # Calling GetValue() on a RResultPtr causes the event loop to run
    histograms = [f.GetValue() for f in futures]
    df.Report().GetValue().Print()
    logging.info('Events with MELA==0 / total: %d/%d', n_zeroMELA.GetValue(), n_total.GetValue())

    return histograms


def fix_xlabels_FSLFO(h):
    xaxis = h.GetXaxis()
    xaxis.SetBinLabel(1, '4e')
    xaxis.SetBinLabel(2, '2e2#mu')
    xaxis.SetBinLabel(3, '2#mu2e')
    xaxis.SetBinLabel(4, '4#mu')


if __name__ == '__main__':
    args = parse_args()
    loglevel = args.loglevel.upper() if not args.loglevel.isdigit() else int(args.loglevel)
    logging.basicConfig(format='%(levelname)s:%(module)s:%(funcName)s: %(message)s', level=loglevel)

    exit(main(args))
