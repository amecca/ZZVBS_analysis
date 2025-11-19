#ifndef CCONSTANTS_H
#define CCONSTANTS_H

#ifdef __cplusplus
extern "C" {
#endif

float getDVBF2jetsConstant(float ZZMass);
float getDVBF1jetConstant(float ZZMass);
float getDWHhConstant(float ZZMass);
float getDZHhConstant(float ZZMass);

float getDVBF2jetsWP(float ZZMass, bool useQGTagging);
float getDVBF1jetWP(float ZZMass, bool useQGTagging);
float getDWHhWP(float ZZMass, bool useQGTagging);
float getDZHhWP(float ZZMass, bool useQGTagging);

float getDVBF2jetsConstant_shiftWP(float ZZMass, bool useQGTagging, float newWP);
float getDVBF1jetConstant_shiftWP(float ZZMass, bool useQGTagging, float newWP);
float getDWHhConstant_shiftWP(float ZZMass, bool useQGTagging, float newWP);
float getDZHhConstant_shiftWP(float ZZMass, bool useQGTagging, float newWP);

float getDbkgkinConstant(int ZZflav, float ZZMass);
float getDbkgConstant(int ZZflav, float ZZMass);

enum FSLFO {
    /* Lepton flavour with order (i.e. 2e2m != 2m2e) in the final state */
    FSLFO_INVALID = -1,
    FSLFO_4e    = 0,
    FSLFO_4mu   = 1,
    FSLFO_2e2mu = 2,
    FSLFO_2mu2e = 3,
    FSLFO_4l    = 4,
    FSLFO_MAX
  };

/* Get the Final State in terms of Lepton Flavour (with order, i.e. 2e2mu != 2mu2m)*/
enum FSLFO get_FSLFO(int Z1Flav, int Z2Flav);
float get_fs_ROS_SS(enum FSLFO f);

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif
