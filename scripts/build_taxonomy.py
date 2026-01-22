"""
Build a human-friendly taxonomy from context.json.
Outputs:
  - taxonomy.json (structured, machine-readable)
  - taxonomy.md (compact, human-readable)
"""
from __future__ import annotations

import json
from typing import Dict, List

INPUT_FILE = "context.json"
OUTPUT_JSON = "taxonomy.json"
OUTPUT_MD = "taxonomy.md"

SUFFIXES = {"app", "clinic", "home", "icu", "plus", "web"}

DOMAIN_GROUPS = {
    "RGS Core": [
        "Patient",
        "Clinician",
        "Hospital",
        "Prescriptions",
        "sessions",
        "Recordings",
        "patient_aisn_data",
    ],
    "Clinical Trial": [
        "AISN",
    ],
    "Engagement and Coaching": [
        "AI Coach",
        "EmotionalSlider",
    ],
    "Difficulty Adaptation and Performance": [
        "Difficulty Adaptation and Performance",
    ],
    "Measurements and Features": [
        "Kinematic Features",
    ],
    "Predictive Analytics": [
        "RecSys",
        "SaddlePoint",
    ],
    "RGS Housekeeping": [
        "RGS Housekeeping",
    ],
    "Miscellaneous": [
        "Miscellaneous",
    ],
}

GROUP_DESCRIPTIONS = {
    "AI Coach": "Coaching messages, schedules, and commitment tracking.",
    "AISN": "AISN clinical trial context (no direct tables).",
    "Clinician": "Clinician profiles, activities, and patient/protocol links.",
    "Difficulty Adaptation and Performance": "Adaptive difficulty settings, parameters, and performance estimators.",
    "EmotionalSlider": "Emotional questionnaires and evaluations.",
    "Hospital": "Hospital organizations, subscriptions, software/protocol links.",
    "Kinematic Features": "Kinematic features captured from sessions (e.g., displacement, volume, surfaces).",
    "Patient": "Patient profiles, devices, diagnoses, language, and subscriptions.",
    "Prescriptions": "Prescriptions across application contexts.",
    "RGS Housekeeping": "Reference entities: protocols, platforms, software, versions.",
    "RecSys": "Recommendation system data, metrics, notes, and staging.",
    "Recordings": "Recordings across application contexts.",
    "SaddlePoint": "Predictive analytics (SPS) sources, diagnosis, prognosis.",
    "patient_aisn_data": "AISN-specific patient data.",
    "sessions": "Sessions across application contexts.",
    "Miscellaneous": "Ungrouped or uncategorized tables.",
}

UNCATEGORIZED_NOTES = {
    "clinical_data": "Likely raw clinical inputs or measurements.",
    "code": "Generic code/reference table.",
    "code_redemption": "Code usage or redemption tracking.",
    "control_plus": "Control/telemetry data for plus variant.",
    "device_cloud_messaging": "Device messaging or telemetry stream.",
    "metric_app": "Metrics captured from app.",
    "metric_plus": "Metrics captured from plus variant.",
    "prediction_data_source_clinical": "Clinical data source for predictions.",
    "prescription_change_reason": "Reasons for prescription changes.",
    "reference_date_wear": "Reference dates for wear data.",
    "station": "Device or station metadata.",
    "tree": "Generic hierarchy/tree structure.",
}

MISC_SUBGROUP_DESCRIPTIONS = {
    "Clinical and Data Sources": "Clinical source data and clinical prediction sources.",
    "Device and Telemetry": "Device, station, and telemetry related tables.",
    "Metrics and Monitoring": "Metrics captured from applications.",
    "Codes and Reference": "Codes, code usage, and reference structures.",
    "Prescription Support": "Supporting data for prescription changes.",
    "Other": "Miscellaneous tables that do not fit other subgroups.",
}

