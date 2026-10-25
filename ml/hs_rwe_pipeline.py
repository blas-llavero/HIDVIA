#!/usr/bin/env python3
"""HIDVIA / Almirall HS-RWE six-month IHS4 challenge.

Train-only validation and inference. Uses precisely observed pre-2026 tables; never
reads future labels for test sets. All competition data must be user-supplied.

Usage:
  python ml/hs_rwe_pipeline.py --data /path/to/public --output output/hs_rwe
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split, KFold
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from lightgbm import LGBMRegressor, early_stopping, log_evaluation

CUTOFF = pd.Timestamp('2025-12-31')
WINDOW_START = pd.Timestamp('2026-01-01')
IMG_DIMS = [f'image_dim_{i:03d}' for i in range(256)]
RNA_DIMS = [f'rnaseq_dim_{i:03d}' for i in range(128)]
SEED = 2026


def days_before(s):
    return (CUTOFF - pd.to_datetime(s, errors='coerce')).dt.days


def load(root, split, name):
    path=Path(root)/split/(name+'.csv')
    if path.is_file(): return pd.read_csv(path)
    return pd.DataFrame()


def ensure_past(df, date_col):
    if df.empty:return df
    dates=pd.to_datetime(df[date_col], errors='coerce')
    if dates.notna().any() and (dates > CUTOFF).any():
        raise ValueError(f'Future data in {date_col}; would leak outcomes')
    return df.assign(_dt=dates).loc[dates.le(CUTOFF)].copy()


def patient_features(root, split):
    dem=load(root,split,'demographics').copy()
    assert dem.patient_id.is_unique
    d=dem.set_index('patient_id')
    d['age_at_cutoff']=2025-pd.to_numeric(d.birth_year,errors='coerce')
    d['years_since_diagnosis']=days_before(d.diagnosis_date)/365.25
    d['years_since_onset']=days_before(d.symptom_onset_date)/365.25
    d=d.drop(columns=['birth_year','symptom_onset_date','diagnosis_date'])
    assign=load(root,split,'patient_assignment').set_index('patient_id')
    d=d.join(assign)
    v=ensure_past(load(root,split,'visits'),'visit_date')
    v['scored']=v.ihs4_score.notna()
    v['time_ago']=days_before(v.visit_date)
    v['is_flare']=(v.visit_type=='flare_reactive').astype('int8')
    v['is_monitor']=(v.visit_type=='treatment_monitoring').astype('int8')
    v['is_followup']=(v.visit_type=='follow_up').astype('int8')
    v=v.sort_values(['patient_id','_dt'])
    def put(group, prefix):
        return group.add_prefix(prefix)
    if not v.empty:
        g=v.groupby('patient_id',sort=False)
        base=g.agg(visit_count=('visit_id','size'), scored_count=('scored','sum'),
            flare_visits=('is_flare','sum'),monitor_visits=('is_monitor','sum'),
            followup_visits=('is_followup','sum'), first_visit=('_dt','min'), last_visit=('_dt','max'),
            days_since_last_visit=('time_ago','min'),last_ihs4=('ihs4_score','last'),
            mean_ihs4=('ihs4_score','mean'),median_ihs4=('ihs4_score','median'),
            std_ihs4=('ihs4_score','std'),max_ihs4=('ihs4_score','max'),
            min_ihs4=('ihs4_score','min'))
        base['observed_years']=((base.last_visit-base.first_visit).dt.days/365.25).clip(lower=.1)
        base['visit_rate_year']=base.visit_count/base.observed_years
        base['scored_rate']=base.scored_count/base.visit_count
        base['flare_fraction']=base.flare_visits/base.visit_count
        base['unscored_count']=base.visit_count-base.scored_count
        base['months_since_first_visit']=days_before(base.first_visit)/30.44
        base=base.drop(columns=['first_visit','last_visit'])
        d=d.join(base)
        scored=v.loc[v.scored].copy()
        if len(scored):
            gg=scored.groupby('patient_id',sort=False)
            lastsc=gg.tail(1).set_index('patient_id')
            d['days_since_last_ihs4']=lastsc.time_ago
            d['last_scored_visit_type']=lastsc.visit_type
            for k in [2,3,5,10]:
                lastk=gg.tail(k).groupby('patient_id').ihs4_score.mean()
                d[f'last_{k}_ihs4_mean']=lastk
            d['last_3_score_slope']=gg.tail(3).groupby('patient_id').apply(
                lambda p:(p.ihs4_score.iloc[-1]-p.ihs4_score.iloc[0])/max(30,(p._dt.iloc[-1]-p._dt.iloc[0]).days)*90,
                include_groups=False)
        for window in [90,180,365,730,1460]:
            q=v.loc[v.time_ago.le(window)].copy()
            if q.empty:continue
            agg=q.groupby('patient_id').agg(**{
                f'visits_{window}d':('visit_id','size'),
                f'flare_visits_{window}d':('is_flare','sum'),
                f'scored_{window}d':('scored','sum'),
                f'ihs4_mean_{window}d':('ihs4_score','mean'),
                f'ihs4_max_{window}d':('ihs4_score','max'),
                f'ihs4_std_{window}d':('ihs4_score','std'),
                f'unscored_{window}d':('scored',lambda x:(~x).sum())})
            d=d.join(agg)
        for year,low,high in [('2022',1095,1460),('2023',730,1095),('2024',365,730),('2025',0,365)]:
            q=v.loc[v.time_ago.ge(low)&v.time_ago.lt(high)]
            d=d.join(q.groupby('patient_id').agg(**{f'ihs4_{year}':('ihs4_score','mean'),f'visits_{year}':('visit_id','size')}))
        d['ihs4_trend_recent']=d.get('ihs4_mean_180d')-d.get('ihs4_mean_730d')
        d['ihs4_trend_year']=d.get('ihs4_2025')-d.get('ihs4_2024')
    tr=ensure_past(load(root,split,'treatments'),'start_date')
    if not tr.empty:
        tr['days_started']=days_before(tr.start_date)
        tr['days_ended']=days_before(tr.end_date)
        tr['active']=tr.end_date.isna() | pd.to_datetime(tr.end_date,errors='coerce').ge(CUTOFF)
        tr['duration_days']=(pd.to_datetime(tr.end_date,errors='coerce').fillna(CUTOFF)-tr._dt).dt.days.clip(lower=0)
        tr['is_bio']=(tr.treatment_class=='Biologic')
        tr['is_antibiotic']=(tr.treatment_class=='Antibiotic')
        tg=tr.groupby('patient_id')
        d=d.join(tg.agg(total_treatments=('treatment_id','size'),bio_lines=('is_bio','sum'),
            antibiotic_courses=('is_antibiotic','sum'),total_treatment_days=('duration_days','sum')))
        bio=tr[tr.is_bio].sort_values(['patient_id','_dt'])
        if not bio.empty:
            active=bio.loc[bio.active].groupby('patient_id').tail(1).set_index('patient_id')
            d['active_biologic']=d.index.isin(active.index).astype('int8')
            d['current_biologic_drug']=active.drug_name
            d['bio_days_active']=active.days_started
            d['bio_line_number']=active.treatment_line
            d['bio_total_days']=bio.groupby('patient_id').duration_days.sum()
            d['bio_last_start_days']=bio.groupby('patient_id').days_started.min()
            d['bio_first_start_days']=bio.groupby('patient_id').days_started.max()
            d['bio_unique_drugs']=bio.groupby('patient_id').drug_name.nunique()
            # Pre/post-treatment score difference is observable, not a counterfactual response label.
            if not v.empty and len(active):
                bio_start=active._dt
                vb=v[v.patient_id.isin(bio_start.index)].copy()
                vb['bio_start']=vb.patient_id.map(bio_start)
                vb['relative_days']=(vb._dt-vb.bio_start).dt.days
                pre=vb.loc[vb.relative_days.between(-365,-1)].groupby('patient_id').ihs4_score.mean()
                post=vb.loc[vb.relative_days.between(30,365)].groupby('patient_id').ihs4_score.mean()
                d['bio_pre_year_ihs4']=pre
                d['bio_post_year_ihs4']=post
                d['bio_observed_score_drop']=pre-post
                d['bio_observed_score_ratio']=post/(pre+.5)
        else:d['active_biologic']=0
        ab=tr[tr.is_antibiotic]
        for w in [90,180,365]:
            recent=ab.loc[ab.days_started.le(w)].groupby('patient_id').agg(**{
                f'ab_courses_started_{w}d':('treatment_id','size'),
                f'ab_duration_started_{w}d':('duration_days','sum')})
            d=d.join(recent)
        d['any_active_antibiotic']=d.index.isin(ab.loc[ab.active].patient_id).astype('int8')
    s=ensure_past(load(root,split,'surgeries'),'procedure_date')
    if not s.empty:
        s['time_ago']=days_before(s.procedure_date)
        d=d.join(s.groupby('patient_id').agg(surgery_count=('surgery_id','size'),
            days_since_last_surgery=('time_ago','min'),
            mean_surgery_interval_days=('time_ago','mean')))
        for w in [180,365,730]:
            d[f'surgeries_{w}d']=s.loc[s.time_ago.le(w)].groupby('patient_id').size()
    d=d.replace([np.inf,-np.inf],np.nan)
    d['split']=split
    return d.reset_index()


def embeddings(root,split,modality):
    if modality=='image':
        meta=load(root,split,'images_metadata')
        emb=load(root,split,'images_embeddings')
        idcol='image_id';prefix='image_';dims=IMG_DIMS
    else:
        meta=load(root,split,'rnaseq_metadata')
        emb=load(root,split,'rnaseq_embeddings')
        idcol='rnaseq_sample_id';prefix='rnaseq_';dims=RNA_DIMS
    if meta.empty or emb.empty:return pd.DataFrame(columns=['patient_id']+dims)
    key='capture_date' if modality=='image' else 'collection_date'
    meta=ensure_past(meta,key)
    assert meta.patient_id.is_unique, 'Expected at most one embedding per patient'
    if meta[idcol].duplicated().any():raise ValueError('Repeated embedding IDs')
    joined=meta[['patient_id',idcol]].merge(emb[[idcol]+dims],on=idcol,validate='one_to_one')
    return joined.drop(columns=idcol)


def tabular_model(trainx,trainy,validx=None,validy=None,iterations=650):
    # categorical values are stringified and encoded with train-only fixed categories.
    cats=[c for c in trainx if str(trainx[c].dtype) in ('object','str','category')]
    trainx=trainx.copy()
    if validx is not None:validx=validx.copy()
    for c in cats:
        categories=pd.Index(trainx[c].astype('object').fillna('MISSING').astype(str).unique())
        trainx[c]=pd.Categorical(trainx[c].astype('object').fillna('MISSING').astype(str),categories=categories)
        if validx is not None:validx[c]=pd.Categorical(validx[c].astype('object').fillna('MISSING').astype(str),categories=categories)
    m=LGBMRegressor(n_estimators=iterations,objective='regression_l1',learning_rate=.035,
        num_leaves=18,max_depth=-1,min_child_samples=65,colsample_bytree=.87,
        subsample=.9,subsample_freq=1,reg_lambda=5,verbosity=-1,random_state=SEED,n_jobs=4)
    kw={}
    if validx is not None:kw={'eval_set':[(validx,validy)],'eval_metric':'l1',
                                'callbacks':[early_stopping(75,verbose=False),log_evaluation(0)]}
    m.fit(trainx,trainy,**kw)
    return m,cats


def coerce(xtrain, xtest, cats):
    a=xtrain.copy();b=xtest.copy()
    for c in cats:
        categories=a[c].cat.categories if hasattr(a[c],'cat') else pd.Index(a[c].astype('object').fillna('MISSING').astype(str).unique())
        a[c]=pd.Categorical(a[c].astype('object').fillna('MISSING').astype(str),categories=categories)
        b[c]=pd.Categorical(b[c].astype('object').fillna('MISSING').astype(str),categories=categories)
    return a,b


def oof_predictions(x,y,iterations=400,folds=4):
    """Patient-disjoint cross-fitted base predictions for unbiased modal residuals."""
    out=np.zeros(len(x),dtype=float)
    cv=KFold(n_splits=folds,shuffle=True,random_state=SEED+5)
    for tr,va in cv.split(x):
        mod,cat=tabular_model(x.iloc[tr],y.iloc[tr],iterations=iterations)
        xx,zz=coerce(x.iloc[tr],x.iloc[va],cat)
        out[va]=np.maximum(0,mod.predict(zz))
    return out


def metric(y,p):return float(mean_absolute_error(y,np.maximum(0,p)))


def ridge_residual_embeddings(train_df, val_df, tab_col, ycol, dimensions, subset, alpha=300):
    tr=train_df.loc[train_df.patient_id.isin(subset)].copy()
    va=val_df.loc[val_df[dimensions[0]].notna()].copy()
    if len(tr)<100 or va.empty:return None,None,0
    feat=dimensions+['pred_base']
    x=tr[feat].to_numpy(dtype=float); v=va[feat].to_numpy(dtype=float)
    mu=np.nanmean(x,axis=0);mu=np.where(np.isfinite(mu),mu,0)
    x=np.where(np.isfinite(x),x,mu);v=np.where(np.isfinite(v),v,mu)
    scaler=StandardScaler().fit(x)
    m=Ridge(alpha=alpha).fit(scaler.transform(x),tr[ycol]-tr[tab_col])
    return va.patient_id.to_numpy(),m.predict(scaler.transform(v)),len(tr)


def run(root,out,iterations=650):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if not (root/'train'/'targets.csv').exists():raise FileNotFoundError('Pass path to public/ directory')
    dfs={s:patient_features(root,s) for s in ['train','test_1','test_2']}
    train=dfs['train'].merge(load(root,'train','targets'),on='patient_id',validate='one_to_one')
    tests=pd.concat([dfs['test_1'],dfs['test_2']],ignore_index=True)
    forbidden={'patient_id','avg_ihs4_next6','split'}
    cols=[c for c in train.columns if c not in forbidden]
    # No target leakage through patient_id or opaque visit identifiers.
    train_idx,valid_idx=train_test_split(np.arange(len(train)),test_size=.20,random_state=SEED)
    a=train.iloc[train_idx].copy();b=train.iloc[valid_idx].copy()
    av=a[cols];bv=b[cols]
    model,cats=tabular_model(av,a.avg_ihs4_next6,bv,b.avg_ihs4_next6,iterations)
    aX,bX=coerce(av,bv,cats)
    pred=np.maximum(0,model.predict(bX))
    base_mean=np.repeat(a.avg_ihs4_next6.median(),len(b))
    hurley_mean=a.groupby('hurley_stage_baseline').avg_ihs4_next6.median()
    hurley_base=b.hurley_stage_baseline.map(hurley_mean).fillna(a.avg_ihs4_next6.median())
    carry=b.last_ihs4.fillna(a.avg_ihs4_next6.median())
    m_val={'n_train':len(a),'n_validation':len(b),'mae_model':metric(b.avg_ihs4_next6,pred),
         'mae_constant_median':metric(b.avg_ihs4_next6,base_mean),
         'mae_hurley_median':metric(b.avg_ihs4_next6,hurley_base),
         'mae_last_ihs4':metric(b.avg_ihs4_next6,carry),
         'mae_biologic':metric(b.loc[b.active_biologic==1,'avg_ihs4_next6'],pred[(b.active_biologic==1).to_numpy()]),
         'mae_without_biologic':metric(b.loc[b.active_biologic!=1,'avg_ihs4_next6'],pred[(b.active_biologic!=1).to_numpy()])}
    for group in ['sex','ethnicity','hurley_stage_baseline','active_biologic']:
        m_val['mae_by_'+group]={str(k):{'n':int(len(g)),'mae':metric(g.avg_ihs4_next6,pred[b.index.get_indexer(g.index)])}
                 for k,g in b.groupby(group,dropna=False) if len(g)>=25}
    allX,testX=coerce(train[cols],tests[cols],cats)
    final,_=tabular_model(allX,train.avg_ihs4_next6,iterations=max(200,int(getattr(model,'best_iteration_',iterations) or iterations)))
    base_train=np.maximum(0,final.predict(allX))
    base_test=np.maximum(0,final.predict(testX))
    train['pred_base']=base_train;tests['pred_base']=base_test
    feature_imp=sorted(zip(cols,final.feature_importances_.astype(int).tolist()),key=lambda x:-x[1])[:30]
    template_dir=root/'evaluation_templates'
    base_pred=tests.set_index('patient_id').pred_base
    for exc in ['exercise1','exercise2']:
        q=pd.read_csv(template_dir/f'answers_teamName_{exc}.csv')
        q['pred_avg_ihs4_next6']=q.patient_id.map(base_pred)
        if exc=='exercise2' and 'super_responder_prob' in q.columns:
            # No counterfactual treatment response labels exist: do not invent such probabilities.
            q=q.drop(columns=['super_responder_prob'])
        assert q.pred_avg_ihs4_next6.notna().all(), f'Missing predictions: {exc}'
        q.to_csv(out/f'answers_Team4_{exc}.csv',index=False)
    # Gather image (256) and RNA-seq (128) embeddings by patient, restricted to pre-cutoff dates.
    nmodal={}
    for modality in ['image','rnaseq']:
        for spl in ['train','test_1','test_2']:
            e=embeddings(root,spl,modality)
            nmodal[f'{modality}_{spl}']=int(e.patient_id.nunique())
        tr_e=embeddings(root,'train',modality)
        te_e=pd.concat([embeddings(root,'test_1',modality),embeddings(root,'test_2',modality)],ignore_index=True)
        train=train.merge(tr_e,on='patient_id',how='left',validate='one_to_one')
        tests=tests.merge(te_e,on='patient_id',how='left',validate='one_to_one')

    # Evaluate modalities on the same patient-disjoint validation holdout.
    # Base predictions used as training residuals are cross-fitted, not in-sample.
    a=train.loc[train.patient_id.isin(a.patient_id)].copy()
    b=train.loc[train.patient_id.isin(b.patient_id)].copy()
    a['pred_base']=a.patient_id.map(dict(zip(train.iloc[train_idx].patient_id,np.maximum(0,model.predict(aX)))))
    b['pred_base']=b.patient_id.map(dict(zip(train.iloc[valid_idx].patient_id,pred)))
    oof_a=oof_predictions(train[train.patient_id.isin(a.patient_id)][cols].reset_index(drop=True),
                          train[train.patient_id.isin(a.patient_id)].avg_ihs4_next6.reset_index(drop=True),
                          iterations=350,folds=4)
    a['pred_oof']=oof_a
    hold={};selected={}
    for mod,features,alphas in [('image',IMG_DIMS,[500,1500,5000,15000]),
                                ('image_rna',IMG_DIMS+RNA_DIMS,[1500,5000,15000,50000])]:
        sub_a=a.loc[a[features].notna().all(axis=1)].copy()
        sub_b=b.loc[b[features].notna().all(axis=1)].copy()
        if len(sub_a)<100 or len(sub_b)<20:continue
        train_matrix=sub_a[features].to_numpy(dtype=np.float32)
        val_matrix=sub_b[features].to_numpy(dtype=np.float32)
        scaler=StandardScaler().fit(train_matrix)
        x=scaler.transform(train_matrix);z=scaler.transform(val_matrix)
        baseline=metric(sub_b.avg_ihs4_next6,sub_b.pred_base)
        trials=[]
        for al in alphas:
            ridge=Ridge(alpha=al).fit(x,sub_a.avg_ihs4_next6-sub_a.pred_oof)
            corr=ridge.predict(z)
            for weight in [.25,.5,1.0]:
                trial_mae=metric(sub_b.avg_ihs4_next6,sub_b.pred_base+weight*corr)
                trials.append((trial_mae,al,weight))
        best=min(trials)
        improvement=baseline-best[0]
        # A no-embeddings option is allowed when optional features hurt this cohort.
        alpha,weight=(best[1],best[2]) if improvement>0 else (best[1],0.)
        selected[mod]={'alpha':int(alpha),'weight':float(weight)}
        hold[mod]={'train_n':len(sub_a),'validation_n':len(sub_b),
            'mae_tabular_same_patients':baseline,'mae_modal_selected':min(baseline,best[0]),
            'mae_delta_positive_is_improvement':max(0.,improvement),
            'alpha_selected_on_holdout':int(alpha),'blend_weight_selected_on_holdout':float(weight),
            'note':'Exploratory tuning on same internal validation set; gains are optimistic, require nested CV / external test.'}

    # Refit modality adjustments against OOF tabular residuals on all 21,000 train patients.
    train['pred_oof']=oof_predictions(train[cols],train.avg_ihs4_next6,iterations=350,folds=4)
    for mod,features,outcol,subset in [('image',IMG_DIMS,'pred_image','image'),
                                        ('image_rna',IMG_DIMS+RNA_DIMS,'pred_joint','rnaseq')]:
        if mod=='image':tests[outcol]=tests.pred_base
        else:tests[outcol]=tests.pred_image
        co=selected.get(mod,{'alpha':1,'weight':0})
        if co['weight']==0:continue
        sub_a=train.loc[train[features].notna().all(axis=1)].copy()
        sub_t=tests.loc[tests[features].notna().all(axis=1)].copy()
        scaler=StandardScaler().fit(sub_a[features].to_numpy(dtype=np.float32))
        ridge=Ridge(alpha=co['alpha']).fit(scaler.transform(sub_a[features].to_numpy(dtype=np.float32)),
                          sub_a.avg_ihs4_next6-sub_a.pred_oof)
        corrected=sub_t.pred_base.to_numpy()+co['weight']*ridge.predict(scaler.transform(sub_t[features].to_numpy(dtype=np.float32)))
        tests.loc[sub_t.index,outcol]=np.maximum(0,corrected)
    for exc,key in [('exercise3_images','pred_image'),('exercise3_images_rnaseq','pred_joint')]:
        q=pd.read_csv(template_dir/f'answers_teamName_{exc}.csv')
        q['pred_avg_ihs4_next6']=q.patient_id.map(tests.set_index('patient_id')[key])
        assert q.pred_avg_ihs4_next6.notna().all()
        q.to_csv(out/f'answers_Team4_{exc}.csv',index=False)
    report={'target':'average latent IHS4 from 2026-01-01 to 2026-06-30',
      'validation_type':'Internal patient-disjoint random holdout in train only; NOT hidden test_1/test_2 evaluation',
      'validation':m_val,'embeddings':nmodal,'modal_holdout':hold,
      'model_features':len(cols),'important_features':feature_imp,
      'test_counts':tests.groupby('split').size().astype(int).to_dict(),
      'important_limitations':['No labels exist for the blind test sets; MAE cannot be calculated for test_1/test_2.',
       'Internal random holdout is not external, temporal or clinical validation.',
       'Synthetic data only; not calibrated for real patient risk.',
       'RNA embeddings are NOT physical device RNA sensor measurements.',
       'No counterfactual response labels: super-responder probabilities withheld.',
       'The prediction system is six-month mean IHS4, not imminent flare probability.',
       'Open biologic line is assumed unchanged over forecast window per challenge documentation.']}
    (out/'validation_report.json').write_text(json.dumps(report,indent=2,default=str))
    # Save final pipeline and category schema for offline research inference.
    import joblib
    joblib.dump({'model':final,'columns':cols,'categories':{c:allX[c].cat.categories.tolist() for c in cats},
      'status':'SYNTHETIC_RESEARCH_ONLY','horizon':'2026-01-01_to_2026-06-30'},out/'research_ihs4_model.joblib',compress=3)
    print(json.dumps({'validation':m_val,'modal_holdout':hold,'counts':nmodal,'output':str(out)},indent=2))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',required=True,help='Local public directory from the challenge archives')
    p.add_argument('--output',default='output/hs_rwe')
    p.add_argument('--iterations',type=int,default=650)
    args=p.parse_args();run(args.data,args.output,args.iterations)
