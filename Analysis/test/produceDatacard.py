#!/usr/bin/env python3

import os
import sys
import json
import re
import string
import copy
from math import isnan
import pandas as pd
from argparse import ArgumentParser
import logging

sys.path.append('../../.python')
from ZZVBS_analysis.Analysis.samples import get_samples_info
from ZZVBS_analysis.Analysis.utils import lumi_dict, lumi_unc_dict, TFileContext
from ZZVBS_analysis.Analysis.combineutils import SystNameHelper, SystHelperCache, fillDataFrame
from systematics import SystDB

# Threshold on the difference between the up and down variation
# necessary to consider a lnN asymmetric instead of symmetric
LNN_ASYMM_THR = 0.05


__builtin_template__ = '''\
imax {imax} number of channels
jmax {jmax} number of backgrounds
kmax {kmax} number of nuisance parameters
------------

shapes * * {path} $CHANNEL/$PROCESS-nominal $CHANNEL/$PROCESS-$SYSTEMATIC
------------

{bins}
------------

{processes}
------------

{systematics}

{groups}
'''

ABS_PATH_LXPLUS = '/afs/cern.ch/work/a/amecca/Analysis/combine10p5_el9/CMSSW_14_1_0_pre4/src/ZZdatacards/input'



def main(args):
    logging.info('writing card for %(year)s', vars(args))

    if(args.path is None):
        # This is a temporary hack until I understand why combineCards.py mishandles relative paths
        args.path = os.path.join(ABS_PATH_LXPLUS, args.localpath)

    # Same config passed to prepareHistoCombine.py
    with open(args.config_file) as f:
        config = json.load(f)

    region = config['region']

    # Paths
    # - the 1st is what is written in the datacard
    # - the 2nd is used to get the yield to be written in the datacard
    path_to_histograms = os.path.join(args.path, str(args.year)+'.root')
    path_to_histograms_local = os.path.join(args.localpath, str(args.year)+'.root')

    ### Bin section ###
    bin_name = getBinName(region, config['observable']['name'])
    observables=[[
        bin_name,
        config['observable']['observation']
    ]]
    df_bin = pd.DataFrame(observables, columns=['bin', 'observation']).transpose()

    if(logging.getLogger().isEnabledFor(logging.DEBUG)):
        print(df_bin.to_string(header=False))
        print()

    # Sample info
    data_info, MC_infos = get_samples_info(region=region)
    data_info.name = 'data_obs'
    all_infos = MC_infos + [data_info] if(args.unblind) else MC_infos

    # Test that all the processes have at least one event - otherwise Combine will crash later
    existing_processes = check_existing_histograms(path_to_histograms_local, observables[0][0], all_infos)
    config_processes = {}
    config.setdefault('processes', {})
    for proc_name, proc_yield in existing_processes.items():
        proc_yield_config = config['processes'].get(proc_name, -1)
        # Yield: prefer what is specified in the config, resort to the integral in the (local) rootfile
        y = existing_processes[proc_name] if proc_yield_config < 0 else proc_yield_config
        config_processes[proc_name] = y
    config['processes'] = config_processes

    ### Observable section ###
    signals     = [proc for proc in config['processes'] if proc in config['signals']    ]
    backgrounds = [proc for proc in config['processes'] if proc not in config['signals']]

    logging.info('signals:     %s', signals    )
    logging.info('backgrounds: %s', backgrounds)
    logging.info('observables: %s', observables)

    # dict: str -> int (process name -> process index)
    minProc = 1 - len(signals)
    samples_to_idx      = {s:minProc+i for i,s in enumerate(signals)    }
    samples_to_idx.update({b:i+1       for i,b in enumerate(backgrounds)})

    logging.info('samples_to_idx: %s', samples_to_idx)

    # Use a Pnadas dataframe to forma the process section of the card
    df_rate = pd.DataFrame(
        [[bin_name, k, samples_to_idx[k], v] for k,v in config['processes'].items()],
        columns=['bin', 'process', 'process_number', 'rate']
    ).transpose()
    df_rate.sort_values('process_number', axis=1, inplace=True)
    df_rate.rename(index={'process_number':'process'}, inplace=True)

    if(logging.getLogger().isEnabledFor(logging.DEBUG)):
        print(df_rate.to_string(header=False))
        print()


    ##### SYSTEMATICS #####
    ### Read systematics ###
    sysFile = os.path.join(args.syst_dir,'{year}.json'.format(year=args.year))
    systematics = SystDB(sysFile)

    ### Process systematics ###
    # MEMO: setdefault(region, {}).setdefault(var, {}).setdefault(sample, {})[syst] = {'up':upVar, 'dn':dnVar}
    db_bin = os.path.join(region, bin_name)
    syst_db_bin = systematics.get_samples_systs(region='4P', var=db_bin)

    # start debug
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        for proc_name, proc_systs in syst_db_bin.items():
            for syst_name, syst_data in proc_systs.items():
                logging.debug('%s - %s: %+.3f %+.3f', proc_name, syst_name, syst_data['up'], syst_data['dn'])
    # end debug

    # Order the systematics so that the samples have the same order of the observable section
    missing_systematics = False
    data_syst = {}
    for sample in samples_to_idx:
        systs_sample = syst_db_bin[sample]

        # Zero theoretical uncertainty on signal cross section, since we are measuring it
        if(sample in config['signals']):
            for syst, val in systs_sample.items():
                if(syst in config['systematics']['skip-if-signal']):
                    val['dn'] = val['up'] = 0
                    logging.debug('Zeroed systematic "%s" for signal "%s"', syst, sample)

        # Remove some systematics on data-driven backgrounds
        if(sample in config.get('data-driven', [])):
            for syst, val in systs_sample.items():
                # Only some systematics have to be removed (e.g. efficiencies)
                # In particulare we want to keep uncertainties on fake rates
                if('_eff_' in syst):
                    val['dn'] = val['up'] = 0
                    logging.debug('Zeroed systematic "%s" for data-driven "%s"', syst, sample)

        data_syst[sample] = systs_sample

    # Set normalization uncertainty (e.g. fake_leptons and fake_photons)
    for sample, val in config['systematics'].get('norm_uncertainty', {}).items():
        if sample in data_syst:
            logging.info('setting norm uncertainty on %s (%s)', sample, val)
            data_syst[sample]['CMS_SMP26XXX_'+sample+'_norm'] = val
            if  (sample == 'fake_leptons'):
                logging.info('Using norm uncertainty instead of lepton fake rate uncertainty')
                data_syst[sample]['CMS_fake_e'] = {'up':0, 'dn':0}
                data_syst[sample]['CMS_fake_m'] = {'up':0, 'dn':0}
        else:
            logging.warning('Norm uncertainty specified for "%s" in config, but the sample was not included or no histogram was found for bin "%s"', sample, bin_name)

    # Set normalization for groups of samples
    for group_name, group_info in config['systematics'].get('norm_group_uncertainty', {}).items():
        logging.info('setting group norm uncertainty on %s (%s)', group_name, group_info['value'])
        for sample in group_info['samples']:
            data_syst[sample]['CMS_'+group_name+'_norm'] = group_info['value']

    # Set manually the uncertainty on certain systematics for some samples
    for syst, syst_manual in config['systematics'].get('set_manual', {}).items():

        for sample, values in syst_manual.items():
            if(data_syst.get(sample)):
                logging.debug('overriding "%s" for "%s" to %s', syst, sample, values)
                data_syst[sample][syst] = values
            else:
                logging.debug('cannot override "%s" for "%s", since the sample has no yield in this bin (or it was removed)', syst, sample)

    # Fix for alpha_s
    # alpha_s appears to be have both variations >1 for some samples and both <1 for others
    for sample, sample_data in data_syst.items():
        alphas = sample_data.get('alphas')  # This is a reference
        if(alphas is None):
            continue # skip if it's missing for this sample
        up, dn = alphas['up'], alphas['dn']
        if(up * dn > 0):
            alphas['dn'] *= -1 # Modify the original data_systs dict
            logging.warning('changed the direction of alphas_Down for %s in %s -> up/dn = %.3f/%.3f', sample, bin_name, up, alphas['dn'])

    ### Decide the name of the systematics to be written in the datacard
    # these change between correlated and uncorrelated samples, and keep into
    # account cases like QCDscale and pdf in which samples are divided in groups
    out_to_orig_syst = {} # needed for the reverse lookup later
    syst_helpers_cache = SystHelperCache(config['systematics'])
    for sample, systs_sample in data_syst.items():
        systs_list = list(systs_sample.keys())
        for syst_name in systs_list:
            syst_helper = syst_helpers_cache.get_or_make(syst_name)
            out_name = syst_helper.outname(sample=sample, year=args.year)
            out_to_orig_syst[out_name] = syst_name
            if(out_name != syst_name):
                logging.debug('renaming (sample: "%s"): "%s" -> "%s"', sample, syst_name, out_name)
                systs_sample[out_name] = systs_sample.pop(syst_name)

    # Fill the dataframe using the dictionary
    df_syst = fillDataFrame(data_syst, formatter=format_lnN, fmt='%f').fillna(0)
    type_column = []
    for syst in df_syst.index:
        # Drop systematics that do not affect any sample
        if(all(df_syst.loc[syst, column] in ('-', 0, '0') for column in df_syst.columns)):
            logging.info('dropping systematic "%s"', syst)
            df_syst.drop(syst, inplace=True)
            continue

        # Decide systematic type and append it to column
        syst_helper = syst_helpers_cache.get_or_make(out_to_orig_syst[syst])
        syst_type = syst_helper.type_
        syst_type_name = None
        if(syst_type == 'gmN'):
            sample_affected, N, alpha = get_gmN_params(syst, data_syst)
            if(N > 0):
                df_syst.loc[syst, sample_affected] = alpha
                syst_type_name = 'gmN %d' %(N)
            else:
                syst_type_name = 'lnN'
        elif(syst_type == 'shape'):
            for sample in get_shape_affected(syst, data_syst):
                df_syst.loc[syst, sample] = 1 # signature: df.loc[row_indexer, column]
            syst_type_name = 'shape'
        else:
            syst_type_name = syst_type
        logging.debug('syst: %s -> syst_type: %s -> syst_type_name: %s', syst, syst_type, syst_type_name)
        type_column.append(syst_type_name)

    # Additional systematics
    for syst, process in config['systematics'].get('ADD_gmN', {}).items():
        logging.debug('additional syst: %s -> %s', syst, process)
        try:
            N, alpha = get_gmN_params_local(path_to_histograms_local, observables[0][0], process)
        except KeyError as e:
            logging.error("%s --> skipping this gmN in datacard", e)
            continue

        if(N > 0):
            new_row = [ alpha if p == process else '-' for p in df_syst.columns ]
            df_syst.loc[syst] = new_row
            type_column.append('gmN %d' %(N))
        else:
            logging.error('N=%d for gmN syst %s', N, syst)
            return 1

    ### Luminosity ###
    year = args.year
    year_int = int(year[:4])
    if(2016 <= year_int <= 2018):
        # Run 2
        if args.year in ('2016preVFP', '2016postVFP'): year = '2016'
        lumi_uncorrelated = lumi_unc_dict[year]['error_uncorrelated']
        lumi_correlated   = lumi_unc_dict[year]['error_correlated']
        lumi_1718         = lumi_unc_dict[year]['error_1718']

        lumi_name_uncorr = 'lumi_%s'%(year)
        lumi_name_correl = 'lumi_13TeV_correlated'
        for n in [lumi_name_uncorr, lumi_name_correl]:
            out_to_orig_syst[n] = 'lumi'

        df_syst.loc[lumi_name_uncorr] = pd.Series({ sample: (lumi_uncorrelated if sample not in config['data-driven'] else 0) for sample in df_syst.columns })
        type_column.append('lnN')

        df_syst.loc[lumi_name_correl] = pd.Series({ sample: (lumi_correlated   if sample not in config['data-driven'] else 0) for sample in df_syst.columns })
        type_column.append('lnN')

        if(args.year in ('2017', '2018')):
            lumi_name_1718 = 'lumi_13TeV_1718'
            out_to_orig_syst[lumi_name_1718] = 'lumi'
            df_syst.loc[lumi_name_1718] = pd.Series({ sample: (lumi_1718       if sample not in config['data-driven'] else 0) for sample in df_syst.columns })
            type_column.append('lnN')

    elif(year_int <= 2026):
        # Run 3
        for lumi_name, lumi_unc_data in lumi_unc_dict['2022&2023&2024'].items():
            lumi_unc = lumi_unc_data.get(str(year_int))
            if(lumi_unc is None):
                continue
            out_to_orig_syst[lumi_name] = 'lumi'
            lumi_row = pd.Series({sample: (lumi_unc if sample not in config['data-driven'] else 0) for sample in df_syst.columns})
            df_syst.loc[lumi_name] = lumi_row
            type_column.append('lnN')

    ### Add the column with the type of the systematics to the DataFrame
    df_syst.insert(0, 'type', type_column, False)

    ### Syst extra ###
    syst_extra_s = '* autoMCStats %d'%(config['systematics']['autoMCStats_threshold'])

    ### Groups of nusiances ###
    groups = {}
    for syst_fullname in df_syst.index:
        syst = out_to_orig_syst[syst_fullname]
        for group_name, group_systs in config['systematics']['groups'].items():
            if(any(s in syst for s in group_systs)):
                logging.debug('syst: %s -> group: %s', syst, group)
                break
        else: # no match in the groups
            if(syst == 'lumi'):
                group_name = 'lumi'
            else:
                continue # break out of the loop on the systematics
        groups.setdefault(group_name, []).append(syst_fullname)

    groups_s = '\n'.join( ['%s group = %s'%(k, ' '.join(v)) for k,v in groups.items()] )


    ### Open template ###
    # if(args.template is not None):
    #     with open(args.template) as ftemplate:
    #         template = ftemplate.read()
    # else:
    template = __builtin_template__

    # template = template.format(
    card_str = PartialFormatter().format(template,
        imax=1,
        jmax=len(signals)+len(backgrounds)-1,
        kmax=len(df_syst),
        path=path_to_histograms,
        bins=df_bin.to_string(header=False),
        processes=df_rate.to_string(header=False),
        systematics='#'+df_syst.to_string()+'\n\n'+syst_extra_s,
        groups=groups_s
    )

    ### Write card ###
    card_basename = args.config_file.split('/')[-1].split('.')[0]
    cardname = os.path.join(args.output,
                            '{}/{}.txt'.format(
                                card_basename,
                                args.year,
                            ))
    card_dir = os.path.dirname(cardname)
    os.makedirs(card_dir, exist_ok=True)

    with open(cardname, 'w') as fout:
        if(missing_systematics): fout.write('### WARNING systematics missing for one or more samples ###\n\n')
        fout.write(card_str)
        logging.info('config written to "%s"', fout.name)

    if(missing_systematics):
        return 2
    return 0


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('config_file', help='Configuration file')
    # parser.add_argument('-t', '--template', help='Alternative template for the datacard')
    parser.add_argument('-o', '--output' , default='cards', help='Directory where the cards will be written')
    parser.add_argument('-y', '--year'   , required=True, choices=lumi_dict.keys())
    parser.add_argument('-i', '--input'  , default='histogramsForCombine', dest='localpath', help='Path to the histograms for local checks (default: %(default)s)')
    parser.add_argument(      '--path'   , default=None                                    , help='Path to the histograms (default: hardcoded + localpath)')
    parser.add_argument(      '--syst-dir', default='../data/systematics')
    parser.add_argument(      '--unblind', action='store_true', help='Read data_obs from input files')
    parser.add_argument('--log', dest='loglevel', metavar='LEVEL', default='WARNING', help='Level for the python logging module. Can be either a mnemonic string like DEBUG, INFO or WARNING or an integer (lower means more verbose).')

    return parser.parse_args()


