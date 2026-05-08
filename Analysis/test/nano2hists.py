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
import math
import re

import ROOT

from ZZAnalysis.NanoAnalysis.tools import setConf

from ZZVBS_analysis.Analysis.utils import TFileContext, mkhist, FinalState \
    , lumi_dict, write_resultmap
from ZZVBS_analysis.Analysis.libutils import find_load_lib


VariationsFor = ROOT.RDF.Experimental.VariationsFor

class RResultMapEmulator(dict):
    def GetKeys(self): return self.keys()


def main(args):
    logging.debug('args: %s', args)

    if(args.multithread):
        ROOT.EnableImplicitMT()

    # Get the Events tree
    df = ROOT.RDataFrame(
        'Events'
        # 'ZZTree/candTree'
        , args.fnames_in)

    if(args.list_columns):
        print(df.Describe())
        return 0

    # Load shared libraries
    ROOT.gInterpreter.AddIncludePath('../interface')
    find_load_lib('cConstants')
    find_load_lib('helpers')

    # Are we running on MC or data? Compute the weights
    if(args.is_MC):
        df_runs = ROOT.RDataFrame('Runs', args.fnames_in)
        genEventSumw = df_runs.Sum('genEventSumw').GetValue()
        logging.info('genEventSumw: %g', genEventSumw)
        lumi = lumi_dict[args.year]['value']
        df = df.Define('weight', '(double) overallEventWeight * ZZCand_dataMCWeight[bestCandIdx] * %f' %(lumi/genEventSumw))
    else:
        df = df.Define('weight', '(double)1.')
    df = df.Define('weight2', 'weight*weight')

    # Run the analysis
    t_start = time()
    histograms, counters = analyze(df, args)
    hmaps = []
    re_skip_syst = re.compile('Z[12]l[12]_')
    for hist in histograms:
        hname = hist.GetName()
        # skip variations for some histograms
        if(re_skip_syst.search(hname)):
            logging.debug('skipping systs for "%s"', hname)
            hmap = RResultMapEmulator(nominal=hist)
        else:
            hmap = VariationsFor(hist)
        hmaps.append(hmap)

    # Read the manual cut reports (for weighted events) and fill an histogram
    counters_read = {n: [v[0].GetValue(), math.sqrt(v[1].GetValue())] for n,v in counters.items()}
    h_cuts = ROOT.TH1F('AAA_cutflow', 'cutflow;cut;Events', len(counters_read),0,1)
    for i, (name, value) in enumerate(counters_read.items()):
        logging.info('cut %-30.30s: %.3g +- %.3g events' %(name, *value))
        h_cuts.GetXaxis().SetBinLabel(i+1, name)
        h_cuts.SetBinContent(i+1, value[0])
        h_cuts.SetBinError  (i+1, value[0])

    t_end = time()
    logging.info('Time elapsed: %.3g s', t_end-t_start)

    # Write histograms
    with TFileContext(args.fname_out, 'RECREATE') as tf_out:
        h_cuts.Write()
        for hmap in hmaps:
            write_resultmap(hmap)
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
    parser.add_argument('fnames_in', nargs='+', metavar='FILE', help='Input: (post-processed) NanoAOD files')
    parser.add_argument('-o', '--output', default=None, dest='fname_out', metavar='FILE', help='Default: %(default)s')
    parser.add_argument('-y', '--year'  , required=True, metavar='YEAR', help='Needed to get the correct luminosity')
    parser.add_argument(      '--list', dest='list_columns', action='store_true', help='List the columns present in the input file and exit')
    parser.add_argument('-n', '--max-entries', type=int, default=0, metavar='N', help='Process a maximum of N entries (disables multithreading)')
    # parser.add_argument(      '--mt'   , dest='multithread', action='store_true' , help='Enable ROOT implicit multithread (default)', default=True)
    parser.add_argument(      '--no-mt', dest='multithread', action='store_false', help='Disable ROOT implicit multithread (output entries will not be ordered)')

    # Data/MC? -> 12. In the face of ambiguity, refuse the temptation to guess.
    pgisMC = parser.add_mutually_exclusive_group(required=True)
    pgisMC.add_argument(      '--data', dest='is_MC', action='store_false', help='Set the event weights to 1')
    pgisMC.add_argument(      '--MC'  , dest='is_MC', action='store_true' , help='Compute the event weights')

    parser.add_argument('--log', dest='loglevel', metavar='LEVEL', default='WARNING', help='Level for the python logging module. Can be either a mnemonic string like DEBUG, INFO or WARNING or an integer (lower means more verbose).')
    args = parser.parse_args()

    if(args.max_entries > 0):
        args.multithread = False
    if(args.fname_out is None):
        split = os.path.splitext(args.fnames_in[0])
        args.fname_out = split[0]+'_hists' + split[1]

    return args


