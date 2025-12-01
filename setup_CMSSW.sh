#!/bin/sh

###########################################################
# Creates a CMSSW environment and sets up VBSZZ_analysis  #
#                                                         #
# Author: A. Mecca (alberto.mecca@cern.ch)                #
###########################################################

set -e
set -u

CMSSW_VERSION=CMSSW_14_1_6
branch_ZZ=Run3
branch=${1:-master}
repo_name=amecca/ZZVBS_analysis.git
checkoutscript=checkout_13X.csh

# Create the CMSSW area
cmsrel ${CMSSW_VERSION}

# Fetch the ZZAnalysis setup script
wget -O ${checkoutscript} https://raw.githubusercontent.com/CJLST/ZZAnalysis/${branch_ZZ}/${checkoutscript}
chmod u+x ${checkoutscript}

# Move to ${CMSSW_BASE}/src and cmsenv
cd ${CMSSW_VERSION}/src
cmsenv

# Execute the ZZAnalysis setup script
../../${checkoutscript}

# Clone ZZ VBS Analysis (try with ssh key, then with plain https)
git clone -b ${branch} ssh://git@gitlab.cern.ch:7999/${repo_name} || git clone -b ${branch} https://gitlab.cern.ch/${repo_name}

# Compile with SCRAM
scram b -j

# Install python requirements (cmsstyle)
python3 -m pip install --user -r ZZVBS_analysis/requirements.txt