TABLE_DESCRIPTION_OVERRIDES = {
    "patient": "Main patient table at signup with identity and demographic fields.",
    "patient_aisn_data": "AISN-related patient data (experimental group, demographics, start date).",
    "clinical_trials": "Clinical trial scores and assessments for enrolled patients.",
    "prescription_staging": "Recsys-staged prescriptions awaiting clinician approval.",
    "prescription_plus": "Clinician-approved prescriptions (moved from staging).",
    "recsys_metrics": "Metrics used by the recommender system (delta_dm, adherence, PPF, etc.).",
    "recsys_intrinsic_measures": "Clinic evaluation milestones (baseline, end, follow-up).",
    "recsys_diagnostic": "Home diagnostic evaluation schedules for RGS app protocols.",
    "recsys_notes": "Clinician notes associated with recommender system output.",
    "prescription_change_reason": "Reasons for prescription changes.",
}

FAMILY_DESCRIPTION_OVERRIDES = {
    "session": "Session instances tied to prescriptions (id, status, timing).",
    "recording": "Session recordings including duration and other capture metrics.",
    "parameter": "Last logged difficulty modulator for a session.",
    "difficulty_modulators": "Time series of difficulty modulator values per patient/protocol.",
    "performance_estimators": "Time series of performance estimators used to adapt difficulty.",
    "prescription": "Prescriptions across app/clinic/home/plus/web contexts.",
    "metric": "Kinematic feature measurements (e.g., displacement, volume, surface area).",
}

TABLE_GROUP_SET = {
    "metric_app": ["Kinematic Features"],
    "metric_plus": ["Kinematic Features"],
    "prescription_change_reason": ["Prescriptions", "RecSys"],
}

TABLE_GROUP_ADD = {
    "patient_aisn_data": ["AISN"],
    "clinical_trials": ["AISN"],
}

EXPLICIT_RELATIONSHIPS = [
    {
        "source": "patient",
        "target": "hospital",
        "columns": ["hospital_id"],
        "type": "foreign_key",
        "note": "Each patient is assigned to a hospital.",
    },
    {
        "source": "recsys_metrics",
        "target": "prescription_staging",
        "columns": ["recommendation_id"],
        "type": "reference",
        "note": "Recsys metrics are tied to staged prescriptions.",
    },
]


def titleize(name: str) -> str:
    return name.replace("_", " ").title()


def family_name(table: str) -> str | None:
    parts = table.split("_")
    if parts and parts[-1] in SUFFIXES:
        return "_".join(parts[:-1])
    return None


def apply_table_description(table_name: str, default_desc: str) -> str:
    override = TABLE_DESCRIPTION_OVERRIDES.get(table_name)
    if override:
        return override
    fam = family_name(table_name)
    if fam and fam in FAMILY_DESCRIPTION_OVERRIDES:
        return FAMILY_DESCRIPTION_OVERRIDES[fam]
    return default_desc


def parse_column(col_str: str) -> Dict[str, str]:
    # Expected format: "name (TYPE): description"
    name = col_str
    data_type = ""
    description = ""
    if " (" in col_str:
        name, rest = col_str.split(" (", 1)
        if "):" in rest:
            data_type, description = rest.split("):", 1)
        elif ")" in rest:
            data_type, description = rest.split(")", 1)
        else:
            data_type = rest
    return {
        "name": name.strip(),
        "data_type": data_type.strip(),
        "description": description.strip().lstrip(":").strip(),
    }


def build_families(tables: List[str]) -> Dict[str, List[str]]:
    counts: Dict[str, int] = {}
    for t in tables:
        fam = family_name(t)
        if fam:
            counts[fam] = counts.get(fam, 0) + 1
    families: Dict[str, List[str]] = {}
    for t in tables:
        fam = family_name(t)
        if fam and counts.get(fam, 0) > 1:
            families.setdefault(fam, []).append(t)
    for fam in families:
        families[fam] = sorted(families[fam])
    return families