# Utility functions
def getSystType(syst, config):
    if  (syst in config['systematics'].get('shape', [])):
        return 'shape'
    elif(syst in config['systematics'].get('gmN'  , [])):
        return 'gmN'
    else:
        return 'lnN'

def format_lnN(value, fmt='%f'):
    # up = 1 - yield_up/yield --> k_up = 1 + up
    up = value['up']
    dn = value['dn']
    if   any(isnan(v)      for v in [up, dn]):
        return '-'
    if   all(abs(v) < 1e-4 for v in [up, dn]):
        # print('WARN: negligible syst:', value)
        return '-'
    if   any(abs(v) > 1    for v in [up, dn]):
        logging.warning('very large syst: %s', value)
        return '-'
    else:
        if(up*dn > 0):
            dn = -dn # fix for cases where weights are applied in the opposite direction
        symmetric = abs(up-dn)/2
        asymmetry = abs(up+dn)/2  # In case of symmetric effect up and dn have opposite sign
        if  (symmetric == 0):
            return '-'
        elif( asymmetry > LNN_ASYMM_THR ):
            return (fmt+'/'+fmt) %(1+dn, 1+up)
        else:
            return fmt %(1 + symmetric)


def getBinName(region, observable):
    return observable  # region+'_'+observable


# Formatter class that ignores missing arguments
try:
    # Python 3
    from _string import formatter_field_name_split
