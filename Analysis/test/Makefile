SKIMDIR::=../../../ZZAnalysis/NanoAnalysis/test
HISTS1 ::= ZZjj-EWK_hists.root ZZjj-QCD_hists.root
LOGLEVEL ?= info
SAMPLES_2022EE ::= ZZTo4l ggTo2e2mu_Contin_MCFM701 ggTo4e_Contin_MCFM701 ggTo4mu_Contin_MCFM701 #TTLL_MLL-50 TTZZ WWZ WZZ ZZZ ggTo2e2tau_Contin_MCFM701 ggTo2mu2tau_Contin_MCFM701 ggTo4tau_Contin_MCFM701
HISTS_2022EE ::= $(patsubst %,hists/2022EE/%.root,$(SAMPLES_2022EE))

#/eos/user/p/psalvini/MARIO_TAMI/ZZVBS_Analysis/muonMVA
NTUPLE_DIR     ::= ntuples
SAMPLES_2024   ::= ZZTo4l_2Jets_EW ZZTo4l_2Jets_EW_QCD ZZTo4l_2Jets_QCD ZZ4Ljj_EWK_LL ZZ4Ljj_EWK_LT ZZ4Ljj_EWK_TT gg4l_POWHEG ggTo2e2mu_Contin_MCFM701 #ggTo4e_Contin_MCFM701 ggTo4m
DATASETS_2024  ::= \
$(patsubst %,EGamma02024%,Cv1 Dv1 Ev1 Fv1 Gv2 Hv2 Iv1 Iv2) \
$(patsubst %,EGamma12024%,Cv1 Dv1 Ev1 Fv1 Gv2 Hv1 Iv1 Iv2) \
$(patsubst %,Muon02024%,  Cv1 Dv1 Ev1 Fv1 Gv1 Hv1 Iv1 Iv2) \
$(patsubst %,Muon12024%,  Cv1 Dv1 Ev1 Fv1 Gv2 Hv2 Iv1 Iv2) \
$(patsubst %,MuonEG2024%, Cv1 Dv1 Ev1 Fv2 Gv3 Hv2 Iv2 Iv2v2)

HISTS_MC_2024  ::= $(patsubst %,hists/2024/%.root,$(SAMPLES_2024))

DIRS ::= \
  hists $(patsubst %,hists/%,2022EE 2024) \
  hists_data $(patsubst %,hists_data/%,2022EE 2024) \
  hists_cut hists_cut/2024 compare_muID compare_muID/2024 \
  hists_pol hists_pol/2024 compare_pol compare_pol/2024 \
  dataMC/2024 \

# all: ZZjj-EWK_hists.root ZZjj-QCD_hists.root
all: $(HISTS_2024_gg2e2muPOWHEG) #$(HISTS_2024) # compareplots/2023postBPix/.timestamp #$(HISTS_2022EE)
.PHONY: all

# Skip rules
.SUFFIXES:
Makefile:;
%.timestamp:;
ntuples/%:;
ntuples_data/%:;

.SECONDARY:

### Recipes

hists/2023postBPix/%_Chunk0.root: ntuples/2023postBPix/%_Chunk0/ZZ4lAnalysis.root nano2hists.py
	./nano2hists.py --MC -y 2023postBPix --log $(LOGLEVEL) -o $@ $<

hists/2022EE/%.root: ntuples/2022EE/%/ZZ4lAnalysis.root nano2hists.py
	./nano2hists.py --MC -y 2023postBPix --log $(LOGLEVEL) -o $@ $<

hists/2022EE/.timestamp: $(HISTS_2022EE)

hists/2024/%.root: nano2hists.py $(NTUPLE_DIR)/2024/%_Chunk*/ZZ4lAnalysis.root | hists/2024
	./$< --MC   -y 2024 --log $(LOGLEVEL) -o $@ $(wordlist 2,$(words $^),$^)
hists_cut/2024/%.root: nano2hists.py /eos/user/a/amecca/samples/ZZVBS_Analysis/muonCUT/2024/%_Chunk*/ZZ4lAnalysis.root | hists_cut/2024
	./$< --MC   -y 2024 --log $(LOGLEVEL) -o $@ $(wordlist 2,$(words $^),$^)
hists_data/2024/%.root: nano2hists.py ntuples_data/2024/%_Chunk*/ZZ4lAnalysis.root | hists_data/2024
	./$< --data -y 2024 --log $(LOGLEVEL) -o $@ $(wordlist 2,$(words $^),$^)

hists/2024/data.root: $(patsubst %,hists_data/2024/%.root,$(DATASETS_2024))
	hadd -f --ff $@ $^

$(DIRS):
	mkdir -p $@

compareplots/%/.timestamp: compare_samples.py | hists/%

plots/2022EE/.timestamp: hists/2022EE/.timestamp
	./plot_dataMC.py --log $(LOGLEVEL) -y 2022EE hists/2022EE -o plots/2022EE
	touch $@

