#ifndef FAKERATES_H
#define FAKERATES_H

// C++
#include <iostream>
#include <fstream>

// ROOT
#include "TFile.h"
#include "TString.h"
#include "TH1F.h"

using namespace std;

class FakeRates
{

public:
	
  FakeRates(): is_init(false){};
  FakeRates(const TString&);
  ~FakeRates();
  void init(const TString&);

  float getFRval(float pt, float eta, int id) const;
  float getFRerr(float pt, float eta, int id) const;
  std::pair<float, float> getFR(float pt, float eta, int id) const;
  float GetFakeRate(float pt, float eta, int id) const{
    return getFRval(pt, eta, id);
  }

protected:
  const TH1F* get_hist(float eta, int id) const;

private:
  bool is_init;
  TH1F *h_m_EB=nullptr, *h_m_EE=nullptr, *h_e_EB=nullptr, *h_e_EE=nullptr;
};

#endif
