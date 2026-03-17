// Include classes
#include "TGraphErrors.h"

#include "FakeRates.hpp"

// Helper
TH1F* _h_from_tge(const TGraphErrors&, bool debug);


// Constructor
//===============================================
FakeRates::FakeRates(const char *input_file_FR_name, const char *method, bool debug)
  : _is_init(false), _debug(debug)
{
  init(input_file_FR_name, method);
}


FakeRates::~FakeRates(){}


// Inititalization
void FakeRates::init(const char *input_file_FR_name, const char *method){
  auto input_file_FR = TFile::Open(input_file_FR_name);
  if(!input_file_FR->IsOpen()){
    fprintf(stderr, "ERROR FakeRates: cannot open \"%s\"\n", input_file_FR->GetName());
    delete input_file_FR;
    return;
  }

  // for Christophe's FR files
  auto g_m_EB = (TGraphErrors*)input_file_FR->Get(Form("FR_%s_muon_EB"    , method));
  auto g_m_EE = (TGraphErrors*)input_file_FR->Get(Form("FR_%s_muon_EE"    , method));
  auto g_e_EB = (TGraphErrors*)input_file_FR->Get(Form("FR_%s_electron_EB", method));
  auto g_e_EE = (TGraphErrors*)input_file_FR->Get(Form("FR_%s_electron_EE", method));

  if(g_m_EB == nullptr){ fprintf(stderr, "ERROR:%s:%s: could not get TGE for muon EB\n"    , __FILE__, __func__); return; }
  if(g_m_EE == nullptr){ fprintf(stderr, "ERROR:%s:%s: could not get TGE for muon EE\n"    , __FILE__, __func__); return; }
  if(g_e_EB == nullptr){ fprintf(stderr, "ERROR:%s:%s: could not get TGE for electron EB\n", __FILE__, __func__); return; }
  if(g_e_EE == nullptr){ fprintf(stderr, "ERROR:%s:%s: could not get TGE for electron EE\n", __FILE__, __func__); return; }

  h_m_EB = _h_from_tge(*g_m_EB, _debug);
  h_m_EE = _h_from_tge(*g_m_EE, _debug);
  h_e_EB = _h_from_tge(*g_e_EB, _debug);
  h_e_EE = _h_from_tge(*g_e_EE, _debug);

  input_file_FR->Close();
  delete input_file_FR;

  _is_init = true;
}
//===============================================



//==================================================================
float FakeRates::getFRval(float pt, float eta, int id) const{
  return getFR(pt, eta, id).first;
}

float FakeRates::getFRerr(float pt, float eta, int id) const{
  return getFR(pt, eta, id).second;
}

std::pair<float, float> FakeRates::getFR(float pt, float eta, int id) const{
  const TH1F* h = get_hist(eta, id);
  if(!h)
    return std::make_pair(1., 0.);

  int b = h->FindFixBin(pt);
  float v = h->GetBinContent(b);
  float e = h->GetBinError  (b);
  return std::make_pair(v, e);
}

const TH1F* FakeRates::get_hist(float eta, int id) const{
  TH1F* h = nullptr;
  if(!_is_init) return h;
  unsigned int aid = abs(id);
  float aeta = fabs(eta);

  switch(aid){
  case 11:
    h = (aeta < 1.479 ? h_e_EB : h_e_EE);
    break;
  case 13:
    h = (aeta < 1.2   ? h_m_EB : h_m_EE);
    break;
  default:
    fprintf(stderr, "ERROR: unknown lepton id: %d\n", id);
  }
  return h;
}


TH1F* _h_from_tge(const TGraphErrors& g, bool debug){
  /* Helper function that creates a TH1F based on a TGraphErrors,
   with N+1 bins and the correct bin content and error*/
  int n = g.GetN();
  std::vector<float> edges;  edges .reserve(n+1);
  std::vector<float> values; values.reserve(n+1);
  std::vector<float> errors; errors.reserve(n+1);
  if(debug)
    fprintf(stderr, "DEBUG (h_from_tge): converting %s (%d points)\n", g.GetName(), n);

  for(int i=0; i<n; ++i){
    float px = g.GetPointX(i);
    float py = g.GetPointY(i);
    float ex = g.GetErrorX(i);
    float ey = g.GetErrorY(i);

    float px_ex = px - ex;
    if(i > 0){
      // Check edge consistency with point errors
      float last = edges.back();
      if(px_ex - last > 1e-7)
	fprintf(stderr, "WARN (h_from_tge): edge discrepancy: last=%.3e, x-ex=%.3e (diff=%.3e)\n", last, px_ex, px_ex-last);
    }
    else // first bin
      edges.push_back(px_ex);
    edges.push_back(px + ex);
    values.push_back(py);
    errors.push_back(ey);
  }

  // allocate on the heap the result
  TH1F* hp = new TH1F(g.GetName(), g.GetTitle(), n, edges.data());
  TH1F& h = *hp; // for convenience

  h.SetDirectory(0); // ROOT deletes TH1 objects created while a TFile is open, when closing it
  for(int i=0; i<n; ++i){
    // fprintf(stderr, "DEBUG: %d - y = %.3g +- %.3g\n", i+1, v, e)
    h.SetBinContent(i+1, values.at(i));
    h.SetBinError  (i+1, errors.at(i));
  }
  // Set the under/overflow value and error equal to the first/last bin - simplifies getFR
  h.SetBinContent(0, values.front());
  h.SetBinError  (0, errors.front());
  h.SetBinContent(n+1, values.back());
  h.SetBinError  (n+1, errors.back());

  if(debug)
    fprintf(stderr, "DEBUG (h_from_tge): returning new TH1F 0x%p (%i bins)\n", hp, hp->GetNbinsX());
  return hp;
}
