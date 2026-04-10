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


int
debug_print_vecF(const ROOT::RVecF &vec, int name){
  for(size_t i = 0; i < vec.size(); ++i)
    printf("debug %d (%p): %ld: %f\n", name, &vec, i, vec[i]);
  return 0;
}

int
debug_print_vecI(const ROOT::RVecI &vec, int name){
  for(size_t i = 0; i < vec.size(); ++i)
    printf("debug %d (%p): %ld: %d\n", name, &vec, i, vec[i]);
  return 0;
}

int
debug_print_F(float v, int name){
  printf("debug %d: %f\n", name, v);
  return 0;
}
