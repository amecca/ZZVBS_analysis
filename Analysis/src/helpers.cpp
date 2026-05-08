#include "helpers.hpp"
#include <Math/Vector4D.h>

using ROOT::Math::PtEtaPhiMVector;
using ROOT::Math::PtEtaPhiEVector;
using ROOT::VecOps::RVec;
using ROOT::RVecI;
using ROOT::RVecF;


float
sum_M_mass(float pt1, float eta1, float phi1, float m1,
	   float pt2, float eta2, float phi2, float m2) {
  PtEtaPhiMVector p4_1 {pt1, eta1, phi1, m1};
  PtEtaPhiMVector p4_2 {pt2, eta2, phi2, m2};
  auto p4_sum = p4_1 + p4_2;
  return p4_sum.M();
}

float
sum_E_mass(float pt1, float eta1, float phi1, float e1,
	   float pt2, float eta2, float phi2, float e2) {
  PtEtaPhiEVector p4_1 {pt1, eta1, phi1, e1};
  PtEtaPhiEVector p4_2 {pt2, eta2, phi2, e2};
  auto p4_sum = p4_1 + p4_2;
  return p4_sum.M();
}

PtEtaPhiMVector
sum4_M(float pt1, float eta1, float phi1, float m1,
       float pt2, float eta2, float phi2, float m2,
       float pt3, float eta3, float phi3, float m3,
       float pt4, float eta4, float phi4, float m4) {
  PtEtaPhiMVector p4_1 {pt1, eta1, phi1, m1};
  PtEtaPhiMVector p4_2 {pt2, eta2, phi2, m2};
  PtEtaPhiMVector p4_3 {pt3, eta3, phi3, m3};
  PtEtaPhiMVector p4_4 {pt4, eta4, phi4, m4};
  auto p4_sum = p4_1 + p4_2 + p4_3 + p4_4;
  return p4_sum;
}

/* Get the indexes of elements passing a cut */
template<class T>
RVecI
idx_passingT(const RVec<T>& vec, std::function<bool(T)> f) {
  RVecI out;
  out.reserve(vec.size());
  for(int i = 0; i < (int)vec.size(); ++i) {
    if(f(vec[i]))
      out.push_back(i);
  }
  return out;
}

/* explicit template instantiation */
template RVecI idx_passingT<float>(const RVec<float>&, std::function<bool(float)>);
template RVecI idx_passingT<int  >(const RVec<int  >&, std::function<bool(int  )>);


/* Same as idx_passingT(), but only on the elements with index in subidxs */
template<class T>
RVecI
idx_passing_subvecT(const RVec<T>& vec, const RVecI& subidxs, std::function<bool(T)> f) {
  RVecI out;
  out.reserve(vec.size());
  for(int i : subidxs) {
    if(f(vec[i]))
      out.push_back(i);
  }
  return out;
}

template RVecI idx_passing_subvecT<float>(const RVec<float>&, const RVecI&, std::function<bool(float)>);
template RVecI idx_passing_subvecT<int  >(const RVec<int  >&, const RVecI&, std::function<bool(int  )>);


/* Special case in which f = [value](int e){ return e==value; } */
RVecI
idx_equal(const RVecI& vec, int value) {
  RVecI out;
  out.reserve(vec.size());

  for(int i = 0; i < (int)vec.size(); ++i) {
    if(vec[i] == value)
      out.push_back(i);
  }
  return out;
}


/* Same, but only consider elements in subidxs */
RVecI
idx_subvec_equal(const RVecI& vec, const RVecI& subidxs, int value) {
  RVecI out;
  out.reserve(vec.size());

  for(int i : subidxs) {
    if(vec[i] == value)
      out.push_back(i);
  }
  return out;
}


/* Reimplemetnation of the jet selection from JetMET, to propagate the JER/JES; see
https://indico.cern.ch/event/1615783/contributions/6811120/attachments/3186812/5672346/20251204_JetMET_PerformanceRun3.pdf */
RVecI
jetPtCut(int year, const RVecF &pts, const RVecF &etas) {
  size_t size = pts.size();
  if(size != etas.size()){
    printf("ERROR:%s: vectors of uneven size: %ld %ld\n", __func__, size, etas.size());
    exit(2);
  }

  RVecI out;
  out.reserve(size);
  for(int i = 0; i < (int)size; ++i){
    float pt   = pts[i];
    float aeta = fabs(etas[i]);
    float pt_cut = 30.f;
    if( (2.5f < aeta && aeta < 3.0f) ||
       ((year == 2022 || year == 2023) && aeta >= 3.0f) )
      pt_cut = 50.f;

    if(pt > pt_cut)
      out.push_back(i);
  }

  return out;
}


template<class T>
RVec<T>
fill_with_indexes(const RVec<T> &src, const RVecI &v_idx) {
  RVec<T> out;

  for(auto &idx : v_idx)
  {
    /* if idx is -1, put an empty object */
    out.push_back(idx >= 0 ? src[idx] : T{});
  }

  return out;
}

template RVec<float> fill_with_indexes<float>(const RVec<float>&, const RVecI&);
template RVec<int  > fill_with_indexes<int  >(const RVec<int  >&, const RVecI&);
template RVec<PtEtaPhiMVector> fill_with_indexes<PtEtaPhiMVector>(const RVec<PtEtaPhiMVector>&, const RVecI&);


/*
   Debug functions that print to stdout the contents of variables.
   To use them, the result value must be used to compute something, e.g. and
   histograms; otherwise the RDF engine will optimize their execution out.
*/
/*
   Warning (AM 2026-04-23): the RDF engine likely does some broken C++ parsing
   and string substitutions, so occurrences of the name of any other parameters
   in a literal string will get translated as well, e.g.
      df.Define('debug1', 'debug_print_vecF(Jet_pt, "Jet_pt")')
   will print something like
      debug vector var0 (0x123456): 51., 42.,
*/
int
debug_print_vecF(const RVecF &vec, const std::string &name) {
  printf("debug vector %s (%p):", name.c_str(), &vec);
  for(auto e : vec)
    printf(" %f,", e);
  printf("\n");
  return 0;
}

int
debug_print_vecI(const RVecI &vec, const std::string &name) {
  printf("debug vector %s (%p):", name.c_str(), &vec);
  for(auto e : vec)
    printf(" %d,", e);
  printf("\n");
  return 0;
}

int
debug_print_F(float v, const std::string &name) {
  printf("debug scalar %s: %f\n", name.c_str(), v);
  return 0;
}

int
debug_print_I(int i, const std::string &name) {
  printf("debug scalar %s: %d\n", name.c_str(), i);
  return 0;
}

int
debug_print_header(unsigned long evtn) {
  printf("######## Event %ld ########\n", evtn);
  return 0;
}
