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

ROOT::RVecF
sort_ascending(const ROOT::RVecF &src) {
  ROOT::RVecF out{src};
  std::sort(out.begin(), out.end());
  return out;
}

ROOT::RVecF
sort_descending(const ROOT::RVecF &src) {
  ROOT::RVecF out{src};
  std::sort(out.begin(), out.end(), [](float a, float b){ return a > b; });
  return out;
}

ROOT::RVecF
filter_pdgId(const ROOT::RVecF &v_idx, const ROOT::RVecI &v_id, int id) {
  ROOT::RVecF out;

  for(auto idx : v_idx){
    if(v_id[idx] == id)
      out.push_back(idx);
  }
  return out;
}

ROOT::RVecF
filter_abs_pdgId(const ROOT::RVecF &v_idx, const ROOT::RVecI &v_id, int id) {
  ROOT::RVecF out;

  for(auto &idx : v_idx){
    if(abs(v_id[idx]) == id)
      out.push_back(idx);
  }
  return out;
}

ROOT::RVecF
fill_with_indexes(const ROOT::RVecF &src, const ROOT::RVecI &v_idx) {
  ROOT::RVecF out;

  for(auto &idx : v_idx)
    out.push_back(src[idx]);

  return out;
}
