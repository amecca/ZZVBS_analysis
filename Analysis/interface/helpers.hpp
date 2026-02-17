#ifndef ZZVBS_HELPERS
#define ZZVBS_HELPERS

#include "ROOT/RVec.hxx"

float
sum_M_mass(float, float, float, float,
	   float, float, float, float);

float
sum_E_mass(float, float, float, float,
	   float, float, float, float);

ROOT::RVecF
sort_ascending(const ROOT::RVecF &src);

ROOT::RVecF
sort_descending(const ROOT::RVecF &src);

ROOT::RVecF
filter_pdgId(const ROOT::RVecF &v_idx, const ROOT::RVecI &v_id, int id);

ROOT::RVecF
filter_abs_pdgId(const ROOT::RVecF &v_idx, const ROOT::RVecI &v_id, int id);

ROOT::RVecF
fill_with_indexes(const ROOT::RVecF &src, const ROOT::RVecI &v_idx);
#endif
