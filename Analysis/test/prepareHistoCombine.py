#!/usr/bin/env python3

#############################################################################################
# Get histograms from an analyzer's results (file: sample, inside has histograms: variable) #
# and write it in a form usable by Combine (file: variable, inside histograms: sample       #
# Author: A. Mecca                                                                          #
#############################################################################################

import os
import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import logging
import re
from array import array
import json
from collections import defaultdict
import ROOT

sys.path.append('../../.python')
from ZZVBS_analysis.Analysis.samples import get_samples_info, add_list_TObj, SampleHandle #, InputDir
from ZZVBS_analysis.Analysis.utils import lumi_dict, TFileContext
from ZZVBS_analysis.Analysis.plotutils import retrieve_bin_edges, \
    TH1_integr_and_err, fix_low_bins
from ZZVBS_analysis.Analysis.combineutils import get_shape_uncorrelated, get_shape_correlyear, get_shape_groups, get_sample_group, SystNameHelper


MIN_BIN_CONTENT = 1e-7
DIRECTION_RENAME = {
    'Up': 'Up',
    'Dn': 'Down',
    '': ''
}


def main(args):
    # Setup
    ok_retrieved  = []
    not_retrieved = []
    fixed_bins = defaultdict(lambda : 0.)

    # Start
    path_out = args.outputdir
    region = None #TODO take from config
    path_in = args.inputdir #InputDir(basedir=args.inputdir, year=args.year, region=region).path()

    # Get systematics that have shape and or are uncorrelated from the config
    with open(args.config) as f:
        config = json.load(f)
    conf_syst = config["systematics"]

    # DEBUG configuration
    systs_shape_uncorr     = get_shape_uncorrelated(conf_syst)
    systs_shape_correlyear = get_shape_correlyear  (conf_syst)
    systs_shape_groups     = get_shape_groups      (conf_syst)
    logging.info('Systematics with shape and uncorrelated: %s', systs_shape_uncorr)
    logging.info('Systematics with shape and correlated between pre/post of a year: %s', systs_shape_correlyear)
    logging.info('Systematics with shape, correlated in group of samples: %s', systs_shape_groups)

    # Input histograms
    data_info, MC_infos = get_samples_info(region=region)
    data_info.name = 'data_obs'

    logging.debug('data_info: %s', data_info.name)
    logging.debug('MC_infos : %s', [s.name for s in MC_infos])

    # Open MC files
    MC_handles = [SampleHandle.from_info(info, dirpath=path_in) for info in MC_infos]

    # Add data
    if(args.unblind):
        data_handle = SampleHandle.from_info(data_info, dirpath=path_in)

    # Dict {syst: Helper} used to choose the output histogram names
    syst_helpers = {}

    # Sometimes the yield in data.root may be 0. In this case we must insert an empty histogram with the appropriate xaxis
    xbins_dict = dict()

    necessary_keys_names = set(k for handle in handles for k in handle.get_keys_names() if k.endswith('-nominal'))

    # Write to output
    with TFileContext(os.path.join(path_out, args.year+'.root'), "RECREATE") as fout:
        for handle in MC_handles + [data_handle]:
            logging.info('sample = %s', handle.name)

            handle_keys = sorted(set.union(handle.get_keys_names(), necessary_keys_names))
            for key_name in handle_keys:
                path_elems = key_name.split('/')
                variable = path_elems[-1]
                path_elems = path_elems[:-1]
                #if(not 'ZZ_mass' in variable): continue #TEMP

                split = variable.split('-')
                if(len(split) < 2): continue

                var_split = split[0].split(':')
                var_name = var_split[0]
                prompt = ':'+var_split[1] if len(var_split) > 1 else ''
                syst = split[1]
                direction = split[2] if len(split) > 2 else ''
                direction = DIRECTION_RENAME[direction]
                # logging.debug(f'{key_name=} -> {path_elems=} -> {variable=} -> {split=} -> {var_name=} {syst=}, {direction=}')

                if('/' in var_name): raise RuntimeError('slash in name "%s"; full name: "%s"', variable, key_name)

                skipIfData = not syst == 'nominal'

                # Decide the name of the output histogram
                # The helper is cached based on the syst name
                syst_helper = syst_helpers.get(syst)
                if(syst_helper is None):
                    syst_helper = SystNameHelper(syst, config['systematics'])
                    syst_helpers[syst] = syst_helper
                syst_out_name = syst_helper.outname(sample=handle.name, year=args.year)
                out_name = '{sample}{prompt}-{syst_out_name}{direction}'.format(
                    **locals(), sample=handle.name)

                # Sub-directory for the original structure + variable name
                fout.cd()
                curdir = fout
                path_elems.append(var_name) # e.g. mZZ, mZZG
                path_elems.reverse()
                while(len(path_elems) > 0):
                    dirname = path_elems.pop()
                    newdir = curdir.Get(dirname)
                    curdir = newdir if newdir else curdir.mkdir(dirname)
                    curdir.cd()

                # Write the histograms with the appropriate name
                if(handle.name == 'data_obs' and skipIfData):
                    continue
                h = handle.get_hist(key_name)
                if(h):
                    h.SetName(out_name)
                    h.Scale(handle.kfactor)

                    # Set the empty and negative bins to a small value, and add to the counter
                    # of bins fixed for a certain variable
                    fixed_bins[var_name+'/'+h.GetName()] += fix_low_bins(h, v=MIN_BIN_CONTENT)

                    h.Write()
                    ok_retrieved.append( {'sample': handle.name, 'variable':variable})
                    if(syst == 'central'):  # Save bin edges in case we need it
                        xbins = retrieve_bin_edges(h.GetXaxis())
                        xbins_dict.setdefault(variable, xbins)
                    h.SetDirectory(0)
                    del h
                else:
                    not_retrieved.append({'sample':handle.name, 'variable':variable})
                    if(handle.name == 'data_obs'):  # data_obs must not be missing
                        logging.error('data_obs (%s) is missing "%s" - replacing with empty histogram', file_in.GetName(), variable)
                        xbins = xbins_dict[variable]
                        h = ROOT.TH1F(out_name, '', len(xbins) - 1, xbins)
                        h.Write()
                        h.SetDirectory(0)
                        del h

    logging.debug('Closing files')

    # Missing files
    files_prob = { e['file'] for e in not_retrieved }  # set()
    max_len = max([len(f) for f in files_prob]) if len(files_prob) > 0 else 0
    format_str = 'From file {:%d.%ds} could not retrieve {:d}/{:d} plots' % (max_len, max_len)
    for file_prob in sorted(files_prob):
        problems = [e['variable'] for e in not_retrieved if e['file'] == file_prob]
        good     = [e['variable'] for e in  ok_retrieved if e['file'] == file_prob]
        logging.warning(format_str.format(file_prob, len(problems), len(problems)+len(good)))

    # Missing central histograms
    hists_prob         = { e['variable'] for e in not_retrieved }
    hists_prob_central = { e for e in hists_prob if e.endswith('central') }
    hists_prob_updn    = { e.rstrip('_Up').rstrip('_Down') for e in hists_prob if e.endswith(('Up', 'Down')) }
    for hist_prob in sorted(hists_prob_central):
        problems = [ e['file'] for e in not_retrieved if e['variable'] == hist_prob ]
        good     = [ e['file'] for e in  ok_retrieved if e['variable'] == hist_prob ]
        msg = 'Histogram {:40.40s} was missing {:2d}/{:2d} times'.format(hist_prob            , len(problems), len(good)+len(problems))
        if(len(problems) < 10):
            msg += ': '+' '.join([f.split('/')[-1] for f in problems])
            logging.info(msg)

    # Missing up/dn histograms
    for hist_prob in sorted(hists_prob_updn):
        problems = [ e['file'] for e in not_retrieved if e['variable'].startswith(hist_prob) ]
        good     = [ e['file'] for e in  ok_retrieved if e['variable'].startswith(hist_prob) ]
        msg = 'Histogram {:40.40s} was missing {:2d}/{:2d} times'.format(hist_prob+'(Up/Down)', len(problems), len(good)+len(problems))
        if(len(problems)/2 < 10):
            msg += ': '+' '.join({f.split('/')[-1] for f in problems})
        logging.info(msg)

    # Save detailed info on what was fixed
    logging.warning('Fixed %d bins in %d histograms (full info in fixed_bins.json)', sum(v for k,v in fixed_bins.items()), len(fixed_bins))
    fixed_bins_sorted = {k:fixed_bins[k] for k in sorted(fixed_bins.keys())}
    with open('fixed_bins.json', 'w') as f:
        json.dump(fixed_bins_sorted, f, indent=2)

    logging.info('Retrieved and wrote {:d} histograms. {:d} were missing. Total: {:d}'.format(len(ok_retrieved), len(not_retrieved), len(ok_retrieved)+len(not_retrieved)))
    return 0


