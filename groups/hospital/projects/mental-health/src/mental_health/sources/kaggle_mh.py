"""Kaggle mental-health sources for hospital/mental-health.

Five public datasets carried under `data/upstream/` so the project builds
offline — provenance, licenses and re-fetch commands live in
`data/upstream/manifest.yaml`. Each resource is annotated before any model
exists; meaning is declared once and survives the implementation.

Three grains that must never be mixed outside the sanctioned bridge:
patient-level facts (episodes, screenings, ECGs), population benchmarks
(registry statistics), and anonymous survey context. The bridge is the
conformed Diagnosis dimension (`transform/seeds/diagnosis_map.csv`), which
this module also uses to stamp `diagnosis_code` at extraction time.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

import dlt
from pf.ontology import annotate

PROJECT_DIR = Path(__file__).resolve().parents[3]
UPSTREAM = PROJECT_DIR / "data" / "upstream"
DIAGNOSIS_MAP = PROJECT_DIR / "transform" / "seeds" / "diagnosis_map.csv"

_YES = {"TRUE", "YES", "Y"}
_NO = {"FALSE", "NO", "N"}


def _diagnosis_codes() -> dict[tuple[str, str], str]:
    """(source_vocabulary, label) → diagnosis_code, from the same seed that
    builds dim_diagnosis — one mapping, two consumers, zero drift."""
    with open(DIAGNOSIS_MAP, newline="", encoding="utf-8") as f:
        return {(r["source_vocabulary"], r["diagnosis_label"]): r["diagnosis_code"] for r in csv.DictReader(f)}


def _rows(name: str) -> Iterator[dict[str, str]]:
    with open(UPSTREAM / name, newline="", encoding="utf-8-sig") as f:
        yield from csv.DictReader(f)


def _yesno(raw: str) -> str:
    v = raw.strip().upper()
    if v in _YES:
        return "yes"
    if v in _NO:
        return "no"
    return v.lower() or "unknown"


def _score_of_ten(raw: str) -> int | None:
    # "3 From 10" → 3
    head = raw.strip().split(" ")[0]
    return int(head) if head.isdigit() else None


@dlt.resource(name="treatment_episodes", write_disposition="replace", primary_key="episode_id")
@annotate(
    source="kaggle_mh",
    concept="TreatmentEpisode",
    grain="one treatment episode per patient",
    description="Synthetic outpatient treatment monitoring (Kaggle "
    "uom190346a). Episode-grain snapshot — the scores are "
    "point-in-time, not a longitudinal series.",
    roles={
        "episode_id": "natural_key",
        "patient_id": "foreign_key",
        "diagnosis_code": "foreign_key",
        "age": "quantity",
        "gender": "status_enum",
        "diagnosis": "status_enum",
        "symptom_severity": "quantity",
        "mood_score": "quantity",
        "sleep_quality": "quantity",
        "physical_activity_hrs_week": "quantity",
        "medication": "status_enum",
        "therapy_type": "status_enum",
        "treatment_started_at": "event_time",
        "treatment_duration_weeks": "quantity",
        "stress_level": "quantity",
        "outcome": "status_enum",
        "treatment_progress": "quantity",
        "emotional_state": "status_enum",
        "adherence_pct": "quantity",
    },
    rename={},
    links={"patient_id": "Patient", "diagnosis_code": "Diagnosis"},
)
def treatment_episodes() -> Iterator[dict[str, Any]]:
    codes = _diagnosis_codes()
    for row in _rows("mental_health_diagnosis_treatment.csv"):
        pid = int(row["Patient ID"])
        yield {
            "episode_id": f"ep_{pid:04d}",
            "patient_id": f"pat_{pid:04d}",
            "age": int(row["Age"]),
            "gender": row["Gender"],
            "diagnosis": row["Diagnosis"],
            "diagnosis_code": codes[("treatment_monitoring", row["Diagnosis"])],
            "symptom_severity": int(row["Symptom Severity (1-10)"]),
            "mood_score": int(row["Mood Score (1-10)"]),
            "sleep_quality": int(row["Sleep Quality (1-10)"]),
            "physical_activity_hrs_week": int(row["Physical Activity (hrs/week)"]),
            "medication": row["Medication"],
            "therapy_type": row["Therapy Type"],
            "treatment_started_at": date.fromisoformat(row["Treatment Start Date"]),
            "treatment_duration_weeks": int(row["Treatment Duration (weeks)"]),
            "stress_level": int(row["Stress Level (1-10)"]),
            "outcome": row["Outcome"],
            "treatment_progress": int(row["Treatment Progress (1-10)"]),
            "emotional_state": row["AI-Detected Emotional State"],
            "adherence_pct": int(row["Adherence to Treatment (%)"]),
        }


@dlt.resource(name="screening_assessments", write_disposition="replace", primary_key="assessment_id")
@annotate(
    source="kaggle_mh",
    concept="ScreeningAssessment",
    grain="one behavioural screening of one person",
    description="Behavioural screening vs expert diagnosis — bipolar I/II, "
    "depression, normal (Kaggle cid007). Cohort unrelated to "
    "treatment_episodes patients.",
    roles={
        "assessment_id": "natural_key",
        "diagnosis_code": "foreign_key",
        "expert_diagnosis": "status_enum",
        "sadness": "status_enum",
        "euphoric": "status_enum",
        "exhausted": "status_enum",
        "sleep_disorder": "status_enum",
        "mood_swing": "status_enum",
        "suicidal_thoughts": "status_enum",
        "anorexia": "status_enum",
        "authority_respect": "status_enum",
        "try_explanation": "status_enum",
        "aggressive_response": "status_enum",
        "ignore_move_on": "status_enum",
        "nervous_breakdown": "status_enum",
        "admit_mistakes": "status_enum",
        "overthinking": "status_enum",
        "sexual_activity_score": "quantity",
        "concentration_score": "quantity",
        "optimism_score": "quantity",
    },
    rename={},
    links={"diagnosis_code": "Diagnosis"},
)
def screening_assessments() -> Iterator[dict[str, Any]]:
    codes = _diagnosis_codes()
    for row in _rows("dataset_mental_disorders.csv"):
        num = row["Patient Number"].strip().split("-")[-1]
        yield {
            "assessment_id": f"scr_{int(num):03d}",
            "expert_diagnosis": row["Expert Diagnose"],
            "diagnosis_code": codes[("disorder_screening", row["Expert Diagnose"])],
            "sadness": row["Sadness"].strip().lower(),
            "euphoric": row["Euphoric"].strip().lower(),
            "exhausted": row["Exhausted"].strip().lower(),
            "sleep_disorder": row["Sleep dissorder"].strip().lower(),
            "mood_swing": _yesno(row["Mood Swing"]),
            "suicidal_thoughts": _yesno(row["Suicidal thoughts"]),
            "anorexia": _yesno(row["Anorxia"]),
            "authority_respect": _yesno(row["Authority Respect"]),
            "try_explanation": _yesno(row["Try-Explanation"]),
            "aggressive_response": _yesno(row["Aggressive Response"]),
            "ignore_move_on": _yesno(row["Ignore & Move-On"]),
            "nervous_breakdown": _yesno(row["Nervous Break-down"]),
            "admit_mistakes": _yesno(row["Admit Mistakes"]),
            "overthinking": _yesno(row["Overthinking"]),
            "sexual_activity_score": _score_of_ten(row["Sexual Activity"]),
            "concentration_score": _score_of_ten(row["Concentration"]),
            "optimism_score": _score_of_ten(row["Optimisim"]),
        }


@dlt.resource(name="ecg_recordings", write_disposition="replace", primary_key="recording_id")
@annotate(
    source="kaggle_mh",
    concept="EcgRecording",
    grain="one 12-lead ECG segment",
    description="Summary features of psychiatric-cohort ECG segments (Kaggle "
    "buraktaci; 2,670 recordings: bipolar, depression, "
    "schizophrenia). Raw signals stay out of the warehouse — "
    "extraction is reproduced by scripts/extract_ecg_features.py.",
    roles={
        "recording_id": "natural_key",
        "diagnosis_code": "foreign_key",
        "disorder_group": "status_enum",
        "n_samples": "quantity",
        "n_leads": "quantity",
        "signal_mean": "quantity",
        "signal_std": "quantity",
        "signal_min": "quantity",
        "signal_max": "quantity",
        "signal_rms": "quantity",
        "lead2_mean": "quantity",
        "lead2_std": "quantity",
    },
    rename={},
    links={"diagnosis_code": "Diagnosis"},
)
def ecg_recordings() -> Iterator[dict[str, Any]]:
    codes = _diagnosis_codes()
    for row in _rows("ecg_features.csv"):
        yield {
            "recording_id": row["recording_id"],
            "source_file": row["source_file"],
            "disorder_group": row["disorder_group"],
            "diagnosis_code": codes[("psychiatry_ecg", row["disorder_group"])],
            "upstream_label": int(row["upstream_label"]),
            "n_samples": int(row["n_samples"]),
            "n_leads": int(row["n_leads"]),
            **{
                k: float(row[k])
                for k in (
                    "signal_mean",
                    "signal_std",
                    "signal_min",
                    "signal_max",
                    "signal_rms",
                    "lead2_mean",
                    "lead2_std",
                )
            },
        }


@dlt.resource(name="survey_responses", write_disposition="replace", primary_key="response_id")
@annotate(
    source="kaggle_mh",
    concept="SurveyResponse",
    grain="one survey response as published upstream",
    description="Population mental-health survey (Kaggle bhavikjikadara, "
    "2014). Respondents are anonymous members of the public — "
    "never Patients. Upstream carries exact duplicates (292,364 "
    "rows, ~290k distinct); landed as-is, deduplicated by the "
    "content-hash surrogate key in staging.",
    roles={
        "response_id": "natural_key",
        "content_hash": "surrogate_key",
        "surveyed_at": "event_time",
        "gender": "status_enum",
        "country": "geo_country",
        "occupation": "status_enum",
        "self_employed": "status_enum",
        "family_history": "status_enum",
        "sought_treatment": "status_enum",
        "days_indoors": "status_enum",
        "growing_stress": "status_enum",
        "changes_habits": "status_enum",
        "mental_health_history": "status_enum",
        "mood_swings": "status_enum",
        "coping_struggles": "status_enum",
        "work_interest": "status_enum",
        "social_weakness": "status_enum",
        "mental_health_interview": "status_enum",
        "care_options": "status_enum",
    },
    rename={},
    links={},
)
def survey_responses() -> Iterator[dict[str, Any]]:
    path = UPSTREAM / "mental_health_survey.csv.gz"
    with gzip.open(path, "rt", newline="", encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            content = "|".join(v.strip() for v in row.values())
            yield {
                "response_id": f"resp_{i:06d}",
                "content_hash": hashlib.sha1(content.encode()).hexdigest()[:16],
                "surveyed_at": datetime.strptime(row["Timestamp"], "%m/%d/%Y %H:%M"),
                "gender": row["Gender"],
                "country": row["Country"],
                "occupation": row["Occupation"],
                "self_employed": _yesno(row["self_employed"]),
                "family_history": _yesno(row["family_history"]),
                "sought_treatment": _yesno(row["treatment"]),
                "days_indoors": row["Days_Indoors"],
                "growing_stress": _yesno(row["Growing_Stress"]),
                "changes_habits": _yesno(row["Changes_Habits"]),
                "mental_health_history": _yesno(row["Mental_Health_History"]),
                "mood_swings": row["Mood_Swings"],
                "coping_struggles": _yesno(row["Coping_Struggles"]),
                "work_interest": _yesno(row["Work_Interest"]),
                "social_weakness": _yesno(row["Social_Weakness"]),
                "mental_health_interview": _yesno(row["mental_health_interview"]),
                "care_options": row["care_options"].strip().lower().replace(" ", "_"),
            }


@dlt.resource(name="registry_annual", write_disposition="replace", primary_key="statistic_id")
@annotate(
    source="kaggle_mh",
    concept="PopulationStatistic",
    grain="one statistic x year x sex x ICD-10 diagnostic group",
    description="Psychiatric in-patients by year, sex and ICD-10 group "
    "(CSO Ireland HRA71 via Kaggle noeyislearning; 2001-2023; "
    "number, rate per 100k, percent). A NULL value is a "
    "suppressed or not-applicable cell — never zero-fill.",
    roles={
        "statistic_id": "natural_key",
        "statistic_code": "status_enum",
        "statistic_label": "free_text",
        "year": "quantity",
        "year_date": "event_time",
        "sex": "status_enum",
        "icd10_group_code": "status_enum",
        "icd10_group": "status_enum",
        "unit": "status_enum",
        "value": "quantity",
    },
    rename={},
    links={},
)
def registry_annual() -> Iterator[dict[str, Any]]:
    for row in _rows("psychiatric_in_patients_annual.csv"):
        raw_value = row["VALUE"].strip()
        sex_code = row["C02199V02655"].strip() or "-"
        icd_code = row["C02945V03560"].strip()
        year = int(row["Year"])
        yield {
            "statistic_id": f"{row['STATISTIC']}_{year}_{sex_code}_{icd_code}",
            "statistic_code": row["STATISTIC"],
            "statistic_label": row["Statistic Label"],
            "year": year,
            "year_date": date(year, 1, 1),
            "sex": row["Sex"],
            "icd10_group_code": icd_code,
            "icd10_group": row["ICD 10 Diagnostic Group"],
            "unit": row["UNIT"],
            "value": float(raw_value) if raw_value else None,
            "is_suppressed": raw_value == "",
        }


@dlt.source(name="kaggle_mh")
def kaggle_mh_source():
    return [treatment_episodes(), screening_assessments(), ecg_recordings(), survey_responses(), registry_annual()]


ALL = [treatment_episodes, screening_assessments, ecg_recordings, survey_responses, registry_annual]
