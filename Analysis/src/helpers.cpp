#include "helpers.hpp"
#include <Math/Vector4D.h>

using ROOT::Math::PtEtaPhiMVector;
using ROOT::Math::PtEtaPhiEVector;


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


/* Get the indexes of elements passing a cut */
template<class T>
ROOT::RVecI
idx_passingT(const ROOT::VecOps::RVec<T>& vec, std::function<bool(T)> f) {
  ROOT::RVecI out;
  out.reserve(vec.size());
  for(int i = 0; i < (int)vec.size(); ++i) {
    if(f(vec[i]))
      out.push_back(i);
  }
  return out;
}

/* explicit template instantiation */
template ROOT::RVecI idx_passingT<float>(const ROOT::VecOps::RVec<float>&, std::function<bool(float)>);
template ROOT::RVecI idx_passingT<int  >(const ROOT::VecOps::RVec<int  >&, std::function<bool(int  )>);


/* Same as idx_passingT(), but only on the elements with index in subidxs */
template<class T>
ROOT::RVecI
idx_passing_subvecT(const ROOT::VecOps::RVec<T>& vec, const ROOT::RVecI& subidxs, std::function<bool(T)> f) {
  ROOT::RVecI out;
  out.reserve(vec.size());
  for(int i : subidxs) {
    if(f(vec[i]))
      out.push_back(i);
  }
  return out;
}

template ROOT::RVecI idx_passing_subvecT<float>(const ROOT::VecOps::RVec<float>&, const ROOT::RVecI&, std::function<bool(float)>);
template ROOT::RVecI idx_passing_subvecT<int  >(const ROOT::VecOps::RVec<int  >&, const ROOT::RVecI&, std::function<bool(int  )>);


/* Special case in which f = [value](int e){ return e==value; } */
ROOT::RVecI
idx_equal(const ROOT::RVecI& vec, int value) {
  ROOT::RVecI out;
  out.reserve(vec.size());

  for(int i = 0; i < (int)vec.size(); ++i) {
    if(vec[i] == value)
      out.push_back(i);
  }
  return out;
}


/* Same, but only consider elements in subidxs */
ROOT::RVecI
idx_subvec_equal(const ROOT::RVecI& vec, const ROOT::RVecI& subidxs, int value) {
  ROOT::RVecI out;
  out.reserve(vec.size());

  for(int i : subidxs) {
    if(vec[i] == value)
      out.push_back(i);
  }
  return out;
}


/* Reimplemetnation of the jet selection from JetMET, to propagate the JER/JES; see
https://indico.cern.ch/event/1615783/contributions/6811120/attachments/3186812/5672346/20251204_JetMET_PerformanceRun3.pdf */
ROOT::RVecI
jetPtCut(int year, const ROOT::RVecF &pts, const ROOT::RVecF &etas) {
  size_t size = pts.size();
  if(size != etas.size()){
    printf("ERROR:%s: vectors of uneven size: %ld %ld\n", __func__, size, etas.size());
    exit(2);
  }

  ROOT::RVecI out;
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
ROOT::VecOps::RVec<T>
fill_with_indexes(const ROOT::VecOps::RVec<T> &src, const ROOT::RVecI &v_idx) {
  ROOT::VecOps::RVec<T> out;

  for(auto &idx : v_idx)
  {
    out.push_back(src[idx]);
  }

  return out;
}

template ROOT::VecOps::RVec<float> fill_with_indexes<float>(const ROOT::VecOps::RVec<float>&, const ROOT::RVecI&);
template ROOT::VecOps::RVec<int  > fill_with_indexes<int  >(const ROOT::VecOps::RVec<int  >&, const ROOT::RVecI&);


template<class T>
ROOT::VecOps::RVec<T>
concat(const ROOT::VecOps::RVec<T>& lhs, const ROOT::VecOps::RVec<T>& rhs) {
  auto out {lhs};
  out.append(rhs.begin(), rhs.end());
  return out;
}

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
debug_print_vecF(const ROOT::RVecF &vec, const std::string &name) {
  printf("debug vector %s (%p):", name.c_str(), &vec);
  for(auto e : vec)
    printf(" %f,", e);
  printf("\n");
  return 0;
}

int
debug_print_vecI(const ROOT::RVecI &vec, const std::string &name) {
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