def parse_args():
    available_regions = ['SR4P', 'CR3P1F' , 'CR2P2F' , 'SR4P_1L', 'SR4P_1P', 'CR4P_1F', 'CR4L',
               'SR3P', 'CR110'  , 'CR101'  , 'CR011'  , 'CR100'  , 'CR001'  , 'CR010', 'CR000', 'SR3P_1L', 'SR3P_1P', 'CR3P_1F', 'CRLFR', 'CR3L',
               'SR2P', 'SR2P_1L', 'SR2P_1P', 'CR2P_1F'
               # 'SR_HZZ', 'CR2P2F_HZZ', 'CR3P1F_HZZ', 'CR_HZZ', 'MC_HZZ',
               # 'MC'
    ]

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter,
                            description='Make a rootfile organized as input for Combine from histograms produced by running on the ntuples')
    parser.add_argument('inputdir', metavar='DIR', help='Top level directory where the input histograms')
    parser.add_argument('-c', '--config'   , required=True,
                        help='Config file (JSON) that describes how to set up the analysis:'
                        ' which variables to fit, which systematics have shape, which are correlated and how, etc.')
    parser.add_argument('-y', '--year'     , required=True, choices=lumi_dict.keys())
    parser.add_argument(      '--blind'    , action='store_true', help='Do not write data_obs in output files')
    parser.add_argument('-o', '--outputdir', default='histogramsForCombine', help='Output location')
    parser.add_argument('--log', dest='loglevel', metavar='LEVEL', default='WARNING', help='Level for the python logging module. Can be either a mnemonic string like DEBUG, INFO or WARNING or an integer (lower means more verbose).')
    args = parser.parse_args()
    args.unblind = not args.blind

    return args


