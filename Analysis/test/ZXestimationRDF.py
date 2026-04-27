#!/bin/env python3

from __future__ import print_function
import os
import shutil
import math
import ROOT
import random
ROOT.PyConfig.IgnoreCommandLineOptions = True
from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection
from ZZAnalysis.NanoAnalysis.tools import getLeptons, get_genEventSumw
from ZZVBS_analysis.Analysis.FakeRates import FakeRates
from ZZVBS_analysis.Analysis.utils import TFileContext, mkhist, FinalState

#ROOT.ROOT.EnableImplicitMT()  # abilita multithreading
#frHelper = FakeRates(year="2018", method="OS")

#pathDir = "/eos/user/p/psalvini/MARIO_TAMI/ZZVBS_Analysis/muonMVA_data/2024"
#pathDir = "/eos/user/p/psalvini/MARIO_TAMI/ZZVBS_Analysis/muonMVA_data/2022postEE/chunkHadded"
pathDir = "/eos/user/p/psalvini/MARIO_TAMI/ZZVBS_Analysis/muonMVA_data/2022preEE/chunkHadded"
#FRpath  = "/eos/user/a/atamigio/ZZ_VBS_Analysis/FakeRates/FakeRates_OS_2022postEE_NomuMva.root"
FRpath  = "/eos/user/a/atamigio/ZZ_VBS_Analysis/FakeRates/FakeRates_OS_2022preEE_NomuMva.root"
#FRpath  = "/afs/cern.ch/user/a/atamigio/analysis/CMSSW_14_1_6/src/ZZAnalysis/AnalysisStep/data/FakeRates/FakeRates_OS_2018.root"
#FRpath  = "/eos/cms/store/group/phys_higgs/cmshzz4l/cjlst/HIG-25-015/RunIII_byZ1Z2/Moriond26_JES/FAKERATES/2024/FakeRates_OS_2024.root"


ROOT.gInterpreter.Declare(f"""
#include "FakeRates.hpp"

FakeRates fr("{FRpath}", "OS");

double GetFR(float pt, float eta, int id) {{
    return fr.getFRval(pt, eta, id);
}}
""")

root_files = [
    pathDir + "/" + subdir + "/ZZ4lAnalysis.root"
    for subdir in sorted(os.listdir(pathDir))
]

for f in root_files:
    print(f)

print("Numero di file:", len(root_files))

histograms = []

ROOT.EnableImplicitMT()

# Get the Events tree
df = ROOT.RDataFrame('Events', root_files)

df = df.Define("Jet1Idx",  "JetLeadingIdx")
df = df.Define("Jet2Idx",  "JetSubleadingIdx")
df = df.Define("nJets", "nCleanedJetsPt30")
#df = df.Define("muon_mva", "Muon_mvaLowPt")

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
df_3P1F_mva = df_3P1F_mva.Define("fakeLep_Idx",   "Lepton_ZZFullSel[l3_Idx] ? l4_Idx : l3_Idx") #da controllare questa cosa, non sono sicuro sia giusta

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


f = ROOT.TFile("ZX_estimation_2022preEE_mva_minus1_m180_allJetsCuts.root", "RECREATE")
for h in histograms:
        h.Write()

h_ZX_m4l_2P2F.Write()
h_ZX_m4l_3P1F.Write()
h_ZX_total.Write()

f.Close()
