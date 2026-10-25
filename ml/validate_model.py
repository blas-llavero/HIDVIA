#!/usr/bin/env python3
"""Evaluate an ALREADY trained experimental logistic model on a separate labelled cohort.
Does not assert external validation without independent cohort provenance.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss,confusion_matrix
try:
    from .train_model import FEATURES,prepare
except ImportError:
    from train_model import FEATURES,prepare

def evaluate(data_csv,model_json,horizon=7,threshold=.5):
    model=json.loads(Path(model_json).read_text())
    if model.get('features')!=FEATURES or model.get('status')!='EXPERIMENTAL_UNVALIDATED':
        raise ValueError('Model metadata mismatch; cannot validate on this model.')
    if model.get('prediction_horizon_days')!=horizon:raise ValueError('Model horizon differs from evaluation horizon')
    df=prepare(data_csv,horizon)
    if df.empty or df.patient_id.nunique()<2 or df.y.nunique()!=2:
        raise ValueError('Insufficient outcome events/patients for evaluation; validation blocked')
    mean=np.asarray(model['mean']);scale=np.maximum(np.asarray(model['scale']),1e-9)
    z=model['intercept']+((df[FEATURES].to_numpy()-mean)/scale)@np.asarray(model['coef'])
    prob=1/(1+np.exp(-np.clip(z,-40,40)))
    true=df.y.to_numpy();pred=(prob>=threshold).astype(int)
    tn,fp,fn,tp=confusion_matrix(true,pred,labels=[0,1]).ravel()
    report={'status':'RESEARCH_EVALUATION_ONLY','test_data':str(data_csv),'patients':int(df.patient_id.nunique()),
      'records':len(df),'flare_onsets_future_7d':int(true.sum()),'prevalence':float(true.mean()),
      'auroc':float(roc_auc_score(true,prob)),'average_precision':float(average_precision_score(true,prob)),
      'brier':float(brier_score_loss(true,prob)),'decision_threshold':threshold,
      'sensitivity':float(tp/(tp+fn)) if tp+fn else None,
      'specificity':float(tn/(tn+fp)) if tn+fp else None,
      'positive_predictive_value':float(tp/(tp+fp)) if tp+fp else None,
      'limitations':['Independent external cohort provenance not established by software.',
       'Patient/temporal overlap with training source must be independently ruled out.',
       'Index-day leakage and outcome adjudication require clinical review.',
       'No calibrated probability or clinical benefit claim.']}
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('labelled_csv');p.add_argument('model_json');p.add_argument('--output',default='ml/validation_report.json');p.add_argument('--threshold',type=float,default=.5)
    a=p.parse_args()
    if not (0<a.threshold<1):p.error('threshold must be between 0 and 1')
    r=evaluate(a.labelled_csv,a.model_json,threshold=a.threshold)
    Path(a.output).write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2))
