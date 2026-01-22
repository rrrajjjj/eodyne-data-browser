# Taxonomy Summary

## RGS Core
- Patient: Patient profiles, devices, diagnoses, language, and subscriptions.
  - Family: patient_language -> patient_language_app, patient_language_plus
  - Tables: patient, patient_affectation, patient_affectation_features, patient_aisn_data, patient_device_data, patient_diagnosis_data, patient_inactivity, patient_privacy_policy, patient_software, patient_subscription
- Clinician: Clinician profiles, activities, and patient/protocol links.
  - Tables: clinician, clinician_activity, clinician_activity_patient, clinician_activity_protocol, clinician_patient, clinician_privacy_policy
- Hospital: Hospital organizations, subscriptions, software/protocol links.
  - Tables: hospital, hospital_clinician, hospital_project, hospital_software, hospital_subscription, protocol_hospital, protocol_software_hospital
- Prescriptions: Prescriptions across application contexts.
  - Family: prescription -> prescription_app, prescription_clinic, prescription_home, prescription_plus, prescription_web
  - Tables: prescription_change_reason
- sessions: Sessions across application contexts.
  - Family: session -> session_app, session_clinic, session_home, session_icu, session_plus, session_web
- Recordings: Recordings across application contexts.
  - Family: recording -> recording_app, recording_clinic, recording_home, recording_icu, recording_plus, recording_web
- patient_aisn_data: AISN-specific patient data.
  - Tables: patient_aisn_data

## Clinical Trial
- AISN: AISN clinical trial context (no direct tables).
  - Tables: clinical_trials, patient_aisn_data

## Engagement and Coaching
- AI Coach: Coaching messages, schedules, and commitment tracking.
  - Tables: coach_messages, coach_messages_per_patient, coach_messages_per_protocol, coach_messages_schedule_per_patient, coach_status, coach_training_time, commitment_answer, commitment_question, commitment_question_patient
- EmotionalSlider: Emotional questionnaires and evaluations.
  - Tables: emotional_answer, emotional_question, emotional_question_patient, evaluation

## Difficulty Adaptation and Performance
- Difficulty Adaptation and Performance: Adaptive difficulty settings, parameters, and performance estimators.
  - Family: difficulty_modulators -> difficulty_modulators_app, difficulty_modulators_plus
  - Family: difficulty_settings -> difficulty_settings_app, difficulty_settings_plus
  - Family: parameter -> parameter_app, parameter_clinic, parameter_home, parameter_icu, parameter_plus, parameter_web
  - Family: performance_estimators -> performance_estimators_app, performance_estimators_plus

## Measurements and Features
- Kinematic Features: Kinematic features captured from sessions (e.g., displacement, volume, surfaces).
  - Family: metric -> metric_app, metric_plus

## Predictive Analytics
- RecSys: Recommendation system data, metrics, notes, and staging.
  - Tables: clinical_trials, prescription_change_reason, prescription_staging, recsys_diagnostic, recsys_intrinsic_measures, recsys_metrics, recsys_notes
- SaddlePoint: Predictive analytics (SPS) sources, diagnosis, prognosis.
  - Tables: prediction_data_source_sps, sps_diagnosis, sps_prediction_source, sps_prognosis

## RGS Housekeeping
- RGS Housekeeping: Reference entities: protocols, platforms, software, versions.
  - Tables: activity, affectation, component, distributor, platform, privacy_policy, protocol, protocol_device_support, protocol_platform, protocol_software, protocol_type, software, version_matching

## Miscellaneous
- Miscellaneous: Ungrouped or uncategorized tables.
  - Clinical and Data Sources: Clinical source data and clinical prediction sources.
    - Tables: clinical_data, prediction_data_source_clinical
  - Codes and Reference: Codes, code usage, and reference structures.
    - Tables: code, code_redemption, tree
  - Device and Telemetry: Device, station, and telemetry related tables.
    - Tables: control_plus, device_cloud_messaging, reference_date_wear, station