def build_taxonomy() -> None:
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    groups = data.get("metadata", {}).get("groups", {})
    tables = data.get("tables", [])

    # Map table -> description from context
    table_descriptions: Dict[str, str] = {}
    for t in tables:
        table_descriptions[t["table"]] = apply_table_description(
            t["table"], t.get("description", "")
        )

    # Map table -> groups (apply overrides)
    table_to_groups: Dict[str, List[str]] = {}
    for t in tables:
        name = t["table"]
        base_groups = list(t.get("groups", []))
        if name in TABLE_GROUP_SET:
            group_list = list(TABLE_GROUP_SET[name])
        else:
            group_list = base_groups
            additions = TABLE_GROUP_ADD.get(name, [])
            for g in additions:
                if g not in group_list:
                    group_list.append(g)
        table_to_groups[name] = sorted(set(group_list))

    # Identify ungrouped tables
    ungrouped = [name for name, group_list in table_to_groups.items() if not group_list]

    # Normalize group metadata and ensure required groups exist
    normalized_groups: Dict[str, Dict[str, List[str]]] = {}
    for gname, gdata in groups.items():
        normalized_groups[gname] = {
            "description": gdata.get("description", ""),
            "parent_groups": gdata.get("parent_groups", []),
            "tables": [],
        }

    for gname in GROUP_DESCRIPTIONS.keys():
        if gname not in normalized_groups:
            normalized_groups[gname] = {
                "description": GROUP_DESCRIPTIONS[gname],
                "parent_groups": [],
                "tables": [],
            }

    # Build group tables from table_to_groups
    for table_name, group_list in table_to_groups.items():
        for gname in group_list:
            if gname not in normalized_groups:
                normalized_groups[gname] = {
                    "description": GROUP_DESCRIPTIONS.get(gname, ""),
                    "parent_groups": [],
                    "tables": [],
                }
            normalized_groups[gname]["tables"].append(table_name)

    # Add Miscellaneous group
    normalized_groups["Miscellaneous"]["tables"] = sorted(ungrouped)

    # AISN is a clinical trial context, not a parent umbrella for other groups
    for gname, gdata in normalized_groups.items():
        if gname != "AISN":
            parents = gdata.get("parent_groups", [])
            gdata["parent_groups"] = [p for p in parents if p != "AISN"]

    # Build misc subgroups under the Miscellaneous umbrella
    misc_subgroups: Dict[str, List[str]] = {}
    for table in ungrouped:
        if table in ("metric_app", "metric_plus"):
            bucket = "Metrics and Monitoring"
        elif table in ("clinical_data", "prediction_data_source_clinical"):
            bucket = "Clinical and Data Sources"
        elif table in ("device_cloud_messaging", "station", "control_plus", "reference_date_wear"):
            bucket = "Device and Telemetry"
        elif table in ("code", "code_redemption", "tree"):
            bucket = "Codes and Reference"
        elif table in ("prescription_change_reason",):
            bucket = "Prescription Support"
        else:
            bucket = "Other"
        misc_subgroups.setdefault(bucket, []).append(table)

    for bucket in misc_subgroups:
        misc_subgroups[bucket] = sorted(misc_subgroups[bucket])

    # Build taxonomy domains
    domains = []
    for domain_name, domain_groups in DOMAIN_GROUPS.items():
        domain_obj = {
            "name": domain_name,
            "description": "",
            "groups": [],
        }
        for group_name in domain_groups:
            group_data = normalized_groups.get(group_name, {})
            group_tables = sorted(group_data.get("tables", []))
            families = build_families(group_tables)
            # Standalone tables are those not in a family
            family_tables = {t for fam in families.values() for t in fam}
            standalone = [t for t in group_tables if t not in family_tables]

            group_obj = {
                "name": group_name,
                "description": GROUP_DESCRIPTIONS.get(group_name, group_data.get("description", "")),
                "table_families": [
                    {
                        "family": fam,
                        "label": titleize(fam),
                        "variants": families[fam],
                    }
                    for fam in sorted(families.keys())
                ],
                "tables": [
                    {
                        "table": t,
                        "label": titleize(t),
                        "note": UNCATEGORIZED_NOTES.get(t, ""),
                    }
                    for t in standalone
                ],
                "subgroups": [],
            }

            if group_name == "Miscellaneous":
                # Do not show all miscellaneous tables at the group level
                group_obj["tables"] = []
                group_obj["table_families"] = []
                subgroups = []
                for bucket in sorted(misc_subgroups.keys()):
                    bucket_tables = misc_subgroups[bucket]
                    bucket_families = build_families(bucket_tables)
                    bucket_family_tables = {t for fam in bucket_families.values() for t in fam}
                    bucket_standalone = [t for t in bucket_tables if t not in bucket_family_tables]
                    subgroups.append(
                        {
                            "name": bucket,
                            "description": MISC_SUBGROUP_DESCRIPTIONS.get(bucket, ""),
                            "table_families": [
                                {
                                    "family": fam,
                                    "label": titleize(fam),
                                    "variants": bucket_families[fam],
                                }
                                for fam in sorted(bucket_families.keys())
                            ],
                            "tables": [
                                {
                                    "table": t,
                                    "label": titleize(t),
                                    "note": UNCATEGORIZED_NOTES.get(t, ""),
                                }
                                for t in bucket_standalone
                            ],
                        }
                    )
                group_obj["subgroups"] = subgroups
            domain_obj["groups"].append(group_obj)
        domains.append(domain_obj)

    # Build table index for quick lookup
    domain_by_group = {}
    for d in domains:
        for g in d["groups"]:
            domain_by_group[g["name"]] = d["name"]

    table_index = {}
    table_details = {}
    table_names = {t["table"] for t in tables}
    for t in tables:
        name = t["table"]
        groups_for_table = table_to_groups.get(name, [])
        if not groups_for_table:
            groups_for_table = ["Miscellaneous"]
        domains_for_table = sorted({domain_by_group.get(g, "Miscellaneous") for g in groups_for_table})
        description = table_descriptions.get(name, "")
        columns = [parse_column(c) for c in t.get("columns", [])]
        table_index[name] = {
            "label": titleize(name),
            "description": description,
            "groups": groups_for_table,
            "domains": domains_for_table,
            "family": family_name(name) or "",
        }
        table_details[name] = {
            "description": description,
            "columns": columns,
        }

    explicit_relationships = list(EXPLICIT_RELATIONSHIPS)

    def add_family_relationship(source_family: str, target_family: str, column: str, note: str) -> None:
        for suffix in SUFFIXES:
            source = f"{source_family}_{suffix}"
            target = f"{target_family}_{suffix}"
            if source in table_names and target in table_names:
                explicit_relationships.append(
                    {
                        "source": source,
                        "target": target,
                        "columns": [column],
                        "type": "foreign_key",
                        "note": note,
                    }
                )

    add_family_relationship(
        "session",
        "prescription",
        "prescription_id",
        "Each session corresponds to a prescription.",
    )
    add_family_relationship(
        "recording",
        "session",
        "session_id",
        "Each recording corresponds to a session.",
    )
    add_family_relationship(
        "parameter",
        "session",
        "session_id",
        "Parameter contains the last logged difficulty modulator for a session.",
    )
    add_family_relationship(
        "performance_estimators",
        "difficulty_modulators",
        "session_id",
        "Performance estimators inform difficulty modulator updates.",
    )

    taxonomy = {
        "taxonomy_version": "1.0",
        "source": INPUT_FILE,
        "goals": [
            "Make browsing intuitive and non-overwhelming",
            "Make it easy to identify what a table represents",
            "Provide a clean hierarchy with table families",
        ],
        "domains": domains,
        "group_hierarchy": normalized_groups,
        "table_index": table_index,
        "table_details": table_details,
        "explicit_relationships": explicit_relationships,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(taxonomy, f, indent=2)

    # Build a compact markdown summary
    lines: List[str] = []
    lines.append("# Taxonomy Summary")
    lines.append("")
    for d in domains:
        lines.append(f"## {d['name']}")
        for g in d["groups"]:
            lines.append(f"- {g['name']}: {g['description']}")
            for fam in g["table_families"]:
                lines.append(f"  - Family: {fam['family']} -> {', '.join(fam['variants'])}")
            if g["tables"]:
                lines.append("  - Tables: " + ", ".join([t["table"] for t in g["tables"]]))
            if g.get("subgroups"):
                for sg in g["subgroups"]:
                    lines.append(f"  - {sg['name']}: {sg['description']}")
                    for fam in sg["table_families"]:
                        lines.append(f"    - Family: {fam['family']} -> {', '.join(fam['variants'])}")
                    if sg["tables"]:
                        lines.append("    - Tables: " + ", ".join([t["table"] for t in sg["tables"]]))
        lines.append("")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote {OUTPUT_JSON} and {OUTPUT_MD}")


if __name__ == "__main__":
    build_taxonomy()