def analyze(df, args):
    year_int = int(args.year[:4])
    tot_entries = df.Count().GetValue()
    logging.info(    'Total entries   : %d', tot_entries)

    if(args.max_entries > 0):
        max_entries = min(args.max_entries, tot_entries)
        df = df.Range(0, max_entries)
        logging.info('Filtered entries: %d', max_entries)

    futures = [] # <ROOT.RDF.RResultPtr>
    counters = {'all': [df.Sum('weight'), df.Sum('weight2')]}

    ### Pre-selection for SR4P
    df = df.Filter(*['nZZCand > 0']*2)
    counters['has ZZ'] = [df.Sum('weight'), df.Sum('weight2')]

    ### Systematics, called before definitions ###
    if(args.is_MC):
        df = df.Vary('weight', 'ROOT::RVecD{weight*puWeightDn/puWeight, weight*puWeightUp/puWeight}', ['Dn', 'Up'], 'CMS_pileup')

        # # JES, JER
        for var in ('pt', 'mass'):
            df = df.Vary('Jet_%s'%(var), 'ROOT::VecOps::RVec<ROOT::RVecF>{Jet_scaleDn_%s, Jet_scaleUp_%s}'%(var,var), ['Dn', 'Up'], 'CMS_scale_j')
            df = df.Vary('Jet_%s'%(var), 'ROOT::VecOps::RVec<ROOT::RVecF>{Jet_smearDn_%s, Jet_smearUp_%s}'%(var,var), ['Dn', 'Up'], 'CMS_res_j')

        # Lepton pt scale and resolution
        for var in ('scaleDn_pt', 'scaleUp_pt', 'smearDn_pt', 'smearUp_pt'):
            df = df.Define('Lepton_%s'%(var), 'ROOT::VecOps::Concatenate(Electron_%s, Muon_%s)'%(var, var))

        for flav in ('Electron', 'Muon', 'Lepton'):
            initial = flav.lower()[0]
            df = df.Vary('%s_pt'%(flav), 'ROOT::VecOps::RVec<ROOT::RVecF>{%s_scaleDn_pt, %s_scaleUp_pt}'%(flav,flav), ['Dn', 'Up'], 'CMS_scale_%s'%(initial))
            df = df.Vary('%s_pt'%(flav), 'ROOT::VecOps::RVec<ROOT::RVecF>{%s_smearDn_pt, %s_smearUp_pt}'%(flav,flav), ['Dn', 'Up'], 'CMS_res_%s'  %(initial))

    ### Aliases and definitions
    df = df.Define('ZZ_mass', 'ZZCand_mass[bestCandIdx]')
    df = df.Define('ZZ_KD'  , 'ZZCand_KD[bestCandIdx]')
    df = df.Define('Z1_mass', 'ZZCand_Z1mass[bestCandIdx]')
    df = df.Define('Z2_mass', 'ZZCand_Z2mass[bestCandIdx]')

    df = df.Define('JetClean_idx', 'idx_equal(Jet_ZZMask, 0)')
    df = df.Define('nJetClean', 'JetClean_idx.size()')
    for var in ('pt', 'eta', 'phi', 'mass'):
        df = df.Define('JetClean_%s'%(var), 'fill_with_indexes(Jet_%s, JetClean_idx)'%(var))
    df = df.Define('JetGood_idx' , 'jetPtCut(%d, JetClean_pt, JetClean_eta)'%(year_int)) # indexes into JetClean
    df = df.Define('nJetGood'    , 'JetGood_idx.size()');
    for var in ('pt', 'eta', 'phi', 'mass'):
        df = df.Define('JetGood_%s'%(var), 'fill_with_indexes(JetClean_%s, JetGood_idx)'%(var))
        for i in (0,1):
            df = df.Define('j%d_%s' %(i+1, var), 'JetGood_%s[%d]' %(var, i))

    df = df.Define('absdetajj', 'fabs(j1_eta-j2_eta)')

    # Final State, Lepton Flavour Order (ie 2e2mu != 2mu2e)
    df = df.Define('Z1flav', 'ZZCand_Z1flav[bestCandIdx]')
    df = df.Define('Z2flav', 'ZZCand_Z2flav[bestCandIdx]')
    df = df.Define('FSLFO', 'get_FSLFO(Z1flav, Z2flav)')
    for Zxlx in ('Z1l1', 'Z1l2', 'Z2l1', 'Z2l2'):
        df = df.Define(Zxlx+'_idx', 'ZZCand_%sIdx[bestCandIdx]' %(Zxlx))
        df = df.Define(Zxlx+'_pt' , 'Lepton_pt[%s_idx]'  %(Zxlx))
        df = df.Define(Zxlx+'_eta', 'Lepton_eta[%s_idx]' %(Zxlx))
        df = df.Define(Zxlx+'_phi', 'Lepton_phi[%s_idx]' %(Zxlx))
        df = df.Define(Zxlx+'_phinorm', Zxlx+'_phi/%f' %(math.pi))

    df = df.Define('ZZ_Lepton_idx', 'ROOT::RVecI {'+
                   ','.join([ '%s_idx' %(Zxlx) for Zxlx in ('Z1l1', 'Z1l2', 'Z2l1', 'Z2l2')])
                   +'}')
    df = df.Define('ZZ_Lepton_pt', 'fill_with_indexes(Lepton_pt, ZZ_Lepton_idx)')

    df = df.Define('Lepton_absPdgId', 'return Map(Lepton_pdgId, [](int id){ return abs(id); })')
    df = df.Define('ZZ_Muon_idx', 'idx_subvec_equal(Lepton_absPdgId, ZZ_Lepton_idx, 13)')
    df = df.Define('ZZ_Muon_pt', 'fill_with_indexes(Lepton_pt, ZZ_Muon_idx)')
    df = df.Define('ZZ_Muon_eta', 'fill_with_indexes(Lepton_eta, ZZ_Muon_idx)')
    df = df.Define('ZZ_leadingMu_pt', 'ZZ_Muon_pt.size() > 0 ? ZZ_Muon_pt[0] : -1.')
    df = df.Define('ZZ_subleadMu_pt', 'ZZ_Muon_pt.size() > 1 ? ZZ_Muon_pt[1] : -1.')
    df = df.Define('ZZ_leadingMu_eta', 'ZZ_Muon_eta.size() > 0 ? ZZ_Muon_eta[0] : -100.')
    df = df.Define('ZZ_subleadMu_eta', 'ZZ_Muon_eta.size() > 1 ? ZZ_Muon_eta[1] : -100.')
    df = df.Define('ZZ_Muon_idxMuon' , 'ZZ_Muon_idx - nElectron')
    df = df.Define('ZZ_Muon_mvaLowPt', 'fill_with_indexes(Muon_mvaLowPt, ZZ_Muon_idxMuon)')
    df = df.Define('ZZ_Muon_minmvaLowPt', 'ZZ_Muon_mvaLowPt.size() > 0? *std::min_element(ZZ_Muon_mvaLowPt.begin(), ZZ_Muon_mvaLowPt.end()) : 1.')

    # mjj
    kinj1 = ['j1_%s' %(var) for var in ('pt', 'eta', 'phi', 'mass')]
    kinj2 = ['j2_%s' %(var) for var in ('pt', 'eta', 'phi', 'mass')]
    df = df.Define('mj1j2' , 'sum_M_mass(' + ', '.join(kinj1 + kinj2) + ')')

    # MELA probabilities (automatic from the branch names)
    branches = [str(b) for b in df.GetColumnNames()]
    branches_prob = [b for b in branches if b.startswith('ZZCand_P_')]
    probs = [p[len('ZZCand_P_'):] for p in branches_prob]
    logging.debug('MELA probs (%d): %s', len(probs), probs)

    # MELA probabilities and ratio
    if(all(p in probs for p in ('JJVBF_BKG_MCFM_JECNominal', 'JJQCD_BKG_MCFM_JECNominal'))):
        df = df.Define('P_EWK', 'ZZCand_P_{0}[bestCandIdx]'.format('JJVBF_BKG_MCFM_JECNominal'))
        df = df.Define('P_QCD', 'ZZCand_P_{0}[bestCandIdx]'.format('JJQCD_BKG_MCFM_JECNominal'))
        for prob in ('P_EWK', 'P_QCD'):
            df = df.Define(prob+'_log', 'log(%s)'%(prob))
        df = df.Define('ratio_EW_EWpQCD', 'P_EWK/(P_EWK+P_QCD)')
    else:
        df = df.Define('P_EWK', '0').Define('P_QCD', '0')

    ### Inclusive histograms
    # futures.append(mkhist(df, 'incl_nJets', ';# jets', 10,-0.5,9.5, v='nCleanedJetsPt30'))

    ### Selection
    df = df.Filter(*['nJetGood >= 2']*2)
    counters['>= 2 good jets'] = [df.Sum('weight'), df.Sum('weight2')]
    df = df.Filter(*['mj1j2 > 120']*2)

    ### Histograms
    futures.append(mkhist(df, 'weight', ';weight', 50,-5.,5.))
    counters['[inclusive] mjj > 120 GeV'] = [df.Sum('weight'), df.Sum('weight2')]
    futures.extend( define_histograms(df         , prefix='') )

    df_VBSincl  = df         .Filter(*['ZZ_mass > 180']*2)
    counters['[VBSincl] ZZ_mass > 180 GeV'] = [df.Sum('weight'), df.Sum('weight2')]
    futures.extend( define_histograms(df_VBSincl , prefix='VBSincl/') )

    df_mjj400   = df_VBSincl .Filter(*['mj1j2 > 400']*2)
    counters['mjj > 400 GeV'] = [df.Sum('weight'), df.Sum('weight2')]
    # futures.extend( define_histograms(df_mjj400  , prefix='mZZ180-mjj400/') )

    df_VBSloose = df_mjj400  .Filter(*['absdetajj > 2.4']*2)
    counters['[VBSloose] |deta_jj| > 2.4'] = [df.Sum('weight'), df.Sum('weight2')]
    futures.extend( define_histograms(df_VBSloose, prefix='VBSloose/') )

    df_VBStight = df_VBSloose.Filter(*['mj1j2 > 1000']*2)
    counters['[VBStight] mjj > 1000 GeV'] = [df.Sum('weight'), df.Sum('weight2')]
    futures.extend( define_histograms(df_VBStight, prefix='VBStight/') )

    for Zxlx in ('Z1l1', 'Z1l2', 'Z2l1', 'Z2l2'):
        futures.append(mkhist(df, '%s_pt' %(Zxlx),    ';%s p_{T} [GeV]'%(Zxlx), 60,0.,600., v='%s_pt'     %(Zxlx)))
        futures.append(mkhist(df, '%s_eta'%(Zxlx),    ';%s #eta'       %(Zxlx), 50,-2.5,2.5,v='%s_eta'    %(Zxlx)))
        futures.append(mkhist(df, '%s_phinorm'%(Zxlx),';%s #phi/#pi'   %(Zxlx), 50,-1.,1. , v='%s_phinorm'%(Zxlx)))

    # Histograms by channel
    for fs in FinalState:
        if fs == FinalState.fs4l: continue
        df_ch = df.Filter('FSLFO==%d' %(fs.value))
        fsname = fs.name.replace('fs','')
        fstitle= fsname.replace('mu','#mu').strip()
        futures.append(mkhist(df_ch, 'ZZ_mass_%s'%(fsname), ';m_{ZZ} [GeV], %s'%(fstitle), 60,0,600, v='ZZ_mass')) #1200
        # for Zxlx in ('Z1l1', 'Z1l2', 'Z2l1', 'Z2l2'):
        #     futures.append(mkhist(df_ch, '%s_pt_%s' %(Zxlx, fsname), ';%s p_{T} [GeV], %s'%(Zxlx, fstitle), 60,0,600, v='%s_pt'     %(Zxlx)))
        #     futures.append(mkhist(df_ch, '%s_eta_%s'%(Zxlx, fsname), ';%s #eta, %s'       %(Zxlx, fstitle), 60,-3,3., v='%s_eta'    %(Zxlx)))
        #     futures.append(mkhist(df_ch, '%s_phi_%s'%(Zxlx, fsname), ';%s #phi/#pi, %s'   %(Zxlx, fstitle), 50,-1,1., v='%s_phinorm'%(Zxlx)))

    zeroMELA = df.Filter("P_EWK == 0 && P_QCD == 0")
    n_zeroMELA = zeroMELA.Count()
    n_total = df.Count()

    logging.info("Finished setting up the analysis")

    # Calling GetValue() on a RResultPtr causes the event loop to run
    df.Report().GetValue().Print()
    logging.info('Events with MELA==0 / total: %d/%d', n_zeroMELA.GetValue(), n_total.GetValue())

    return futures, counters