# Utility functions

# Output nominal
# schema: <year>.root -> <variable>/<sample>-nominal
# example: 2016.root  -> ZZ_mass/ZZTo4l-nominal

# Output systematics
# schema: <year>.root -> <variable>/<sample>-CMS_<syst>(Up|Down)
# example: 2016.root  -> ZZ_mass/ZZTo4l-CMS_eff_eUp


def get_shape_down(h_ce, h_up):
    h_dn_name = h_up.GetName().replace('_Up', '_Down')
    logging.debug('h_dn_name: %s', h_dn_name)
    h_dn = h_up.Clone(h_dn_name)
    for b in range(0, h_ce.GetNbinsX()+2):
        v_ce = h_ce.GetBinContent(b)
        v_up = h_up.GetBinContent(b)
        e_ce = h_ce.GetBinError(b)
        e_up = 0 #h_up.GetBinError(b)
        v_dn = max(0, 2*v_ce - v_up) # v_ce - (v_up-v_ce) = 2*v_ce - v_up
        e_dn = 0 #min(v_dn, e_up)  # the error is the same as that on the up bin, but capped so that it never goes below 0  # sqrt(2*e_ce**2 + e_up**2)
        # logging.debug('%2d: ce: %.3g+-%.3g - up: %.3g+-%.3g - dn: %.3g+-%.3g', b, v_ce, e_ce, v_up, e_up, v_dn, e_dn)
        h_dn.SetBinContent(b, v_dn)
        h_dn.SetBinError(b, e_dn)
    return h_dn


if __name__ == '__main__':
    args = parse_args()
    loglevel = args.loglevel.upper() if not args.loglevel.isdigit() else int(args.loglevel)
    logging.basicConfig(format='%(levelname)s:%(module)s:%(funcName)s: %(message)s', level=loglevel)

    exit(main(args))