except ImportError:
    formatter_field_name_split = str._formatter_field_name_split

class PartialFormatter(string.Formatter):
    def get_field(self, field_name, args, kwargs):
        try:
            val = super(PartialFormatter, self).get_field(field_name, args, kwargs)
        except (IndexError, KeyError, AttributeError):
            first, _ = formatter_field_name_split(field_name)
            val = '{' + field_name + '}', first
        return val


def check_existing_histograms(fname, observable, infos):
    '''
    Filters the list of names of the SampleInfo and returns only those that
    actually have an histogram in the files for the observable, along with their
    integral, to be written in the datacard
    '''
    logging.debug('fname     : %s', fname)
    logging.debug('observable: %s', observable)
    existing_processes = {}

    with TFileContext(fname) as tf:
        obs_folder = tf.Get(observable)
        if(not obs_folder):
            raise KeyError('Observable "%s" missing from file "%s"' %(observable, fname))
        # logging.debug('obs_folder: %s', obs_folder)
        keys = obs_folder.GetListOfKeys()
        # logging.debug('keys: %s', '\n\t'+'\n\t'.join(sorted([k.GetName() for k in keys if not 'CMS' in k.GetName()])))
        for info in infos:
            process = info.name
            hname = process+'-nominal'
            if  (not keys.Contains(hname)):
                logging.warning('dropping %s, since it is missing for observable "%s" in %s', process, observable, fname)
            else:
                h = obs_folder.Get(hname)
                integral = h.Integral(1, h.GetNbinsX())
                if(integral <= 0):
                    logging.warning('dropping %s, since it has norm %.3g for observable "%s" in %s', process, integral, observable, fname)
                else:
                    existing_processes[process] = integral
    logging.debug('existing_p: %s', existing_processes )
    return existing_processes


