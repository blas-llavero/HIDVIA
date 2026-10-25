#!/usr/bin/env python3
"""Train an exploratory 7-day flare model on patient-level longitudinal HS data.

Use only consented, de-identified datasets with explicitly recorded flare-onset dates.
The output is experimental and must undergo clinical, temporal and external validation.
Dependencies: pandas, numpy, scikit-learn (see requirements.txt).
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

FEATURES=['pain','itch','swelling','fatigue','stress','sleep','drainage','pain_delta','swelling_delta']

def prepare(source, horizon=7):
    df=pd.read_csv(source)
    required={'patient_id','date','flare_onset',*FEATURES[:7]}
    if missing:=required-set(df.columns): raise ValueError('Missing columns: '+', '.join(sorted(missing)))
    df['date']=pd.to_datetime(df.date,errors='raise',utc=True)
    df=df.sort_values(['patient_id','date']).drop_duplicates(['patient_id','date']).copy()
    for col in FEATURES[:7]:
        df[col]=pd.to_numeric(df[col],errors='raise')
    df['pain_delta']=df.groupby('patient_id').pain.diff().fillna(0).clip(lower=-10,upper=10)
    df['swelling_delta']=df.groupby('patient_id').swelling.diff().fillna(0).clip(lower=-10,upper=10)
    # Labels are strictly events AFTER the current observation through day 7.
    # Drop index dates without future observation coverage to reduce right censoring.
    labels=[];eligible=[]
    for pid,grp in df.groupby('patient_id'):
        last=grp.date.max()
        starts=grp.loc[grp.flare_onset.astype(int)==1,'date']
        for idx,row in grp.iterrows():
            until=row.date+pd.Timedelta(days=horizon)
            covered=until<=last
            event=bool(((starts>row.date)&(starts<=until)).any())
            labels.append((idx,int(event)));eligible.append((idx,bool(covered and int(row.flare_onset)==0)))
    df['y']=pd.Series(dict(labels))
    df['eligible']=pd.Series(dict(eligible))
    return df.loc[df.eligible].dropna(subset=FEATURES).copy()

def train(source,output,horizon=7):
    df=prepare(source,horizon)
    if df.patient_id.nunique()<8:raise ValueError('At least 8 independent patients required for a meaningful demo holdout')
    split=GroupShuffleSplit(n_splits=1,test_size=.25,random_state=42)
    train_ids,test_ids=next(split.split(df[FEATURES],df.y,groups=df.patient_id))
    tr=df.iloc[train_ids];te=df.iloc[test_ids]
    if tr.y.nunique()!=2 or te.y.nunique()!=2:raise ValueError('Both classes are required in train and patient-disjoint test cohorts')
    scaler=StandardScaler().fit(tr[FEATURES])
    clf=LogisticRegression(class_weight='balanced',max_iter=2000,random_state=42)
    clf.fit(scaler.transform(tr[FEATURES]),tr.y)
    pred=clf.predict_proba(scaler.transform(te[FEATURES]))[:,1]
    metrics={'heldout_patients':int(te.patient_id.nunique()),'heldout_records':len(te),'positive_rate':round(float(te.y.mean()),4),
             'auroc':round(float(roc_auc_score(te.y,pred)),4),'average_precision':round(float(average_precision_score(te.y,pred)),4),
             'brier':round(float(brier_score_loss(te.y,pred)),4)}
    artifact={'type':'logistic_regression','status':'EXPERIMENTAL_UNVALIDATED','prediction_horizon_days':horizon,
       'features':FEATURES,'mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),
       'coef':clf.coef_[0].tolist(),'intercept':float(clf.intercept_[0]),'metrics':metrics,
       'trained_utc':datetime.now(timezone.utc).isoformat(),'data_usage':'consented_deidentified_only',
       'limitations':'Not externally validated. Predicted probabilities may be miscalibrated. Not for care decisions.'}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(artifact,indent=2),encoding='utf-8')
    return metrics

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('csv',help='De-identified labelled longitudinal CSV')
    parser.add_argument('--output',default='ml/research_model.json')
    parser.add_argument('--horizon',type=int,default=7)
    args=parser.parse_args();print(json.dumps(train(args.csv,args.output,args.horizon),indent=2))
