#ifndef ZZVBS_HELPERS
#define ZZVBS_HELPERS

#include <functional> /* std::function<> */
#include "ROOT/RVec.hxx"
#include <Math/Vector4D.h>


float
sum_M_mass(float, float, float, float,
	   float, float, float, float);

float
sum_E_mass(float, float, float, float,
	   float, float, float, float);

ROOT::Math::PtEtaPhiMVector
sum4_M(float pt1, float eta1, float phi1, float m1,
       float pt2, float eta2, float phi2, float m2,
       float pt3, float eta3, float phi3, float m3,
       float pt4, float eta4, float phi4, float m4);

/* Get the indexes of elements passing a condition */
template<class T>
ROOT::RVecI
idx_passingT(const ROOT::VecOps::RVec<T>& vec, std::function<bool(T)>);

/* Same, but consider only elements with index in subidxs */
template<class T>
ROOT::RVecI
idx_passing_subvecT(const ROOT::VecOps::RVec<T>& vec, const ROOT::RVecI& subidxs, std::function<bool(T)> f);

/* Get the indexes of elements equal to a value */
ROOT::RVecI
idx_equal(const ROOT::RVecI& vec, int value);

/* Same, in a subvector of indexes */
ROOT::RVecI
idx_subvec_equal(const ROOT::RVecI& vec, const ROOT::RVecI& subidxs, int value);

ROOT::RVecI
jetPtCut(int year, const ROOT::RVecF &pts, const ROOT::RVecF &etas);

/* Could be replace by ROOT::VecOps::Take(), except that this deals well
   with indexes < 0, by invoking the default constructor */
template<class T>
ROOT::VecOps::RVec<T>
fill_with_indexes(const ROOT::VecOps::RVec<T> &src, const ROOT::RVecI &v_idx);

ROOT::RVecF
fix_SFuncert(const ROOT::RVecF &eff, const ROOT::RVecF &unc);

int
debug_print_vecF(const ROOT::RVecF &, const std::string&);
int
debug_print_vecI(const ROOT::RVecI &, const std::string&);

int
debug_print_F(float, const std::string&);
#endif
