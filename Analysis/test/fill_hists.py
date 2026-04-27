#!/bin/env python3

from __future__ import print_function
import math
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection
from ZZAnalysis.NanoAnalysis.tools import getLeptons, get_genEventSumw

pathMC = "/eos/home-a/atamigio/ZZ_VBS_Analysis/Productions/PROD_samplesNano_2022_MC_c10cce63_09Dic25/chunkHadded/"
#pathData = "/eos/home-a/atamigio/ZZ_VBS_Analysis/Productions/PROD_samplesNano_2022_MC_c10cce63_09Dic25/chunkHadded/"

ROOT.TH1.SetDefaultSumw2()

maxEntriesPerSample = None # Use only up to this number of events in each MC sample, for quick tests; use None for no scaling

def fillHistos(samplename, filename) :

    h_Z1Mass = ROOT.TH1F("Z1Mass"+samplename,"Z1Mass"+samplename,200,30.,130.)
    h_Z1Mass.GetXaxis().SetTitle("m_{#it{Z1}} (GeV)")
    h_Z1Mass.GetYaxis().SetTitle("Events")

    h_Z2Mass = ROOT.TH1F("Z2Mass"+samplename,"Z1Mass"+samplename,260,0.,130.)
    h_Z2Mass.GetXaxis().SetTitle("m_{#it{Z2}} (GeV)")
    h_Z2Mass.GetYaxis().SetTitle("Events")

    f = ROOT.TFile.Open(filename)

    event = f.Events
    event.SetBranchStatus("*", 0)
    event.SetBranchStatus("run", 1)
    event.SetBranchStatus("luminosityBlock", 1)
    event.SetBranchStatus("*Muon*", 1)
    event.SetBranchStatus("*Electron*", 1)
    event.SetBranchStatus("*ZZCand*", 1)
    event.SetBranchStatus("bestCandIdx", 1)
    event.SetBranchStatus("HLT_passZZ4l", 1)
    nEntries = event.GetEntries()

    isMC = False
    if(samplename == "Data"):
        print("Data: sel=", nEntries)
    else:
        isMC = True
        event.SetBranchStatus("overallEventWeight",1)

        # Get sum of weights
        genEventSumw = get_genEventSumw(f, maxEntriesPerSample)

    iEntry=0
    sum_overallEventW=0
    printEntries=max(5000,nEntries/10)
    while iEntry<nEntries and event.GetEntry(iEntry):
        iEntry+=1
        if iEntry%printEntries == 0 : print("Processing", iEntry)

        bestCandIdx = event.bestCandIdx
 
        # Check that the event contains a selected candidate, and that
        # passes the required triggers (which is necessary for samples
        # processed with TRIGPASSTHROUGH=True)
        if(bestCandIdx != -1 and event.HLT_passZZ4l): 
            weight = 1.
            ZZs = Collection(event, 'ZZCand')
            theZZ = ZZs[bestCandIdx]
            #sumDataWeight += weight
            #print(sumDataWeight)
            #print(theZZ)
	           
            if isMC : 
                weight = (event.overallEventWeight*theZZ.dataMCWeight/genEventSumw)
                mZ1=theZZ.Z1mass
                mZ2=theZZ.Z2mass
                h_Z1Mass.Fill(mZ1,weight)
                h_Z2Mass.Fill(mZ2,weight)
                # Example on how to get the four leptons of the candidates, ordered as
                # [Z1l1, Z2l2, Z2l1, Z2l2]
                #leps = getLeptons(theZZ, event)
                #print(leps[3].pt)
                sum_overallEventW += event.overallEventWeight
                #print(sum_overallEventW)
                    
    f.Close()

    return h_Z1Mass, h_Z2Mass

def runMC():
    outFile = "Test_MC.root" 

    samples = [
        dict(name = "WWZ",filename = pathMC+"WWZ/ZZ4lAnalysis.root"),
        dict(name = "WZZ",filename = pathMC+"WZZ/ZZ4lAnalysis.root"),
        dict(name = "ZZZ",filename = pathMC+"ZZZ/ZZ4lAnalysis.root"),
        
        # dict(name = "VBFToZZTo4l",filename = pathMC + "VBFToContinToZZTo4l/ZZ4lAnalysis.root"),
        # dict(name = "TTZToLLNuNu",filename = pathMC + "TTZToLLNuNu_M10ext1/ZZ4lAnalysis.root"),
        # dict(name = "TTZJets",filename = pathMC + "TTZJets_M10_MLMext1/ZZ4lAnalysis.root"),

        dict(name = "ggTo4mu",filename = pathMC+"ggTo4mu_Contin_MCFM701/ZZ4lAnalysis.root"),
        dict(name = "ggTo4e",filename = pathMC+"ggTo4e_Contin_MCFM701/ZZ4lAnalysis.root"),
        dict(name = "ggTo4tau",filename = pathMC+"ggTo4tau_Contin_MCFM701/ZZ4lAnalysis.root"),
        dict(name = "ggTo2e2mu",filename = pathMC+"ggTo2e2mu_Contin_MCFM701/ZZ4lAnalysis.root"),       
        dict(name = "ggTo2e2tau",filename = pathMC+"ggTo2e2tau_Contin_MCFM701/ZZ4lAnalysis.root"),
        dict(name = "ggTo2mu2tau",filename = pathMC+"ggTo2mu2tau_Contin_MCFM701/ZZ4lAnalysis.root"),

        # dict(name = "ZZTo4l",filename = pathMC+"ZZTo4lext1/ZZ4lAnalysis.root"),
        dict(name = "ZZTo4l",filename = pathMC+"ZZTo4l/ZZ4lAnalysis.root"),
        
        # dict(name = "ggH125",filename = pathMC+"ggH125/ZZ4lAnalysis.root"),
        # dict(name = "VBF125",filename = pathMC+"VBFH125/ZZ4lAnalysis.root"),
        # dict(name = "WplusH125",filename = pathMC+"WplusH125/ZZ4lAnalysis.root"),
        # dict(name = "WminusH125",filename = pathMC+"WminusH125/ZZ4lAnalysis.root"),
        # dict(name = "ZH125",filename = pathMC+"ZH125/ZZ4lAnalysis.root"),
        # dict(name = "ttH125",filename = pathMC+"ttH125/ZZ4lAnalysis.root"),
    ]


    of = ROOT.TFile.Open(outFile,"recreate") 

    for s in samples:
        histos = fillHistos(s["name"], s["filename"])
        for h in histos:
            of.WriteObject(h,h.GetName())

    of.Close()

if __name__ == "__main__" :
    runMC()