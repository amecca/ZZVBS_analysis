### Setup

Compile the C/C++ code into shared libraries using `make`.

### Running the analysis

The starting point are CJLST-processed NanoAODs, produced either with
[runLocal.py](https://github.com/CJLST/ZZAnalysis/blob/Run3/NanoAnalysis/test/runLocal.py)
or from a full production with
[HTCondor](https://github.com/CJLST/ZZAnalysis/blob/Run3/AnalysisStep/scripts/batch_Condor.py).

They can be processed with `nano2hists.py` into ROOT files containing histograms.
This script uses [RDataFrame](https://root.cern/doc/master/classROOT_1_1RDataFrame.html).
C/C++ code can be compiled into a shared library and called inside RDF functions,
after loading the .so with the ROOT interpreter.

The histograms can be used by `plot_dataMC.py` to produce some standard
[cmsstyle](https://github.com/CJLST/ZZAnalysis/blob/Run3/Analysis/scripts/batch_Condor.py)-compliant
images (PDF and PNG) containing the MC stack, data points and ratio plot.
Alternatively, `compare_plots.py` can be used to compare only two sets of files, whose
histograms are first hadd-ed together.

All the python scripts use [argparse](https://docs.python.org/3/library/argparse.html),
so the options they accept can be shown by running them with the `-h` flag.
