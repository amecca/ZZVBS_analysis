SKIMDIR::=../../../ZZAnalysis/NanoAnalysis/test
HISTS1 ::= ZZjj-EWK_hists.root ZZjj-QCD_hists.root
LOGLEVEL ?= info
SAMPLES_2022EE ::= ZZTo4l ggTo2e2mu_Contin_MCFM701 ggTo4e_Contin_MCFM701 ggTo4mu_Contin_MCFM701 #TTLL_MLL-50 TTZZ WWZ WZZ ZZZ ggTo2e2tau_Contin_MCFM701 ggTo2mu2tau_Contin_MCFM701 ggTo4tau_Contin_MCFM701
HISTS_2022EE ::= $(patsubst %,hists/2022EE/%.root,$(SAMPLES_2022EE))

#/eos/user/p/psalvini/MARIO_TAMI/ZZVBS_Analysis/muonMVA
NTUPLE_DIR     ::= ntuples
SAMPLES_2024   ::= ZZTo4l_2Jets_EW ZZTo4l_2Jets_EW_QCD ZZTo4l_2Jets_QCD ZZ4Ljj_EWK_LL ZZ4Ljj_EWK_LT ZZ4Ljj_EWK_TT gg4l_POWHEG ggTo2e2mu_Contin_MCFM701 #ggTo4e_Contin_MCFM701 ggTo4mu_Contin_MCFM701 # ZZTo4l TTLL_MLL-4to50 TTLL_MLL-50 TTWW WWZ WZZ ZZZ
NTUPLE_PATTERN ::= $(patsubst %,$(NTUPLE_DIR)/2024/%_Chunk%,$(SAMPLES_2024))
NTUPLES_2024_ALL::= $(shell find $(NTUPLE_DIR)/2024/ -maxdepth 1 -type d -name "*Chunk*")
NTUPLES_2024   ::= $(filter $(NTUPLE_PATTERN),$(NTUPLES_2024_ALL))
HISTS_2024     ::= $(patsubst $(NTUPLE_DIR)/2024/%,hists/2024/%.root,$(NTUPLES_2024))

# all: ZZjj-EWK_hists.root ZZjj-QCD_hists.root
all: $(HISTS_2024_gg2e2muPOWHEG) #$(HISTS_2024) # compareplots/2023postBPix/.timestamp #$(HISTS_2022EE)
.PHONY: all

# Skip rules
.SUFFIXES:
Makefile:;
%.py:;
%_Skim.root:;
%.root:;
%.timestamp:;

.SECONDARY:

# Recipes
# %_hists.root: $(SKIMDIR)/%_Skim.root nano2hists.py | skim
# 	./nano2hists.py --log info -o $@ $<
#
# skim:
# 	$(MAKE) -C $(SKIMDIR)
# .PHONY: skim

hists/2023postBPix/%_Chunk0.root: ntuples/2023postBPix/%_Chunk0/ZZ4lAnalysis.root nano2hists.py
	./nano2hists.py --log $(LOGLEVEL) -o $@ $<

hists/2022EE/%.root: ntuples/2022EE/%/ZZ4lAnalysis.root nano2hists.py
	./nano2hists.py --log $(LOGLEVEL) -o $@ $<

hists/2022EE/.timestamp: $(HISTS_2022EE)

hists/2024/%.root: $(NTUPLE_DIR)/2024/%/ZZ4lAnalysis.root nano2hists.py #| hists/2024
	./nano2hists.py --log $(LOGLEVEL) -o $@ $<
hists_cut/2024/%.root: /eos/user/a/amecca/samples/ZZVBS_Analysis/muonCUT/2024/%/ZZ4lAnalysis.root nano2hists.py #| hists_cut/2024
	./nano2hists.py --log $(LOGLEVEL) -o $@ $<

# hists/%: | hists
# 	mkdir $@
# hists_cut/%: | hists_cut
# 	mkdir $@
# plots/%: | plots
# 	mkdir $@
# compare_muID/%: | compare_muID
# 	mkdir $@
# compare_gg4l/%: | compare_gg4l
# 	mkdir $@
# compare_pol/%: | compare_pol
# 	mkdir $@
# hists plots compare_muID compare_gg4l compare_pol hists_cut:
# 	mkdir $@

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

