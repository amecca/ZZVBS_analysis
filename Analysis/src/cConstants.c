#include "math.h"
#include "stdbool.h"
#include "stdlib.h"
#include "cConstants.h"

#ifdef __cplusplus
extern "C" {
#endif

const float PI_FLOAT = 3.14159f;

float getDVBF2jetsConstant(float ZZMass){
   static float par[9] = {
      1.876,
      -55.488,
      403.32,
      0.3906,
      80.8,
      27.7,
      -0.06,
      54.97,
      309.96
   };
   float kappa =
   pow(1.-atan((ZZMass-par[1])/par[2])*2./PI_FLOAT, par[0])
   + par[3]*exp(-pow((ZZMass-par[4])/par[5], 2))
   + par[6]*exp(-pow((ZZMass-par[7])/par[8], 2));
   float constant = kappa/(1.-kappa);
   return constant;
}

float getDVBF1jetConstant(float ZZMass){
   float par[8]={
      0.395,
      -0.07,
      85.,
      30.,
      -0.691,
      -5659.47,
      5734.37,
      0.75
   };
   float kappa =
   par[0]
   + par[1]*exp(-pow((ZZMass-par[2])/par[3], 2))
   + par[4]*pow(log((ZZMass-par[5])/par[6]), par[7])*(ZZMass>=(par[5]+par[6]));
   float constant = kappa/(1.-kappa);
   return constant;
}

float getDWHhConstant(float ZZMass){
   return 1e-3;
}

float getDZHhConstant(float ZZMass){
   return 1e-4;
}

float getDVBF2jetsWP(float ZZMass, bool useQGTagging){
   if (useQGTagging)
      return 0.363;
   else
      return 1.043-460./(ZZMass+634.);
}

float getDVBF1jetWP(float ZZMass, bool useQGTagging){
   if (useQGTagging)
      return 0.716;
   else
      return 0.697;
}

float getDWHhWP(float ZZMass, bool useQGTagging){
   if (useQGTagging)
      return 0.965;
   else
      return 0.951;
}

float getDZHhWP(float ZZMass, bool useQGTagging){
   if (useQGTagging)
      return 0.9952;
   else
      return 0.9937;
}

float getDVBF2jetsConstant_shiftWP(float ZZMass, bool useQGTagging, float newWP) {
   float oldc = getDVBF2jetsConstant(ZZMass);
   float oldWP = getDVBF2jetsWP(ZZMass, useQGTagging);
   return oldc * (oldWP/newWP) * ((1-newWP)/(1-oldWP));
}

float getDVBF1jetConstant_shiftWP(float ZZMass, bool useQGTagging, float newWP) {
   float oldc = getDVBF1jetConstant(ZZMass);
   float oldWP = getDVBF1jetWP(ZZMass, useQGTagging);
   return oldc * (oldWP/newWP) * ((1-newWP)/(1-oldWP));
}

float getDWHhConstant_shiftWP(float ZZMass, bool useQGTagging, float newWP) {
   float oldc = getDWHhConstant(ZZMass);
   float oldWP = getDWHhWP(ZZMass, useQGTagging);
   return oldc * (oldWP/newWP) * ((1-newWP)/(1-oldWP));
}

float getDZHhConstant_shiftWP(float ZZMass, bool useQGTagging, float newWP) {
   float oldc = getDZHhConstant(ZZMass);
   float oldWP = getDZHhWP(ZZMass, useQGTagging);
   return oldc * (oldWP/newWP) * ((1-newWP)/(1-oldWP));
}


float getDbkgkinConstant(int ZZflav, float ZZMass){ // ZZflav==id1*id2*id3*id4
   float par[14]={
      0.775,
      -0.565,
      70.,
      5.90,
      -0.235,
      130.1,
      13.25,
      -0.33,
      191.04,
      16.05,
      187.47,
      -0.21,
      1700.,
      400.
   };
   if (abs(ZZflav)==121*121 || abs(ZZflav)==121*242 || abs(ZZflav)==242*242) par[11]=-0.42; // 4e
   float kappa =
   par[0]
   +par[1]*exp(-pow(((ZZMass-par[2])/par[3]), 2))
   +par[4]*exp(-pow(((ZZMass-par[5])/par[6]), 2))
   +par[7]*(
            exp(-pow(((ZZMass-par[8])/par[9]), 2))*(ZZMass<par[8])
            + exp(-pow(((ZZMass-par[8])/par[10]), 2))*(ZZMass>=par[8])
            )
   + par[11]*exp(-pow(((ZZMass-par[12])/par[13]), 2));
   
   float constant = kappa/(1.-kappa);
   return constant;
}

float getDbkgConstant(int ZZflav, float ZZMass){
   return getDbkgkinConstant(ZZflav, ZZMass);
}

enum FSLFO get_FSLFO(int Z1Flav, int Z2Flav){
  enum FSLFO r = FSLFO_INVALID;
  int c1 = 0;
  switch(abs(Z1Flav)){
  case 121: c1 = 1; break;
  case 169: c1 = 2; break;
  default: return r;
  }
  switch(abs(Z2Flav)){
  case 121: r = (c1==1 ? FSLFO_4e : FSLFO_2mu2e); break;
  case 169: r = (c1==1 ? FSLFO_2mu2e: FSLFO_4mu); break;
  default: return r;
  }
  return r;
}

float get_fs_ROS_SS(enum FSLFO c){
  if(c == FSLFO_4mu  ) return 1.04;
  if(c == FSLFO_4e   ) return 1.01;
  if(c == FSLFO_2e2mu) return 1.04;
  if(c == FSLFO_2mu2e) return 1.00;
  return 1.;
}

#ifdef __cplusplus
} /* extern "C" */
#endif
