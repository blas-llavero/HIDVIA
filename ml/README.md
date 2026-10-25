# Research ML pipeline (not deployed by default)

This is a **real training and scoring pipeline**, not a claim that a clinically validated predictive model has been trained. A training dataset was not accessible in the current deliverable. **Without a separately trained model, HIDVIA works using a transparent, non-validated symptom signal**, and calibration is optional.

## Required de-identified CSV

Each row represents one patient on one index date. Headers:

`patient_id,date,flare_onset,pain,itch,swelling,fatigue,stress,sleep,drainage`

- `patient_id`: pseudonym, stable per patient; never names or identifiers.
- `date`: ISO date, UTC for the current research pipeline.
- `flare_onset`: 0 or 1 denoting documented clinically adjudicated flare **on that date**, not a model label. A flare within the *subsequent* seven days is computed using future records for **labels only**. Rows lacking a full seven-day follow-up window are excluded, as are rows on an active onset day.
- Symptom numerical fields: pain, itch, swelling, fatigue, stress on 0–10 scales; sleep in hours; drainage as 0 or 1.

The patient's HS diagnosis, flare adjudication method, disease severity, treatments, and censoring assumptions should be documented separately. Missing-data bias, timing of care and treatment changes require explicit handling. Do not train on mere symptom snapshots without outcomes.

## Train

```bash
python3 -m pip install -r ml/requirements.txt
python3 ml/train_model.py /path/to/deidentified_longitudinal.csv --output ml/research_model.json
```

The script uses **patient-grouped** holdout splitting and reports AUROC, average precision, Brier score and outcome prevalence. Split once per training run; carry out external, site-based and later-period validation before even contemplating clinical use. The deployed backend accepts the file only if the operator **explicitly** sets `HIDVIA_MODEL_PATH`, described below.

```bash
HIDVIA_MODEL_PATH=ml/research_model.json python3 server/app.py
```

The user-facing output remains experimental, not clinical advice. No public model weights or training data are included. Do not misinterpret a raw model probability as a calibrated disease risk.
