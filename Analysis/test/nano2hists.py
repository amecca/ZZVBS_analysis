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

# Python doesn't like names starting with a digit; to import from modules
# in "4l_channel" we have a few options:
# - rename the directory (e.g. to channel_4l)
# - try to do stuff with importlib
# - append the absolute path to "4l_channel/python/" to sys.path
sys.path.append(os.path.realpath('../python'))
from utils import TFileContext, mkhist


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
    
            hist.Write(basename)
            logging.debug('wrote "%s"', basename)
            tf_out.cd()
    logging.info('wrote %d histograms to "%s"', len(histograms), args.fname_out)

    return 0


def main_fromdict(**kwargs):
    '''Utility to call the main from another script with keyword arguments'''
    main(Namespace(kwargs))


def parse_args():
    parser = ArgumentParser('Run the VBS ZZjj analysis on a NanoAOD file from ZZ (Run 3)',
                            epilog='outputs ROOT files with histograms. For efficiency, '
                            'the fancy plot formatting is in a separate step')
    parser.add_argument('fname_in', metavar='FILE', help='Input: (post-processed) NanoAOD file')
    parser.add_argument('-o', '--output', default='hists.root', dest='fname_out', metavar='FILE', help='Default: %(default)s')
    parser.add_argument(      '--list', dest='list_columns', action='store_true', help='List the columns present in the input file and exit')
    parser.add_argument('-n', '--max-entries', type=int, default=0, metavar='N', help='Process a maximum of N entries (disables multithreading)')
    # parser.add_argument(      '--mt'   , dest='multithread', action='store_true' , help='Enable ROOT implicit multithread (default)', default=True)
    parser.add_argument(      '--no-mt', dest='multithread', action='store_false', help='Disable ROOT implicit multithread (output entries will not be ordered)')
    parser.add_argument('--log', dest='loglevel', metavar='LEVEL', default='WARNING', help='Level for the python logging module. Can be either a mnemonic string like DEBUG, INFO or WARNING or an integer (lower means more verbose).')
    args = parser.parse_args()

    if(args.max_entries > 0):
        args.multithread = False

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

    # Selection
    df = df.Filter('ZZ_mass > 100')
    df = df.Filter('nJet >= 2')
    df = df.Filter('absdetajj > 1')

    # Request some histograms
    futures.append(mkhist(df, 'ZZ_mass', '', 60,0,600))
    futures.append(mkhist(df, 'ZZ_KD'  , '', 50,0,1))
    futures.append(mkhist(df, 'absdetajj', '', 60,0,6))

    logging.info("Finished setting up the analysis")

    # Calling GetValue() on a RResultPtr causes the event loop to run
    histograms = [f.GetValue() for f in futures]
    df.Report().GetValue().Print()

    return histograms


if __name__ == '__main__':
    args = parse_args()
    loglevel = args.loglevel.upper() if not args.loglevel.isdigit() else int(args.loglevel)
    logging.basicConfig(format='%(levelname)s:%(module)s:%(funcName)s: %(message)s', level=loglevel)

    exit(main(args))
