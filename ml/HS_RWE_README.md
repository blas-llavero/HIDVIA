# HS-RWE Challenge Track — Six-month IHS4 Forecast

This is **not** the HIDVIA app's experimental 7-day flare tracking model. The supplied Almirall challenge defines a separate **regression task**: predict the patient's *latent average daily IHS4* from 2026-01-01 through 2026-06-30 using records dated no later than 2025-12-31. Dataset is synthetic.

## Install and run

Use Python 3.11+, and install the dependencies:

```bash
pip install -r ml/requirements.txt
```

Extract either user-supplied dataset ZIP **outside the public GitHub repository**. The command expects `public/train`, `public/test_1`, `public/test_2` and `public/evaluation_templates`. Example:

```bash
python ml/hs_rwe_pipeline.py --data /private/challenge/public --output output/hs_rwe
python ml/summarize_hs_rwe.py --data /private/challenge/public --validation output/hs_rwe/validation_report.json --output output/hs_rwe/VALIDATION_REPORT.md
```

Four score-ready files are written:
- `answers_Team4_exercise1.csv` — 10,228 test patients
- `answers_Team4_exercise2.csv` — 4,140 biologic patients (optional `super_responder_prob` excluded)
- `answers_Team4_exercise3_images.csv` — 1,200 image patients
- `answers_Team4_exercise3_images_rnaseq.csv` — 400 image+RNA patients

Output also includes `validation_report.json`, `research_ihs4_model.joblib` and a separate Markdown report. The joblib model must be loaded **only from a trusted local source**; it contains pickle objects. It is not trained or validated for the live app's symptom check-ins or wearable data.

## Safeguards and interpretation

The pipeline checks observation dates against the challenge cutoff; builds history, visit frequency/missingness, treatment/surgery and practitioner features; trains and evaluates a LightGBM MAE model on a patient-disjoint training holdout; and studies image and RNA embeddings on their eligible subsets with strongly regularized residual models. Modality hyperparameters are chosen on the same internal holdout, so the reported modality gain is optimistic, not independent validation.

The supplied test data **have no true targets**. Do not describe holdout MAE as `test_1` or `test_2` scores. The super-responder counterfactual label is also unavailable; no probabilities are invented. This work must not be used for clinical decisions.

The uploaded challenge document is marked **INTERNAL USE**; do not publish source datasets or pseudonymized participant rows to a public GitHub repository without authorisation.
