"""Prepare three prespecified candidates on permitted cached features; no target labels.

CSV generation and structural checks are NOT an official performance experiment.
Only accepted submissions and the organiser metric can assess RMSE improvement.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from model import PARAMS, REGIONS, STRATA_COLS, predict, write_submission


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data',type=Path,required=True,help='Permitted features/ and strata/ cache')
    ap.add_argument('--out',type=Path,default=Path('submissions/interventions'))
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    fs=[];ss=[];hashes={}
    for r in REGIONS:
        for folder,dest in [('features',fs),('strata',ss)]:
            path=a.data/folder/(r+'.parquet')
            hashes[f'{folder}/{r}.parquet']=hashlib.sha256(path.read_bytes()).hexdigest()
            dest.append(pd.read_parquet(path))
    f=pd.concat(fs,ignore_index=True).merge(pd.concat(ss,ignore_index=True)[STRATA_COLS],
                                          on='GEOID',how='left',validate='one_to_one')
    if f.pop_total.isna().any():raise ValueError('Missing strata join')
    cases={
      'E001_control':{},
      'E003_building_prior005':{'bld_base':.05},
      'E004_road_leak030':{'road_tertiary_leak':.30},
      'E005_building_prior000':{'bld_base':0.0},
    }
    base=predict(f,dict(PARAMS));rec=[]
    for name,change in cases.items():
        p={**PARAMS,**change};out=predict(f,p);path=a.out/(name+'.csv')
        sub=write_submission(out,path)
        cols=['transport_gap','building_gap','poi_gap','coverage_gap_score']
        values=sub[cols].to_numpy()
        assert np.isfinite(values).all() and ((values>=0)&(values<=1)).all()
        delta=out.coverage_gap_score-base.coverage_gap_score
        rec.append({'candidate':name,'isolated_change':change,'rows':len(sub),
                    'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'changed_tracts':int((delta.abs()>1e-12).sum()),
                    'mean_score_delta':float(delta.mean()),
                    'min_score_delta':float(delta.min()),'max_score_delta':float(delta.max()),
                    'official_submission_id':None,'official_rmse':None})
    report={'stage':'prepared_not_submitted_or_scored',
            'diagnostic_missing_buildings_with_acs_housing':int(((f.ov_bld==0)&(f.housing_units>0)).sum()),
            'discarded_E002':'No affected tract; do not upload a duplicate control. ACS is not used as a replacement building-count denominator.',
            'prepared_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'data_sources':'Only current permitted Overture/ACS/strata caches; no withdrawn reference layers',
            'input_hashes':hashes,'candidates':rec,
            'selection_rule':'Compare accepted official RMSE against E001; preserve every result. No local accuracy claim without organiser labels. Check quotas and rules before each upload.'}
    (a.out/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