def define_histograms(df, prefix=''):
    futures = []
    futures.append(mkhist(df, prefix+'ZZ_mass'  , ';m_{ZZ} [GeV]'      ,60,  0, 600, v='ZZ_mass'  )) #1200
    futures.append(mkhist(df, prefix+'ZZ_KD'    , ';KD'                ,50,  0,   1, v='ZZ_KD'    ))
    futures.append(mkhist(df, prefix+'Z1_mass'  , ';m_{Z1} [GeV]'      ,60, 60, 120, v='Z1_mass'  ))
    futures.append(mkhist(df, prefix+'Z2_mass'  , ';m_{Z2} [GeV]'      ,60, 60, 120, v='Z2_mass'  ))
    futures.append(mkhist(df, prefix+'absdetajj', ';|#Delta #eta_{jj}|',80,  0,   8, v='absdetajj'))
    futures.append(mkhist(df, prefix+'j1_pt'    , ';j1 p_{T} [GeV]'    ,60,  0, 600, v='j1_pt'    ))
    futures.append(mkhist(df, prefix+'j2_pt'    , ';j2 p_{T} [GeV]'    ,60,  0, 600, v='j2_pt'    ))
    futures.append(mkhist(df, prefix+'FSLFO'    , ';Final state'       , 4,  0,   4, v='FSLFO'    ))
    futures.append(mkhist(df, prefix+'mj1j2'    , ';m_{j1 j2}'         ,60,  0,1200, v='mj1j2'    ))
    futures.append(mkhist(df, prefix+'nJets'    , ';# jets (cleaned)'  ,10,-.5, 9.5, v='nCleanedJetsPt30'))
    futures.append(mkhist(df, prefix+'nJetGood' ,';# jets (re-cleaned)',10,-.5, 9.5, v='nJetGood'))
    for prob in ('EWK', 'QCD'):
        futures.append(mkhist(df, prefix+'MELA_'+prob+'_log', ';log(P(%s))'%(prob), 50,-50, 0, v='P_%s_log'%(prob)))
    futures.append(mkhist (df, prefix+'ratio_EW_EWpQCD', ';P_{EW}/(P_{EW}+P_{QCD})', 50, 0, 1, v='ratio_EW_EWpQCD'))

    futures.append(mkhist(df, prefix+'ZZ_leadingMu_pt'    , ';leading #mu p_{T} [GeV]', 60, 0. ,300., v='ZZ_leadingMu_pt'    ))
    futures.append(mkhist(df, prefix+'ZZ_subleadMu_pt'    , ';sublead #mu p_{T} [GeV]', 60, 0. ,300., v='ZZ_subleadMu_pt'    ))
    futures.append(mkhist(df, prefix+'ZZ_leadingMu_eta'   , ';leading #mu #eta'       , 48,-2.4, 2.4, v='ZZ_leadingMu_eta'   ))
    futures.append(mkhist(df, prefix+'ZZ_subleadMu_eta'   , ';sublead #mu #eta'       , 48,-2.4, 2.4, v='ZZ_subleadMu_eta'   ))
    futures.append(mkhist(df, prefix+'ZZ_Muon_minmvaLowPt', ';min(#mu MVA)'           , 40,-1. , 1. , v='ZZ_Muon_minmvaLowPt'))

    return futures


def fix_xlabels_FSLFO(h):
    xaxis = h.GetXaxis()
    xaxis.SetBinLabel(1, '4e')
    xaxis.SetBinLabel(2, '4#mu')
    xaxis.SetBinLabel(3, '2e#2#mu')
    xaxis.SetBinLabel(4, '2#mu2e')


if __name__ == '__main__':
    args = parse_args()
    loglevel = args.loglevel.upper() if not args.loglevel.isdigit() else int(args.loglevel)
    logging.basicConfig(format='%(levelname)s:%(module)s:%(funcName)s: %(message)s', level=loglevel)

    exit(main(args))
