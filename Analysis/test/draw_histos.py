from __future__ import print_function
import math
import ctypes
import ROOT
import numpy as np
from array import array
ROOT.PyConfig.IgnoreCommandLineOptions = True

inFilenameMC   = "Test_MC.root"
outFilename = "Plots.root"

# da capire che sono 
blindPlots = True
blindHLow = 105.
blindHHi  = 140.
blindHM   = 500.
epsilon=0.1
addEmptyBins = True

Lum = 35.08424 # 1/fb 2022 C-G  (= 35.181930231/fb of full 355100_362760 Golden json - 0.097685694 of eraB that we don't use

# Set style matching the one used for HZZ plots
ROOT.TH1.SetDefaultSumw2()
ROOT.gStyle.SetErrorX(0)
ROOT.gStyle.SetPadTopMargin(0.05)  
ROOT.gStyle.SetPadBottomMargin(0.13)
ROOT.gStyle.SetPadLeftMargin(0.16) 
ROOT.gStyle.SetPadRightMargin(0.03)
ROOT.gStyle.SetLabelOffset(0.008, "XYZ")
ROOT.gStyle.SetLabelSize(0.04, "XYZ")
ROOT.gStyle.SetAxisColor(1, "XYZ")
ROOT.gStyle.SetStripDecimals(True)
ROOT.gStyle.SetTickLength(0.03, "XYZ")
ROOT.gStyle.SetNdivisions(510, "XYZ")
ROOT.gStyle.SetPadTickX(1)
ROOT.gStyle.SetPadTickY(1)
ROOT.gStyle.SetTitleSize(0.05, "XYZ")
ROOT.gStyle.SetTitleOffset(1.00, "X")
ROOT.gStyle.SetTitleOffset(1.25, "Y")
ROOT.gStyle.SetLabelOffset(0.008, "XYZ")
ROOT.gStyle.SetLabelSize(0.04, "XYZ")

canvasSizeX=910
canvasSizeY=700

# da capire che fanno
def printCanvases(type="png", path=".") :
    canvases = ROOT.gROOT.GetListOfCanvases()
    for c in canvases :
        c.Print(path+"/"+c.GetTitle()+"."+type)

def printCanvas(c, type="png", name=None, path="." ) :
    if name == None : name = c.GetTitle()
    name=name.replace(">","")
    name=name.replace("<","")
    name=name.replace(" ","_")
    c.Print(path+"/"+name+"."+type)

def Stack (f, version = "Z1Mass"):
    name = version

    #------------EW------------------#
    WWZ = f.Get(name+"WWZ")
    WZZ = f.Get(name+"WZZ")
    ZZZ = f.Get(name+"ZZZ")

    EWSamples = [WZZ, ZZZ]
    EW = WWZ.Clone("h_EW")
    for i in EWSamples:
        EW.Add(i,1.)
    EW.Scale(Lum*1000.)        
    EW.SetLineColor(ROOT.TColor.GetColor("#000099"))
    EW.SetFillColor(ROOT.TColor.GetColor("#0331B9"))

    #------------ggTo-----------------#
    ggTo4mu = f.Get(name+"ggTo4mu") 
    ggTo4e = f.Get(name+"ggTo4e")
    ggTo4tau = f.Get(name+"ggTo4tau")
    ggTo2e2mu = f.Get(name+"ggTo2e2mu")
    ggTo2e2tau = f.Get(name+"ggTo2e2tau")
    ggTo2mu2tau = f.Get(name+"ggTo2mu2tau")

    ggZZSamples = [ ggTo4e, ggTo4tau, ggTo2e2mu, ggTo2e2tau, ggTo2mu2tau]
    ggToZZ = ggTo4mu.Clone("h_ggTo")
    for i in ggZZSamples:
        ggToZZ.Add(i,1.)
    ggToZZ.Scale(Lum*1000.)    
    ggToZZ.SetLineColor(ROOT.TColor.GetColor("#000099"))
    ggToZZ.SetFillColor(ROOT.TColor.GetColor("#4b78ff"))  

     #-----------qqZZ---------------#
    ZZTo4l = f.Get(name+"ZZTo4l")
    ZZTo4l.Scale(Lum*1000.)    
    ZZTo4l.SetLineColor(ROOT.TColor.GetColor("#000099"))
    ZZTo4l.SetFillColor(ROOT.TColor.GetColor("#99ccff"))

    #------------------Stack----------#
    if version=="Z1Mass" :
        hs = ROOT.THStack("Stack_Z1Mass", "; m_{#it{Z1}} (GeV) ; Events" )
    elif version=="Z2Mass" :
        hs = ROOT.THStack("Stack_Z2Mass", "; m_{#it{Z2}} (GeV) ; Events" )

    hs.Add(EW,"HISTO")
    hs.Add(ggToZZ,"HISTO")
    hs.Add(ZZTo4l,"HISTO")

    return hs

fMC = ROOT.TFile.Open(inFilenameMC,"READ")
#fData = ROOT.TFile.Open(inFilenameData,"READ")
of = ROOT.TFile.Open(outFilename,"recreate")

# Labels for log plots
xlabelsv = [80, 100, 200, 300, 400, 500]
label_margin = -0.1
xlabels=[None]*len(xlabelsv)
for i, label in enumerate(xlabelsv): 
    xlabels[i] = ROOT.TLatex(label, label_margin , str(label));
    xlabels[i].SetTextAlign(23)
    xlabels[i].SetTextFont(42)
    xlabels[i].SetTextSize(0.04)

HStack = Stack(fMC)
HStack_hm = HStack.Clone()

Canvas = ROOT.TCanvas("MZ1","MZ1",canvasSizeX,canvasSizeY)
Canvas.SetTicks()
Canvas.SetLogx()
#ymaxd=HData.GetMaximum()
xmin=ctypes.c_double(0.)
ymin=ctypes.c_double(0.)
xmax=ctypes.c_double(0.)
ymax=ctypes.c_double(0.)
#HData.ComputeRange(xmin,ymin,xmax,ymax)
yhmax=math.ceil(max(HStack.GetMaximum(), ymax.value))
HStack.SetMaximum(yhmax)
HStack.Draw("histo")
HStack.GetXaxis().SetRangeUser(70., 300.)

HStack.GetXaxis().SetLabelSize(0)
for label in xlabels :
    label.Draw()
ROOT.gPad.RedrawAxis()

printCanvases()