HISTS_2024_ZZjj-EWK ::= $(patsubst %,hists/2024/ZZTo4l_2Jets_EW_Chunk%.root,$(shell seq 0 2))
HISTS_2024_ZZjj-QCD ::= $(patsubst %,hists/2024/ZZTo4l_2Jets_QCD_Chunk%.root,$(shell seq 0 1))
HISTS_2024_ZZjj-EWK_pol  ::= $(patsubst %,hists/2024/%,ZZ4Ljj_EWK_LL_Chunk0.root ZZ4Ljj_EWK_LL_Chunk1.root ZZ4Ljj_EWK_LL_Chunk2.root ZZ4Ljj_EWK_LL_Chunk3.root ZZ4Ljj_EWK_LL_Chunk4.root ZZ4Ljj_EWK_LL_Chunk5.root ZZ4Ljj_EWK_LL_Chunk6.root ZZ4Ljj_EWK_LL_Chunk7.root ZZ4Ljj_EWK_LL_Chunk8.root ZZ4Ljj_EWK_LL_Chunk9.root ZZ4Ljj_EWK_LT_Chunk0.root ZZ4Ljj_EWK_LT_Chunk1.root ZZ4Ljj_EWK_LT_Chunk2.root ZZ4Ljj_EWK_LT_Chunk3.root ZZ4Ljj_EWK_LT_Chunk4.root ZZ4Ljj_EWK_LT_Chunk5.root ZZ4Ljj_EWK_LT_Chunk6.root ZZ4Ljj_EWK_LT_Chunk7.root ZZ4Ljj_EWK_LT_Chunk8.root ZZ4Ljj_EWK_LT_Chunk9.root ZZ4Ljj_EWK_TT_Chunk0.root ZZ4Ljj_EWK_TT_Chunk1.root ZZ4Ljj_EWK_TT_Chunk2.root ZZ4Ljj_EWK_TT_Chunk3.root ZZ4Ljj_EWK_TT_Chunk4.root ZZ4Ljj_EWK_TT_Chunk5.root ZZ4Ljj_EWK_TT_Chunk6.root ZZ4Ljj_EWK_TT_Chunk7.root ZZ4Ljj_EWK_TT_Chunk8.root ZZ4Ljj_EWK_TT_Chunk9.root)
compare_pol/2024/.timestamp: compare_samples.py $(HISTS_2024_ZZjj-EWK_pol) $(HISTS_2024_ZZjj-EWK) | compare_pol/2024
	./compare_samples.py -o $(@D) -y 2024 --log $(LOGLEVEL) \
	-1 hists/2024/ZZ4Ljj_EWK_{LL,LT,TT}_Chunk*.root \
	-2 hists/2024/ZZTo4l_2Jets_EW_Chunk*.root \
	--scale1 39.809 \
	--title1 "ZZjj #rightarrow 4ljj LL+LT+TT" --title2 "ZZjj #rightarrow 4ljj inclusive" --title-r "LL+LT+TT/incl."
	touch $@

HISTS_2024_gg2e2muMCFM   ::= $(patsubst %,hists/2024/ggTo2e2mu_Contin_MCFM701_Chunk%.root,$(shell seq 0 24))
HISTS_2024_gg2e2muPOWHEG ::= $(patsubst %,hists/2024/gg4l_POWHEG_Chunk%.root,$(shell seq 0 9))
compare_gg4l/2024/.timestamp: compare_samples.py $(HISTS_2024_gg2e2muMCFM) $(HISTS_2024_gg2e2muPOWHEG) | compare_gg4l/2024
	./compare_samples.py -o $(@D) -y 2024 --log $(LOGLEVEL) \
	-1 hists/2024/ggTo2e2mu_Contin_MCFM701_Chunk*.root \
	-2 hists/2024/gg4l_POWHEG_Chunk*.root \
	--logy \
	--norm \
	--title1 "gg #rightarrow 2e2#mu MCFM" --title2 "gg #rightarrow 2e2#mu POWHEG" --title-r "POW/MCFM"
	touch $@

compare_EW-QCD/2024/.timestamp: compare_samples.py $(HISTS_2024_ZZjj-EWK) $(HISTS_2024_ZZjj-QCD) | compare_gg4l/2024
	./compare_samples.py -o $(@D) -y 2024 --log $(LOGLEVEL) \
	-1 $(HISTS_2024_ZZjj-QCD) \
	-2 $(HISTS_2024_ZZjj-EWK) \
	--title1 "qq #rightarrow ZZjj #rightarrow 4l jj QCD" --title2 "qq #rightarrow ZZjj #rightarrow 4l jj EWK" --title-r "EWK/QCD"
	touch $@

HISTS_2024_ZZjj-EWK_cut ::= $(patsubst %,hists_cut/2024/ZZTo4l_2Jets_EW_Chunk%.root,$(shell seq 0 2))
compare_muID/2024/.timestamp: compare_samples.py $(HISTS_2024_ZZjj-EWK_cut) $(HISTS_2024_ZZjj-EWK) | compare_muID/2024
	./compare_samples.py -o $(@D) -y 2024 --log $(LOGLEVEL) \
	-1 hists_cut/2024/ZZTo4l_2Jets_EW_Chunk*.root \
	-2 hists/2024/ZZTo4l_2Jets_EW_Chunk*.root \
	--title1 "ZZjj-EW, cut-based #mu ID" --title2 "ZZjj-EW, MVA #mu ID" --title-r "MVA/cut-based"
	touch $@

compare_muID/2024/%_upper.png: compare_muID/2024/.timestamp
	convert +append $(@D)/$*_4mu.png $(@D)/$*_2mu2e.png +repage $@
compare_muID/2024/%_lower.png: compare_muID/2024/.timestamp
	convert +append $(@D)/$*_2e2mu.png $(@D)/$*_4e.png +repage $@
compare_muID/2024/%_channels.png: compare_muID/2024/%_upper.png compare_muID/2024/%_lower.png
	convert -append $^ +repage $@

./%.svg: ./%.dot
	dot -Tsvg $< -o$@

# Phony helpers
.PHONY: debug
debug:
	@echo "NTUPLE_PATTERN  : $(NTUPLE_PATTERN)"
	@echo "NTUPLES_2024_ALL: $(shell echo $(NTUPLES_2024_ALL) | wc -w)"
	@echo "NTUPLES_2024    : $(shell echo $(NTUPLES_2024) | wc -w)"
	@echo "HISTS_2024      : $(HISTS_2024)"
	@echo "HISTS_2024_gg2e2muPOWHEG: $(HISTS_2024_gg2e2muPOWHEG)"
#@echo "HISTS_2024  : $(HISTS_2024)"
# @echo "HISTS_2022EE: $(HISTS_2022EE)"

.PHONY: test
test: .test_EWK .test_QCD
.test_%: ZZjj-%_hists.root ZZjj-%_histref.root
	compare_rootfiles3.py $^
	touch $@

.PHONY: plots_compare_muID
plots_compare: plots/.timestamp
