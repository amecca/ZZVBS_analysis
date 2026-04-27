#!/bin/env python3

import os
import math
from argparse import ArgumentParser
import logging
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
from ZZVBS_analysis.Analysis.FakeRates import FakeRates
from ZZVBS_analysis.Analysis.utils import TFileContext, mkhist, FinalState


FRpath_template  = "/eos/user/p/psalvini/MARIO_TAMI/ZZVBS_Analysis/FakeRates/FakeRates_OS_{year}_NomuMva.root"


def main(args):
    FRpath = FRpath_template.format(year=args.year)
    ROOT.gInterpreter.Declare(f"""
#include "FakeRates.hpp"

FakeRates fr("{FRpath}", "OS");

double GetFR(float pt, float eta, int id) {{
    return fr.getFRval(pt, eta, id);
}}
""")

    for f in args.fnames_in:
        logging.debug(f)

    logging.info("Number of file(s): %d", len(args.fnames_in))

    histograms = []

    ROOT.EnableImplicitMT()

    # Get the Events tree
    df = ROOT.RDataFrame('Events', args.fnames_in)

    df = df.Define("Jet1Idx",  "JetLeadingIdx")
    df = df.Define("Jet2Idx",  "JetSubleadingIdx")
    df = df.Define("nJets", "nCleanedJetsPt30")

    df = df.Define(
        "mjj",
        """
        ROOT::Math::PtEtaPhiMVector j1(
            Jet_pt[Jet1Idx],
            Jet_eta[Jet1Idx],
            Jet_phi[Jet1Idx],
            Jet_mass[Jet1Idx]
        );
    
        ROOT::Math::PtEtaPhiMVector j2(
            Jet_pt[Jet2Idx],
            Jet_eta[Jet2Idx],
            Jet_phi[Jet2Idx],
            Jet_mass[Jet2Idx]
        );
    
        return (j1 + j2).M();
        """
    )

    df = df.Filter("mjj >= 120")
    df = df.Filter("nJets >= 2")

    #2P2F
    df_2P2F = df.Filter("ZLLbest2P2FIdx != -1")
    df_2P2F = df_2P2F.Define("theZLLIdx",    "ZLLbest2P2FIdx")
    df_2P2F = df_2P2F.Define("muon_mva", "Muon_mvaLowPt[theZLLIdx]")

    df_2P2F_mva = df_2P2F.Filter("muon_mva > -1")

    df_2P2F_mva = df_2P2F_mva.Define("m4l_2P2F",     "ZLLCand_mass[ZLLbest2P2FIdx]")

    df_2P2F_mva = df_2P2F_mva.Filter("m4l_2P2F > 180")
    df_2P2F_mva = df_2P2F_mva.Define("fakeLep1_Idx", "ZLLCand_Z2l1Idx[theZLLIdx]")
    df_2P2F_mva = df_2P2F_mva.Define("fakeLep2_Idx", "ZLLCand_Z2l2Idx[theZLLIdx]")

    #leptons
    df_2P2F_mva = df_2P2F_mva.Define("fakeLep1_pt",    "Lepton_pt[fakeLep1_Idx]")
    df_2P2F_mva = df_2P2F_mva.Define("fakeLep1_eta",   "Lepton_eta[fakeLep1_Idx]")
    df_2P2F_mva = df_2P2F_mva.Define("fakeLep1_pdgId", "Lepton_pdgId[fakeLep1_Idx]")

    df_2P2F_mva = df_2P2F_mva.Define("fakeLep2_pt",    "Lepton_pt[fakeLep2_Idx]")
    df_2P2F_mva = df_2P2F_mva.Define("fakeLep2_eta",   "Lepton_eta[fakeLep2_Idx]")
    df_2P2F_mva = df_2P2F_mva.Define("fakeLep2_pdgId", "Lepton_pdgId[fakeLep2_Idx]")
    #------------------------------------------------

    #fake rates
    df_2P2F_mva = df_2P2F_mva.Define(
        "fr1",
        "GetFR(fakeLep1_pt, fakeLep1_eta, fakeLep1_pdgId)"
    )

    df_2P2F_mva = df_2P2F_mva.Define(
        "fr2",
        "GetFR(fakeLep2_pt, fakeLep2_eta, fakeLep2_pdgId)"
    )
    #------------------------------------------------

    #weight
    df_2P2F_mva = df_2P2F_mva.Define(
        "tFactor_2P2F",
        "-(fr1/(1-fr1))*(fr2/(1-fr2))" 
    )
    #------------------------------------------------

    df_2P2F_mva = df_2P2F_mva.Define("weight",     "1.0")
    df_2P2F_mva = df_2P2F_mva.Define("idx_Z1l1",   "ZLLCand_Z2l1Idx[ZLLbest2P2FIdx]")
    df_2P2F_mva = df_2P2F_mva.Define("lep1_pt",    "Lepton_pt[idx_Z1l1]")
    df_2P2F_mva = df_2P2F_mva.Define("lep1_eta",   "Lepton_eta[idx_Z1l1]")
    df_2P2F_mva = df_2P2F_mva.Define("lep1_pdgId", "Lepton_pdgId[idx_Z1l1]")
    df_2P2F_mva = df_2P2F_mva.Define("mJets",      "mjj")

    histograms.append(mkhist(df_2P2F_mva, 'lep1_pt',    '; lep1 p_{T} [GeV]', 60,0.,600., v='lep1_pt'))
    histograms.append(mkhist(df_2P2F_mva, 'lep1_eta',   '; lep1 eta',         50,-2.5,2.5, v='lep1_eta'))
    histograms.append(mkhist(df_2P2F_mva, 'mJets',      '; mJets [GeV]',      60,0.,600., v='mJets'))
    histograms.append(mkhist(df_2P2F_mva, 'fr1',        '; fr1',              100, 0., 0.25, v='fr1'))
    histograms.append(mkhist(df_2P2F_mva, 'fr2',        '; fr2',              100, 0., 0.25, v='fr2'))

    # Z+X distribution 2P2F
    h_ZX_m4l_2P2F = df_2P2F_mva.Histo1D(
        ("ZX_m4l_2P2F", ";m_{4l} (GeV);Events", 45, 150., 600.),
        "m4l_2P2F",
        "tFactor_2P2F")
    #------------------------------------------------
    #end 2P2F
    #------------------------------------------------

    #3P1F
    df_3P1F = df.Filter("ZLLbest3P1FIdx != -1")
    df_3P1F = df_3P1F.Define("theZLLIdx", "ZLLbest3P1FIdx")

    df_3P1F = df_3P1F.Define("muon_mva", "Muon_mvaLowPt[theZLLIdx]")

    df_3P1F_mva = df_3P1F.Filter("muon_mva > -1")

    df_3P1F_mva = df_3P1F_mva.Define("m4l_3P1F",  "ZLLCand_mass[ZLLbest3P1FIdx]")
    df_3P1F_mva = df_3P1F_mva.Filter("m4l_3P1F > 180")

    #find the fake lep
    df_3P1F_mva = df_3P1F_mva.Define("l3_Idx",        "ZLLCand_Z2l1Idx[theZLLIdx]")
    df_3P1F_mva = df_3P1F_mva.Define("l4_Idx",        "ZLLCand_Z2l2Idx[theZLLIdx]")
    df_3P1F_mva = df_3P1F_mva.Define("fakeLep_Idx",   "Lepton_ZZFullSel[l3_Idx] ? l4_Idx : l3_Idx")

    #lepton
    df_3P1F_mva = df_3P1F_mva.Define("fakeLep_pt",    "Lepton_pt[fakeLep_Idx]")
    df_3P1F_mva = df_3P1F_mva.Define("fakeLep_eta",   "Lepton_eta[fakeLep_Idx]")
    df_3P1F_mva = df_3P1F_mva.Define("fakeLep_pdgId", "Lepton_pdgId[fakeLep_Idx]")

    #fake rate
    df_3P1F_mva = df_3P1F_mva.Define(
        "fr",
        "GetFR(fakeLep_pt, fakeLep_eta, fakeLep_pdgId)"
    )

    #weight
    df_3P1F_mva = df_3P1F_mva.Define(
        "tFactor_3P1F",
        "fr/(1-fr)"
    )

    df_3P1F_mva = df_3P1F_mva.Define("weight", "1.0")
    df_3P1F_mva = df_3P1F_mva.Define("mJets",  "mjj")

    histograms.append(mkhist(df_3P1F_mva, 'mJets',      '; mJets [GeV]',      60,0.,600., v='mJets'))
    histograms.append(mkhist(df_3P1F_mva, 'fr',        '; fr',              100, 0., 0.25, v='fr'))
    histograms.append(mkhist(df_3P1F_mva, 'm4l_3P1F','; m4l_3P1F [GeV]',60,0.,600., v='m4l_3P1F'))

    # Z+X distribution 3P1F
    h_ZX_m4l_3P1F = df_3P1F_mva.Histo1D(
        ("ZX_m4l_3P1F", ";m_{4l} (GeV);Events", 45, 150., 600.),
        "m4l_3P1F",
        "tFactor_3P1F")

    #------------------------------------------------
    #end 3P1F
    #------------------------------------------------

    # Z+X distribution total
    h_ZX_total = h_ZX_m4l_2P2F.Clone("ZX_m4l_total")
    h_ZX_total.Add(h_ZX_m4l_3P1F.GetPtr())

    h_ZX_total.SetTitle("ZX 2022 (muMva > -1, m4l > 180, all jets cuts);m_{4l};Events/10");

    f = ROOT.TFile(args.fname_out, "RECREATE")
    for h in histograms:
            h.Write()

    h_ZX_m4l_2P2F.Write()
    h_ZX_m4l_3P1F.Write()
    h_ZX_total.Write()

    f.Close()
    logging.info('Wrote to "%s"', args.fname_out)


def parse_args():
    parser = ArgumentParser(description='Produce histograms with the Z+X estimation')
    parser.add_argument('fnames_in', nargs='+', metavar='FILE', help='Input: (post-processed) NanoAOD file.'+
                        ' Ntuples are stored in "/eos/user/p/psalvini/MARIO_TAMI/ZZVBS_Analysis/muonMVA_data/<year>"'
                        )
    parser.add_argument('-o', '--output', default='ZX.root', dest='fname_out', metavar='FILE', help='Default: %(default)s')
    parser.add_argument('-y', '--year', default='2022EE')
    parser.add_argument('--log', dest='loglevel', metavar='LEVEL', default='WARNING', help='Level for the python logging module. Can be either a mnemonic string like DEBUG, INFO or WARNING or an integer (lower means more verbose).')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    args = parse_args()
    loglevel = args.loglevel.upper() if not args.loglevel.isdigit() else int(args.loglevel)
    logging.basicConfig(format='%(levelname)s:%(module)s:%(funcName)s: %(message)s', level=loglevel)

    exit(main(args))
