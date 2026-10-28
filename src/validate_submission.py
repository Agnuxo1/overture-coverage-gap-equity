"""Validate the exact scored-ID contract before any official upload."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd


def validate(submission, sample):
    sub=pd.read_csv(submission,dtype={'GEOID':str})
    template=pd.read_csv(sample,dtype={'GEOID':str})
    if 'GEOID' not in sub or 'GEOID' not in template:
        raise ValueError('Both files must contain GEOID')
    expected=set(template.GEOID.dropna());actual=set(sub.GEOID.dropna())
    missing=sorted(expected-actual);extra=sorted(actual-expected)
    columns=[c for c in sub if c!='GEOID']
    scores=sub[columns].apply(pd.to_numeric,errors='coerce').to_numpy()
    finite=bool(np.isfinite(scores).all())
    bounded=bool(finite and ((scores>=0)&(scores<=1)).all())
    duplicates=int(sub.GEOID.duplicated().sum())
    ids_valid=bool(sub.GEOID.notna().all() and sub.GEOID.str.fullmatch(r'\d{11}').all())
    template_valid=bool(len(template)>0 and template.GEOID.notna().all()
                        and template.GEOID.str.fullmatch(r'\d{11}').all()
                        and not template.GEOID.duplicated().any())
    ok=(template_valid and not missing and not extra and not duplicates and ids_valid and bounded
        and 'coverage_gap_score' in columns)
    return {'passed':bool(ok),'submission_rows':len(sub),'sample_rows':len(template),
            'missing_count':len(missing),'missing_first5':missing[:5],
            'extra_count':len(extra),'extra_first5':extra[:5],
            'duplicate_ids':duplicates,'id_format_valid':ids_valid,
            'scores_finite':finite,'scores_in_range':bounded,'template_valid':template_valid,
            'note':'A structural gate, not a performance score or platform receipt.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--submission',type=Path,required=True)
    p.add_argument('--sample',type=Path,required=True)
    a=p.parse_args();r=validate(a.submission,a.sample)
    print(json.dumps(r,indent=2));raise SystemExit(0 if r['passed'] else 2)


if __name__=='__main__':main()
