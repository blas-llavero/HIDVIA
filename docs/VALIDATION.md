# Clinical ML validation plan — not yet performed

## Define the outcome

The research objective is to estimate the chance of an independently adjudicated *HS flare onset within the next seven days* in a person with established HS, using data available no later than the prediction timestamp. Explicitly define flare events, worsening and symptom onset with dermatologists; distinguish active flares from future new onset. Establish index-date eligibility and absence of outcome leakage.

## Data harmonisation

Data dictionary: pseudonymous patient and visit IDs; time stamps; site/clinic; pain, itch, swelling, nodules/abscesses/drainage; treatment and recent changes; previous flares; body sites, IHS4 or equivalent severity where available; sleep and self-reported stress; physician adjudication; validated photo capture protocol. Document wearable availability/consent and missing data. Minimize sensitive attributes and demographics; evaluate biases and fairness without using protected traits to deny care.

## Training and evaluation

- Split by patient (and ideally by hospital), preserve prospective time direction, and avoid leaking future events, future outcomes, and repeated patient observations across partitions.
- Report prevalence, AUROC, AUPRC/average precision, sensitivity, specificity, PPV, NPV, calibration plots and Brier score at prespecified clinically justified operating points, including alert fatigue and lead time.
- Compare patient-only symptom baselines, time-series predictors (e.g. gradient boosting and hierarchical longitudinal models), wearable/no-wearable ablations, and image/no-image ablations. Evaluate follow-up missingness, calibration utility and subgroup performance.
- Investigate partial participation and differing report frequency: missingness may itself be a source of selection bias; avoid counting absent check-ins as low risk.
- Conduct external prospective validation and human factors studies before any clinical deployment. Model changes must be controlled and documented.

## Research model in this repository

`ml/train_model.py` implements a patient-grouped exploratory logistic model. It is a basic starting point, not a validated algorithm. It constructs seven-day future onset labels from documented events after index dates and excludes rows with inadequate future coverage. The fitted coefficients are generated **only when suitable de-identified longitudinal source data are actually provided**. No accuracy metrics or weights are fabricated in the package.

**Safety guardrail:** Default fallback remains unvalidated symptom signalling without calibration. Alerts are demonstrative and must not be used for escalation, medication change, triage or patient reassurance.
