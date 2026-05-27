#include "MELAhelper.hpp"

#include <stdio.h>  /* stdout */
#include <unistd.h> /* dup(), dup2() */
#include <fcntl.h>  /* O_WRONLY */

#include "TLorentzVector.h"

/* Headers from JHUGenMELA/MELA/interface/ */
#include "TVar.hh"
#include "Mela.h"

using ROOT::Math::PtEtaPhiMVector;
using ROOT::VecOps::RVec;
using ROOT::RVecI;

// Mela&
MELAhelper::MELAhelper(UInt_t n_threads) : init_status_(1), n_threads_(n_threads) {
  init_status_ = init();
}


int
MELAhelper::init() {
  printf("INFO:%s: constructing Mela\n", __func__);
  /* Allocate space for all the MELA pointers.
     Comment from A.M.: Presently (2026-05-27), Mela does not have an
     implementation of operator=(), so this crashes:
     ```
     Mela* mela_vec;
     [...]
     for(UInt_t i...) { mela_vec[i] = Mela(...) }
     ```
     Thus we must keep a vector of pointers, instead of objects */
  mela_vec_ = (Mela**) malloc(sizeof(Mela*) * n_threads_);

  /* Construct the MELA objects. This calls Mela::build(), which prints a lot
     to stdout: thus we redirect stdout to /dev/null for a bit */

  int fd_stdout, fd_stdout_copy, fd_devnull;
  fflush(stdout);
  fd_stdout = fileno(stdout);
  fd_devnull = open("/dev/null", O_WRONLY);
  fd_stdout_copy = dup(fd_stdout); /* needed to restore it later */
  dup2(fd_devnull, fd_stdout); /* this does the redirection */

  for(UInt_t i = 0; i < n_threads_; ++i) {
    void* space = aligned_alloc(64, sizeof(Mela)); /* align to cache line boundary to avoid false sharing */
    if(!space) {
      fprintf(stderr, "FATAL:%s: allocation failed for Mela object %u\n", __func__, i);
      return 2;
    }
    Mela* mela = new(space) Mela(SQRTS, MH, TVar::VerbosityLevel::ERROR);
    mela->setCandidateDecayMode(TVar::CandidateDecayMode::CandidateDecay_ZZ);
    mela_vec_[i] = mela;
  }

  /* Restore the original stdout */
  dup2(fd_stdout_copy, fd_stdout);

  for(UInt_t i = 0; i < n_threads_; ++i)
    printf("DEBUG: Mela (%u) at %p\n", i, mela_vec_[i]);

  printf("DEBUG:%s: END\n", __func__);
  return 0;
}

/* Helper to convert the modern `LorentzVector`s used in NanoOAD to legacy 
   `TLorentzVector`s used in MELA */
TLorentzVector
lorentz2Tlorentz(const PtEtaPhiMVector& l) {
  TLorentzVector t;
  t.SetPtEtaPhiM(l.pt(), l.eta(), l.phi(), l.M());
  return t;
}

/* MELAhelper member functions */
int
MELAhelper::set_input_event(UInt_t slot /*multithreading in RDF*/,
			  const RVec<PtEtaPhiMVector>& ZZLepton_p4, const RVecI& ZZLepton_pdgId,
			  const RVec<PtEtaPhiMVector>&      Jet_p4, const RVecI&      Jet_pdgId) {
  if(slot > n_threads_-1) {
    fprintf(stderr, "ERROR:%s: requested slot %u, but the helper was built for a maximum of %u threads\n", __func__, slot, n_threads_);
    exit(2);
  }
  if(init_status_ != 0) {
    if(init_status_ == 1) fprintf(stderr, "ERROR:%s: Mela was not initialized\n", __func__);
    else fprintf(stderr, "ERROR:%s: Mela::init() failed with error %i\n", __func__, init_status_);
    exit(2);
  }

  /* Create the collections needed by Mela: leptons in ZZ and "extra" (jets in our case) */
  SimpleParticleCollection_t daughters, associates;
  size_t nlep = ZZLepton_p4.size();

  if(ZZLepton_pdgId.size() != nlep || nlep != 4) {
    fprintf(stderr, "ERROR:%s: number of leptons' p4=%ld, pdgId=%ld; both must be 4",
	    __func__, nlep, ZZLepton_pdgId.size());
    exit(2);
  }
  daughters.reserve(4);

  for(size_t i = 0; i < 4; ++i)
    daughters.emplace_back(ZZLepton_pdgId[i],
			   lorentz2Tlorentz(ZZLepton_p4[i]));

  /* Assume that the jets are sorted in pt, or that MELA does not care 
     Take at most two jets
   */
  for(size_t i = 0; i < std::min(2ul, Jet_p4.size()); ++i)
    associates.emplace_back(Jet_pdgId[i],
			    lorentz2Tlorentz(Jet_p4[i]));

  /* Get the mela object allocated for this thread ("slot") */
  Mela* mela = mela_vec_[slot];
  mela->setInputEvent(&daughters, &associates /*no LHE information */);

  return 0;
}

float
MELAhelper::prob_EWK(UInt_t slot) {
  // printf("INFO:%s: slot %u\n", __func__, slot);
  Mela* mela = mela_vec_[slot];
  mela->setProcess(TVar::Process::bkgZZ, TVar::MatrixElement::MCFM, TVar::Production::JJVBF);
  return compute_prob(*mela);
}

float
MELAhelper::prob_QCD(UInt_t slot){
  Mela* mela = mela_vec_[slot];
  mela->setProcess(TVar::Process::bkgZZ, TVar::MatrixElement::MCFM, TVar::Production::JJQCD);
  return compute_prob(*mela);
}

float
MELAhelper::compute_prob(Mela& mela) {
  /* computeProdDecP <--> both "prob" and "dec" settings in the wrapper are true */
  float p;
  /* this function is not marked const in Mela, but hopefully it does not modify
     the object in such a way that consecutive calls return differnt values */
  mela.computeProdDecP(p, USECONSTANT);
  // printf("INFO:%s: p = %.3e\n", __func__, p);
  return p;
}
