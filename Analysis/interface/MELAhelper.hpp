/**
 * Wrapper around JHUGenMela Mela, used to compute MELA scores in a RDataFrame
 * environment.
 *
 * Author: A. Mecca (alberto.mecca@cern.ch)
 * Creation date: 2026-05-27
 */

#ifndef MELAHELPER_HPP
#define MELAHELPER_HPP

#include "ROOT/RVec.hxx"
#include <Math/Vector4D.h>

#include "Mela.h"


class MELAhelper {
  /* This class is meant to be used with multithreaded RDataFrame, thus:
   * - The constructor takes the number of threads as argument
   *   - in python, one can do `ROOT.gInterpreter.Declare("MELAhelper mela(max(1u, ROOT.GetThreadPoolSize()))")`
   * - The functions take the thread index as the first parameter
   *   - e.g `df = df.Define("P_EWK", "mela.prob_EWK(rdfslot_)")`
   *   - TODO (A.M.) test if `DefineSlot("", "mela.prob_EWK()")` works
   * - The setInputEvent should be run once per event in RDF, and then the probabilities can be computed;
   *   one way to convince the RDF engine of this dependence, is to use the 0 returned by that function:
   *   `df = df.Define("_MELAsetup", "mela.setInputEvent(ZZLeptons_p4, ...)")`
   *   `df = df.Define("P_EWK", "_MELAsetup+mela.prob_EWK(rdfslot_)")`
   *   `df = df.Define("P_QCD", "_MELAsetup+mela.prob_QCD(rdfslot_)")`
   */

public:
  /* Constants and "constants" (hardcoded values because of lazyness) */
  static constexpr double SQRTS       = 13.6;  /*TeV*/
  static constexpr double MH          = 125.;  /*GeV*/
  static constexpr bool   USECONSTANT = false; /*normalizes the probability; we do not need it, since we use the ratio*/

  MELAhelper(UInt_t n_threads);

  int init();
  int set_input_event(UInt_t slot,
		      const ROOT::VecOps::RVec<ROOT::Math::PtEtaPhiMVector>& ZZLepton_p4, const ROOT::RVecI& ZZLepton_pdgId,
		      const ROOT::VecOps::RVec<ROOT::Math::PtEtaPhiMVector>&      Jet_p4, const ROOT::RVecI&      Jet_pdgId);
  float prob_EWK(UInt_t slot);
  float prob_QCD(UInt_t slot);

  int init_status() const { return init_status_; }

protected:
  Mela& get_or_make(UInt_t n_threads);
  static float compute_prob(Mela&);

private:
  /* Keep an array of Mela, one for each RDF thread so we don't have to deal with locks */
  int init_status_;
  UInt_t n_threads_;
  Mela** mela_vec_;
};

#endif
