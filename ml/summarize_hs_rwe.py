#!/usr/bin/env python3
"""Create a human-readable validation report from the HS-RWE outputs and input records."""
import argparse,json
from pathlib import Path
import pandas as pd

def summarize(root,output,report_path):
    root=Path(root);output=Path(output)
    report=json.loads(Path(report_path).read_text());v=report['validation'];modal=report['modal_holdout']
    rows=[]
    train_sites=set(pd.read_csv(root/'train/patient_assignment.csv').practitioner_id)
    for s in ['train','test_1','test_2']:
        dem=pd.read_csv(root/s/'demographics.csv');vis=pd.read_csv(root/s/'visits.csv');ass=pd.read_csv(root/s/'patient_assignment.csv')
        rows.append({'cohort':s,'N':len(dem),'female %':round(100*(dem.sex=='Female').mean(),1),
            'IHS4 scored %':round(100*vis.ihs4_score.notna().mean(),1),
            'observed IHS4 mean':round(vis.ihs4_score.mean(),2),
            'new practitioner %':round(100*(~ass.practitioner_id.isin(train_sites)).mean(),1)})
    table=pd.DataFrame(rows).to_markdown(index=False)
    q=[f'''# HIDVIA / Almirall HS-RWE research validation report

**Data:** Supplied synthetic Almirall challenge archives. **Forecast target:** latent average daily IHS4 in January–June 2026. **Information cutoff:** 2025-12-31. **Assessment:** reproducible internal holdout, not clinical, prospective or external validation.

## Blind test sets

Train: 21,000 labelled patients; test_1: 4,000; test_2: 6,228. Test labels are not supplied, so **it is impossible to calculate test_1/test_2 MAE in this environment**. All four submission templates were populated separately. Only the organiser can score them.

## Patient-disjoint holdout (16,800 train / 4,200 validation patients)

| Method | MAE, lower better |
|---|---:|
| HIDVIA LightGBM using longitudinal tabular records | **{v['mae_model']:.3f}** |
| Hurley-stage median | {v['mae_hurley_median']:.3f} |
| Carry forward last IHS4 | {v['mae_last_ihs4']:.3f} |
| Training-population median | {v['mae_constant_median']:.3f} |

Biologic subgroup (n={v['mae_by_active_biologic']['1']['n']}): MAE {v['mae_biologic']:.3f}; non-biologic (n={v['mae_by_active_biologic']['0']['n']}): MAE {v['mae_without_biologic']:.3f}.

## Embeddings (internal modality-tuned holdout, optimistic)

| Modal subset | Train | Validation | Tabular MAE | Modality-adjusted MAE | Difference (positive = improvement) |
|---|---:|---:|---:|---:|---:|
''']
    for k,z in modal.items():q.append(f"| {k} | {z['train_n']} | {z['validation_n']} | {z['mae_tabular_same_patients']:.3f} | {z['mae_modal_selected']:.3f} | {z['mae_delta_positive_is_improvement']:+.3f} |\n")
    q.append('''
**Caveat:** Hyperparameters and blending were selected on this same small internal holdout (550 image / 107 image+RNA validation patients). This is hypothesis-generation, NOT an unbiased estimate of multimodal gain. A valid comparative test must evaluate all three models (tabular; tabular+image; tabular+image+RNA) on the *same 3b patients*, with nested validation or an untouched test with labels. Image and RNA subsets are nonrandom. RNA-seq embeddings are not acquired by a phone sensor.

## Dataset shift observed (features only; no test outcomes)

'''+table+'\n\n')
    q.append('''
Test 2 has more female patients and less complete IHS4 scoring than train. These are documented covariate and missingness shifts; their effect on the hidden test MAE is unmeasurable without the hidden outcomes. The model relies heavily on **practitioner_id**, an important possible site/documentation artefact rather than biology; deployment should evaluate new-site transportability and consider reduced reliance on this identifier.

## Model features and exclusion of leakage

111 pre-cutoff demographic, clinical-visit, scoring-frequency, flare-reactive visit, treatment-history, surgery-history and site features. The open biologic treatment is assumed to continue in the forecast interval as specified by the challenge. **Surgical outcome columns (`recurrence_within_6mo`, `wound_healing_weeks`) are excluded**, because values recorded close to December 2025 could reveal future outcomes. Test IDs are opaque and not used as predictors. Embeddings are loaded only when capture or collection dates are on/before 2025-12-31.

The most important tabular features by model split count include practitioner ID, duration of active biologic, Hurley stage, last IHS4 score and its age. Feature importance is model association, not proof of causal relevance.

## Super-responder exercise limitation

The data includes observed IHS4 targets, but **does not include individual no-biologic counterfactual outcomes or a validated super-responder label**. It is therefore not possible to directly train or validate a probability for the challenge's >75% counterfactual-treatment reduction definition. Exercise 2 includes the required IHS4 forecasts but intentionally omits the optional `super_responder_prob` column rather than inventing a calibrated probability. Historical pre/post treatment scores may be exploratory *observational proxies*, with confounding by indication and regression to the mean.

## What was tried, what failed, and what remains

- Tabular-only LightGBM compared against population-median, Hurley and last-score baselines; internal improvement observed.
- Image embedding residual correction offers near-zero incremental holdout improvement after shrinkage; avoid claiming useful image effects based on this result.
- Joint image+RNA correction shows a positive small-cohort holdout difference, but it was tuned on only 107 held-out records and is not independently established.
- Next: blind organiser scoring on both test sets, nested/cross-fitted uncertainty intervals, batch/device confound models, modality sample-volume curves, site-held-out evaluation, and treatment-counterfactual analyses with additional outcome labels.

## Clinical use

**No medical-device claim.** These are synthetic, challenge-specific results only. Six-month IHS4 regression cannot be presented as prediction of an imminent flare. A phone diary/risk score and a physical RNA instrument need separate real-world validations and a manufacturer-defined protocol before use for patient care.
''')
    output.write_text(''.join(q),encoding='utf8')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--validation',required=True);p.add_argument('--output',required=True)
 a=p.parse_args();summarize(a.data,a.output,a.validation)
