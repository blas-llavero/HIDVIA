# HIDVIA / Almirall HS-RWE research validation report

**Data:** Supplied synthetic Almirall challenge archives. **Forecast target:** latent average daily IHS4 in January–June 2026. **Information cutoff:** 2025-12-31. **Assessment:** reproducible internal holdout, not clinical, prospective or external validation.

## Blind test sets

Train: 21,000 labelled patients; test_1: 4,000; test_2: 6,228. Test labels are not supplied, so **it is impossible to calculate test_1/test_2 MAE in this environment**. All four submission templates were populated separately. Only the organiser can score them.

## Patient-disjoint holdout (16,800 train / 4,200 validation patients)

| Method | MAE, lower better |
|---|---:|
| HIDVIA LightGBM using longitudinal tabular records | **1.457** |
| Hurley-stage median | 2.582 |
| Carry forward last IHS4 | 2.693 |
| Training-population median | 4.371 |

Biologic subgroup (n=1714): MAE 1.221; non-biologic (n=2486): MAE 1.620.

## Embeddings (internal modality-tuned holdout, optimistic)

| Modal subset | Train | Validation | Tabular MAE | Modality-adjusted MAE | Difference (positive = improvement) |
|---|---:|---:|---:|---:|---:|
| image | 2250 | 550 | 1.460 | 1.456 | +0.004 |
| image_rna | 493 | 107 | 1.896 | 1.624 | +0.272 |

**Caveat:** Hyperparameters and blending were selected on this same small internal holdout (550 image / 107 image+RNA validation patients). This is hypothesis-generation, NOT an unbiased estimate of multimodal gain. A valid comparative test must evaluate all three models (tabular; tabular+image; tabular+image+RNA) on the *same 3b patients*, with nested validation or an untouched test with labels. Image and RNA subsets are nonrandom. RNA-seq embeddings are not acquired by a phone sensor.

## Dataset shift observed (features only; no test outcomes)

| cohort   |     N |   female % |   IHS4 scored % |   observed IHS4 mean |   new practitioner % |
|:---------|------:|-----------:|----------------:|---------------------:|---------------------:|
| train    | 21000 |       72   |            64.3 |                12.38 |                  0   |
| test_1   |  4000 |       72.6 |            64.4 |                12.43 |                  0.2 |
| test_2   |  6228 |       89.3 |            51.4 |                12.6  |                  0.4 |


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