# compare_muID/2023postBPix/.timestamp: compare_samples.py hists/2023postBPix/ZZTo4l_2Jets_EW_Chunk0.root hists/2023postBPix/ZZTo4l_2Jets_EW_muIDmva_Chunk0.root | compareplots/2023postBPix
# 	./compare_samples.py -o compare_muID/2023BPix -y 2023BPix --log $(LOGLEVEL) \
# 	-1 hists/2023postBPix/ZZTo4l_2Jets_EW_Chunk*.root \
# 	-2 hists/2023postBPix/ZZTo4l_2Jets_EW_muIDmva_Chunk*.root \
# 	--title1 "ZZjj-EW, cut-based #mu ID" --title2 "ZZjj-EW, MVA #mu ID" --title-r "MVA/cut-based"
# 	touch $@

HISTS_2024_ZZjj-EWK_pol  ::= $(patsubst %,hists/2024/ZZ4Ljj_EWK_%.root,LL LT TT)
compare_pol/2024/.timestamp: compare_samples.py hists/2024/ZZTo4l_2Jets_EW.root $(HISTS_2024_ZZjj-EWK_pol) | compare_pol/2024
	./compare_samples.py -o $(@D) -y 2024 --log $(LOGLEVEL) \
	-1 $(wordlist 3,$(words $^),$^) \
	-2 $(word 2,$^) \
	--scale1 39.809 \
	--title1 "ZZjj #rightarrow 4ljj LL+LT+TT" --title2 "ZZjj #rightarrow 4ljj inclusive" --title-r "LL+LT+TT/incl."
	touch $@

compare_gg4l/2024/.timestamp: compare_samples.py hists/2024/ggTo2e2mu_Contin_MCFM701.root hists/2024/gg4l_POWHEG.root | compare_gg4l/2024
	./compare_samples.py -o $(@D) -y 2024 --log $(LOGLEVEL) \
	-1 $(word 2,$^) \
	-2 $(word 3,$^) \
	--logy \
	--title1 "gg #rightarrow 2e2#mu MCFM" --title2 "gg #rightarrow 2e2#mu POWHEG" --title-r "POW/MCFM"
	touch $@

compare_EW-QCD/2024/.timestamp: compare_samples.py hists/2024/ZZTo4l_2Jets_EW.root hists/2024/ZZTo4l_2Jets_QCD.root | compare_gg4l/2024
	./compare_samples.py -o $(@D) -y 2024 --log $(LOGLEVEL) \
	-1 $(word 2,$^) \
	-2 $(word 3,$^) \
	--title1 "qq #rightarrow ZZjj #rightarrow 4l jj QCD" --title2 "qq #rightarrow ZZjj #rightarrow 4l jj EWK" --title-r "EWK/QCD"
	touch $@

compare_muID/2024/.timestamp: compare_samples.py hists_cut/2024/ZZTo4l_2Jets_EW.root hists/2024/ZZTo4l_2Jets_EW.root | compare_muID/2024
	./compare_samples.py -o $(@D) -y 2024 --log $(LOGLEVEL) \
	-1 $(word 2,$^) \
	-2 $(word 3,$^) \
	--title1 "ZZjj-EW, cut-based #mu ID" --title2 "ZZjj-EW, MVA #mu ID" --title-r "MVA/cut-based"
	touch $@

compare_muID/2024/%_upper.png: compare_muID/2024/.timestamp
	convert +append $(@D)/$*_4mu.png $(@D)/$*_2mu2e.png +repage $@
compare_muID/2024/%_lower.png: compare_muID/2024/.timestamp
	convert +append $(@D)/$*_2e2mu.png $(@D)/$*_4e.png +repage $@
compare_muID/2024/%_channels.png: compare_muID/2024/%_upper.png compare_muID/2024/%_lower.png
	convert -append $^ +repage $@

dataMC/2024/.timestamp: plot_dataMC.py $(HISTS_MC_2024) hists/2024/data.root | dataMC/2024
	./$< -o $(@D) -y 2024 --log $(LOGLEVEL) hists/2024
	touch $@

./%.svg: ./%.dot
	dot -Tsvg $< -o$@

# Phony helpers
.PHONY: debug
debug:
	@echo "HISTS_2024      : $(HISTS_2024)"
	@echo "HISTS_2024_gg2e2muPOWHEG: $(HISTS_2024_gg2e2muPOWHEG)"
	@echo "DATASETS_2024: $(DATASETS_2024)"
#@echo "HISTS_2024  : $(HISTS_2024)"
# @echo "HISTS_2022EE: $(HISTS_2022EE)"

.PHONY: test
test: .test_EWK .test_QCD
.test_%: ZZjj-%_hists.root ZZjj-%_histref.root
	compare_rootfiles3.py $^
	touch $@

.PHONY: hists-data hists-MC
hists-data: hists/2024/data.root
hists-MC: $(HISTS_MC_2024)

.PHONY: plots_compare_muID
plots_compare: plots/.timestamp
