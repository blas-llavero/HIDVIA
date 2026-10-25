#!/usr/bin/env python3
"""Read-only challenge dataset inventory; emits schemas/counts, NEVER patient-level rows.

Scan local files and archives. ZIP members remain in memory; path traversal is never extracted.
Only pass data approved for research. Do NOT commit partner files or the report if filenames sensitive.
"""
from __future__ import annotations
import argparse
from collections import Counter
import io
import json
from pathlib import Path
import re
import zipfile

TABULAR={'.csv','.tsv','.xlsx','.xls','.json','.parquet'}
IMAGES={'.png','.jpg','.jpeg','.webp','.tiff','.dcm'}
LABELS=('flare','onset','relapse','recurrence','exacerb','outcome','hisi','sartorius','severity','hurley')
PATIENT=('patient','subject','participant','individual','case_id')
DATE=('date','visit','time','timestamp','day','week')
MOLECULAR=('rna','gene','expression','transcript','seq','biomarker','cytokine','protein')

def classify(cols):
    cols=[str(x).strip().lower() for x in cols]
    return {"outcome_candidates":[x for x in cols if any(w in x for w in LABELS)],
            "patient_id_candidates":[x for x in cols if any(w in x for w in PATIENT)],
            "temporal_candidates":[x for x in cols if any(w in x for w in DATE)],
            "molecular_candidates":[x for x in cols if any(w in x for w in MOLECULAR)]}

def table_audit(filename, opener):
    suffix=Path(filename).suffix.lower();result={'file':filename,'type':suffix.lstrip('.')}
    try:
        import pandas as pd
        if suffix in ('.csv','.tsv'):
            # Limit memory; only read header + at most 2000 rows; no row content in report.
            data=pd.read_csv(opener(),sep='\t' if suffix=='.tsv' else ',',nrows=2000,low_memory=False)
        elif suffix in ('.xlsx','.xls'):
            data=pd.read_excel(opener(),nrows=2000)
        elif suffix=='.parquet':data=pd.read_parquet(opener()).head(2000)
        elif suffix=='.json':
            obj=json.load(opener());data=pd.json_normalize(obj if isinstance(obj,list) else [obj]).head(2000)
        else:return result
        cols=[str(c) for c in data.columns]
        result.update({'sample_rows_read':len(data),'columns':cols,'signals':classify(cols),
          'missing_percent_sample':{c:round(float(data[c].isna().mean())*100,1) for c in cols[:100]}})
    except Exception as exc:result['parse_error']=type(exc).__name__+': '+str(exc)[:130]
    return result

def inspect(path):
    p=Path(path)
    files=[p] if p.is_file() else [f for f in p.rglob('*') if f.is_file()]
    entries=[];counts=Counter();scanned=0
    for f in sorted(files):
        if zipfile.is_zipfile(f):
            with zipfile.ZipFile(f) as archive:
                for item in archive.infolist():
                    if item.is_dir() or item.file_size>250_000_000:continue
                    name=f.name+'!'+item.filename
                    suffix=Path(name).suffix.lower();counts[suffix]+=1
                    if suffix in TABULAR:
                        try:entries.append(table_audit(name,lambda i=item:io.BytesIO(archive.read(i))))
                        except Exception as exc:entries.append({'file':name,'parse_error':str(exc)[:120]})
                    scanned+=1
        else:
            suffix=f.suffix.lower();counts[suffix]+=1
            if suffix in TABULAR:entries.append(table_audit(str(f.relative_to(p) if p.is_dir() else f.name),lambda f=f:open(f,'rb')))
            scanned+=1
    suitable=[]
    for e in entries:
        signals=e.get('signals',{})
        if signals.get('outcome_candidates') and signals.get('patient_id_candidates') and signals.get('temporal_candidates'):
            suitable.append(e['file'])
    return {'status':'SCHEMA_AUDIT_ONLY_NOT_VALIDATION','files_count':scanned,'extensions':dict(counts),
      'image_files':sum(n for suffix,n in counts.items() if suffix in IMAGES),
      'tables':entries,'prospective_flare_training_candidates':suitable,
      'caveats':['Column names are only hints; labels must be clinically adjudicated.',
      'Cross-sectional clinical, imaging and RNA data do not automatically support future-flare forecasting.',
      'Train/test separation must be by patient/site/time, with no post-outcome features.',
      'File inventory is not evidence of clinical utility, device compatibility or model validity.']}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path',help='Dataset directory, ZIP or single table; does not extract or modify anything')
    parser.add_argument('--output',default='ml/challenge_schema_report.json')
    args=parser.parse_args();report=inspect(args.path)
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'Schema report: {out} | {report["files_count"]} files, {len(report["tables"])} tables; no clinical validation performed.')
