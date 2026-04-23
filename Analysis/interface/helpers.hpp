#ifndef ZZVBS_HELPERS
#define ZZVBS_HELPERS

#include <functional> /* std::function<> */
#include "ROOT/RVec.hxx"

float
sum_M_mass(float, float, float, float,
	   float, float, float, float);

float
sum_E_mass(float, float, float, float,
	   float, float, float, float);

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

template<class T>
ROOT::VecOps::RVec<T>
fill_with_indexes(const ROOT::VecOps::RVec<T> &src, const ROOT::RVecI &v_idx);

template<class T>
ROOT::VecOps::RVec<T>
concat(const ROOT::VecOps::RVec<T>& lhs, const ROOT::VecOps::RVec<T>& rhs);

int
debug_print_vecF(const ROOT::RVecF &, const std::string&);
int
debug_print_vecI(const ROOT::RVecI &, const std::string&);

int
debug_print_F(float, const std::string&);
#endif
