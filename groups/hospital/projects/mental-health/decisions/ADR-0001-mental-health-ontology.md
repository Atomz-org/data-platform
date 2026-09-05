# ADR-0001 — Mental-health ontology extension, its research anchors, and grain law

Status: accepted · 2026-09-01

## Decision

The `hospital` group extension adds seven classes — Patient, Diagnosis,
TreatmentEpisode, ScreeningAssessment, EcgRecording, SurveyResponse,
PopulationStatistic — and four relations, all bridging through the conformed
`Diagnosis` dimension (`transform/seeds/diagnosis_map.csv`). Three data
natures are kept structurally apart:

1. **Clinical, patient grain** — TreatmentEpisode, ScreeningAssessment,
   EcgRecording. Each row is one person's record.
2. **Population benchmark** — PopulationStatistic (CSO Ireland HRA71,
   psychiatric in-patients 2001–2023). Pre-aggregated; a NULL value is a
   suppressed or not-applicable cell, never zero.
3. **Population context** — SurveyResponse. Respondents are anonymous
   members of the public, **not** Patients.

**Grain law:** patient-level facts and population-level data meet only in
`fct_diagnosis_benchmark`, only as shares, only at conformed ICD-10 group
grain. Any patient-level join to benchmark or survey data is a bug.

## Research anchors

The class split follows the constructs used by the Karolinska Institutet
Department of Global Public Health research groups
(https://ki.se/en/gph/research/research-groups-at-gph):

- **EPiCSS** (Epidemiology of Psychiatric Conditions, Substance use and
  Social Environment — Gardner/Agardh): the separation of psychiatric
  *case data* from *social-environment context* motivates SurveyResponse
  (social determinants: occupation, family history, days indoors, coping)
  as a class disjoint from Patient, and PopulationStatistic as
  registry-based epidemiology at published grain.
- **PRIME Health** (Prevention, Intervention and Mechanisms in Public
  Health — Magnusson): TreatmentEpisode models an *intervention with an
  outcome* (therapy type, medication, adherence, outcome), the unit
  intervention research reasons about.
- **GH-Pharma** (Global Health Pharmacology and Therapeutics — Aklillu):
  medication and therapy_type are first-class episode attributes so
  therapeutic comparisons stay expressible without remodelling.
- **EPHIR** (Epidemiology and Public Health Intervention Research —
  Möller): the benchmark mart's case-mix-share design (never absolute
  counts across unlike denominators) follows standard intervention-
  epidemiology practice.

## Dataset dispositions

Landed (see `data/upstream/manifest.yaml` for hashes and licenses):
treatment monitoring (Kaggle uom190346a), in-patient registry (Kaggle
noeyislearning ← CSO Ireland HRA71, CC BY 4.0), population survey (Kaggle
bhavikjikadara), disorder screening (Kaggle cid007), psychiatry ECG
features (Kaggle buraktaci — raw 12-lead signals stay out of the
warehouse; `scripts/extract_ecg_features.py` reproduces the features).

Registered as candidates, not landed (see `catalog/candidate_sources.yaml`):
Compumacy/Psych_data (226 MB conversational text corpus — NLP shape, not
relational; Apache-2.0), the multilingual mental-health NLP dataset survey
(bucuram), the ODSC dataset listicle, and the Kaggle Mental Health tag feed.
Catalogs are backlogs with admission criteria, never bulk-onboarded.

## Notable mechanics

- The survey's content-hash `surrogate_key` role drives the generated
  staging dedupe: 292,364 upstream rows → 290,051 distinct responses
  (2,313 exact duplicates). The raw table keeps full multiplicity.
- `conformed_icd10_group` folds the registry's legacy classification labels
  (pre-ICD-10 eras of HRA71) into modern groups so 2001–2023 trends hold.
- `pf check` warns that survey_responses carries two key-role columns
  (natural + surrogate); this is deliberate — response_id preserves
  upstream ordinality, content_hash defines identity.
