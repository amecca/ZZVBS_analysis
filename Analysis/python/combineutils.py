import pandas as pd
import logging


def get_syst_type(syst, conf_syst):
    if  (syst in conf_syst.get('shape', [])):
        return 'shape'
    elif(syst in conf_syst.get('gmN'  , [])):
        return 'gmN'
    else:
        return 'lnN'


def get_shape_uncorrelated(conf_syst):
    # Some systematics are:
    # - uncorrelated: they must be separated by year -> "<SYS>_201*";
    # - shape: there must be two histograms in the rootfile with the exact same name + "Up/Down".
    # However, the EventAnalyzer should not itself decide if a systematic is or not uncorrelated,
    # so the year suffix should not be decided there. Rather, we modify the histograms' names when preparing them for Combine.
    return {syst for syst in conf_syst['uncorrelated'] if get_syst_type(syst, conf_syst) == 'shape'}


def get_shape_correlyear(conf_syst):
    # Mainly for CMS_pileup
    return {syst for syst in conf_syst['correl_year'] if get_syst_type(syst, conf_syst) == 'shape'}


def get_shape_groups(conf_syst):
    # Some systematics are:
    # - shape: there must be two histograms in the rootfile with the exact same name + "Up/Down".
    # - correlated within a group of samples: e.g. QCDscale_VV for ZZ and WZ
    # - correlated between years
    # However, the EventAnalyzer should not itself decide if a systematic is or not uncorrelated,
    # so the year suffix should not be decided there. Rather, we modify the histograms' names when preparing them for Combine.
    return {syst for syst in conf_syst['split-by-sample-group'] if get_syst_type(syst, conf_syst) == 'shape'}


def get_sample_group(sample, syst):
    '''
    Return the name of a group of processes for a given sample name and systematic
    (e.g. ZZTo4l -> VV for QCDscale, but ZZTo4l -> qq for pdf)
    '''
    if  (syst == 'QCDscale'):
        return get_sample_group_QCDscale(sample)
    elif(syst == 'pdf'):
        return get_sample_group_pdf(sample)
    else:
        raise KeyError('Don\'t know how to assign a group to systematic "%s"' %(syst))

def get_sample_group_pdf(sample):
    # NOTE: ggTo* samples have NO PDF uncertainty stored in the ntuples! So pdf_gg ALWAYS gets cancelled
    if  (sample.startswith(('ggTo4e', 'ggTo2e2m', 'ggTo4m'))):
        return 'gg'
    else:
        return 'qqbar'

def get_sample_group_QCDscale(sample):
    logging.warning('TODO: adapt to sample nice names')
    if  (sample.startswith(('ZZGTo4LG','WZGTo3LNuG','ZZGTo2L2jG','WZGTo2L2jG', 'signal'))):
        return 'VVgamma'
    elif(sample.startswith(('ZZZ', 'WZZ', 'WWZ', 'WWW'))):
        return 'VVV'
    elif(sample.startswith(('ZZTo','WZTo','WWTo'))):
        return 'VV'
    elif(sample.startswith(('ggTo4e', 'ggTo2e2m', 'ggTo4m'))):
        return 'ggVV'
    elif(sample.startswith(('TTW', 'TTZ'))):
        return 'ttV'
    elif(sample.startswith(('TTTo',))):
        return 'ttbar'
    elif(sample.startswith(('TZq','tW'))):
        return 'tV'
    elif(sample.startswith(('ZGToLLG', 'fake_photons'))):
        return 'Vgamma'
    elif(sample.startswith('DY')):
        return 'V'
    elif(sample.startswith('ZH')):
        return 'VH'
    elif(sample.startswith('fake')):
        return None
    else:
        raise KeyError('Sample "%s" has no group' %(sample))


def get_syst_corrtype(syst, conf_syst):
    if(syst == 'nominal'): return None
    for ct in ('uncorrelated', 'correl_year', 'correlated'):
        if(syst in conf_syst[ct]): return ct
    else:
        raise TypeError('Correlation type unspecified for "%s"' %(syst))


# This helper is used to decide the name of histograms in Combine input, and
# also the entries in the syst table in datacards
class SystNameHelper:
    def __init__(self, name, conf_syst):
        # conf_syst = config["systematics"]
        if(name == 'central'): raise RuntimeError()

        self.name = name
        self.type_ = get_syst_type(self.name, conf_syst)
        self.corrtype = get_syst_corrtype(self.name, conf_syst)
        self.do_group = self.name in conf_syst['split-by-sample-group']
        logging.debug('SystNameHelper: %s', vars(self))

    def outname(self, sample, year):
        out = self.name
        if(self.name == 'nominal'): return out

        if(self.do_group):
            out += "_"+get_sample_group(sample, syst=self.name)

        if  (self.corrtype == 'uncorrelated'):
            out += "_"+year
        elif(self.corrtype == 'correl_year'):
            out += "_%d"%(int(year[:4]))
        elif(self.corrtype == 'correl_era'):
            year_int = int(year[:4])
            if(2015 <= year_int <= 2018): out += '_13TeV'
            elif(year_int <= 2026):       out += '_13p6TeV'
        elif(self.corrtype == 'correlated'):
            pass
        else: raise TypeError('Unknown correlation type "%s"' %(self.corrtype))

        return out


class SystHelperCache(dict):
    def __init__(self, config):
        self.config = config

    def get_or_make(self, syst):
        if syst not in self.keys():
            self[syst] = SystNameHelper(syst, self.config)
        return self[syst]


def formatUpDn(value, fmt='%+2.2f'):
    if   all(abs(v) < 1e-4 for v in [value['up'], value['dn']]):
        return '-'
    else:
        return (fmt+'/'+fmt) %(value['up']*100, value['dn']*100)  # For slides or AN


def fillDataFrame(raw_data, formatter=formatUpDn, fmt='%+2.2f'):
    # "Unpack" the inner dictionary {'up':x.xx, 'dn':x.xx} into a string
    data = { sample:
             { syst: formatter(value, fmt=fmt) for syst, value in d.items() }
             for sample, d in raw_data.items() }

    # Use pandas for pretty formatting
    return pd.DataFrame.from_dict(data) #, orient='index')