def get_gmN_params(syst, data_syst):
    logging.debug('syst: %s', syst)
    n_affected = 0
    sample_affected = None
    N = 0
    alpha = 0
    for sample, sample_data in data_syst.items():
        syst_data = sample_data[syst]
        if(syst_data['up'] - syst_data['dn'] > 0):
            n_affected += 1
            sample_affected = sample
            N      = syst_data['N']
            integr = syst_data['integr']
            alpha  = integr/N
            logging.debug('sample: %s - N: %d - integr: %g - alpha: %g', sample, N, integr, alpha)

    if  (n_affected >  1):
        raise RuntimeError('The number of samples affected by "%s" is %d, but the specified type is gmN!' %(syst, n_affected))
    elif(n_affected == 0):
        logging.warning('No sample is affected by "%s", but the specified type is "gmN"' %(syst))

    return sample_affected, N, alpha


def get_gmN_params_local(fname, observable, process):
    '''
    Retrieve the gmN parameters N and alpha from the local rootfile (which has an histogramsForCombine layout)
    Parameters:
    :param fname: path to file with histograms
    :param observable: name TDirectory in the file
    :param process: name of the process within the TDirectory
    '''
    with TFileContext(fname) as tf:
        h = tf.Get(observable).Get(process)
        if(not h): raise KeyError('observable "%s", process "%s" in file "%s"' %(observable, process, fname))
        N      = h.GetEntries()
        integr = h.Integral(1, h.GetNbinsX())
        alpha  = integr/N
        logging.debug('process: %s - N: %d - integr: %g - alpha: %g', process, N, integr, alpha)
    return N, alpha


def get_shape_affected(syst, data_syst):
    samples_affected = []
    for sample, sample_data in data_syst.items():
        syst_data = sample_data.get(syst, {'up':0, 'dn':0})
        if(syst_data['up'] - syst_data['dn'] != 0.):
            samples_affected.append(sample)

    if(len(samples_affected) == 0):
        logging.warning('No sample is affected by "%s", but the specified type is "shape"' %(syst))

    logging.debug('syst: %-12s - affected(%d): %s', syst, len(samples_affected), samples_affected)
    return samples_affected


if __name__ == '__main__':
    args = parse_args()
    loglevel = args.loglevel.upper() if not args.loglevel.isdigit() else int(args.loglevel)
    logging.basicConfig(format='%(levelname)s:%(module)s:%(funcName)s: %(message)s', level=loglevel)

    exit(main(args))
