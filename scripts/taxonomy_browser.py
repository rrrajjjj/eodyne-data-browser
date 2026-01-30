"""
Streamlit UI to browse taxonomy.json with checkable structure and tooltips.
Run: streamlit run scripts/taxonomy_browser.py
"""
import json
import os
import html
import re
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher
import streamlit as st

try:
    import plotly.graph_objects as go
except Exception:
    go = None

DATA_FILE = "taxonomy.json"
LOGS_DIR = Path(__file__).resolve().parents[1] / "sample_logs"

LOG_SOURCES = {
    "RGSApp": LOGS_DIR / "app_sample_log.json",
    "RGSClinic": LOGS_DIR / "clinic_sample_log.json",
    "RGSWeb": LOGS_DIR / "web_sample_log.json",
}


def load_taxonomy():
    if not os.path.exists(DATA_FILE):
        st.error("taxonomy.json not found. Run `python scripts/build_taxonomy.py` first.")
        st.stop()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def tooltip_label(label: str, tooltip: str | None):
    if not tooltip:
        return label
    safe_label = html.escape(label)
    safe_tip = html.escape(tooltip)
    return f"<span title=\"{safe_tip}\">{safe_label}</span>"


def matches_search(name: str, desc: str, search: str) -> bool:
    if not search:
        return True
    hay = f"{name} {desc}".lower()
    return search.lower() in hay


GENERIC_COLUMNS = {"id", "created_at", "updated_at", "deleted_at"}


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def fuzzy_score(query: str, text: str) -> float:
    if not query or not text:
        return 0.0
    q_norm = normalize(query)
    t_norm = normalize(text)
    if not q_norm or not t_norm:
        return 0.0
    ratio = SequenceMatcher(None, q_norm, t_norm).ratio()
    ratio_compact = SequenceMatcher(None, compact(query), compact(text)).ratio()
    q_tokens = set(q_norm.split())
    t_tokens = set(t_norm.split())
    overlap = len(q_tokens & t_tokens) / max(1, len(q_tokens))
    return max(ratio, ratio_compact, overlap)


def load_log_file(path: Path):
    try:
        raw_text = path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
        # Some exports store JSON as a quoted string; try decoding twice.
        if isinstance(data, str):
            stripped = data.strip()
            if (stripped.startswith("{") and stripped.endswith("}")) or (
                stripped.startswith("[") and stripped.endswith("]")
            ):
                data = json.loads(stripped)
        return data
    except Exception as exc:
        st.error(f"Failed to load {path.name}: {exc}")
        return None


def type_name(value) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    return "string"


def truncate_value(value, max_len=120) -> str:
    if isinstance(value, (dict, list)):
        preview = json.dumps(value, ensure_ascii=False)
    else:
        preview = str(value)
    if len(preview) > max_len:
        return preview[: max_len - 1] + "…"
    return preview


def summarize_header_fields(header: dict) -> dict:
    if not isinstance(header, dict):
        return {}
    summary = {}
    for key, value in header.items():
        if isinstance(value, dict):
            summary[key] = sorted(value.keys())
        elif isinstance(value, list):
            summary[key] = value
        else:
            summary[key] = type_name(value)
    return summary


def count_event_records(payload) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        if not payload:
            return 0
        if "t" in payload or "time" in payload:
            return 1
    return 0


def summarize_event_section(section: dict, sample_limit=50) -> dict:
    if not isinstance(section, dict):
        return {}
    summary = {}
    for event_name, payload in section.items():
        info = {"type": type_name(payload)}
        if isinstance(payload, list):
            info["count"] = len(payload)
            keys = set()
            for item in payload[:sample_limit]:
                if isinstance(item, dict):
                    keys.update(item.keys())
            if keys:
                info["fields"] = sorted(keys)
        elif isinstance(payload, dict):
            info["fields"] = sorted(payload.keys())
        summary[event_name] = info
    return summary


def describe_node(value, depth=2, max_fields=40, sample_limit=50):
    if isinstance(value, dict):
        keys = sorted(value.keys())
        node = {"type": "object", "field_count": len(keys)}
        if depth > 0:
            fields = {}
            for key in keys[:max_fields]:
                fields[key] = describe_node(
                    value[key],
                    depth=depth - 1,
                    max_fields=max_fields,
                    sample_limit=sample_limit,
                )
            node["fields"] = fields
            if len(keys) > max_fields:
                node["remaining_fields"] = len(keys) - max_fields
        return node
    if isinstance(value, list):
        node = {"type": "array", "count": len(value)}
        sample = value[:sample_limit]
        if sample:
            if all(isinstance(item, dict) for item in sample):
                keys = set()
                for item in sample:
                    keys.update(item.keys())
                node["item_fields"] = sorted(keys)
            else:
                node["item_type"] = type_name(sample[0])
        return node
    return {"type": type_name(value)}


def build_outline(data: dict, depth=2):
    outline = {}
    if not isinstance(data, dict):
        return outline
    for key in sorted(data.keys()):
        outline[key] = describe_node(data[key], depth=depth)
    return outline


def build_event_catalog(data: dict):
    catalog = {}
    if not isinstance(data, dict):
        return catalog
    protocol_events = data.get("ProtocolEvents")
    if isinstance(protocol_events, dict):
        catalog["ProtocolEvents"] = summarize_event_section(protocol_events)
    data_section = data.get("Data", {})
    if isinstance(data_section, dict):
        for group_name in ("CommonEvents", "ProtocolEvents", "ObjectEvents"):
            group = data_section.get(group_name)
            if isinstance(group, dict):
                catalog[f"Data.{group_name}"] = summarize_event_section(group)
    return catalog


def build_tracking_summary(data: dict):
    summary = {}
    if not isinstance(data, dict):
        return summary
    tracking_data = data.get("TrackingData")
    if isinstance(tracking_data, dict):
        summary["TrackingData"] = describe_node(tracking_data, depth=2)
    data_section = data.get("Data", {})
    if isinstance(data_section, dict):
        if "TrackingRaw" in data_section:
            summary["TrackingRaw"] = describe_node(data_section.get("TrackingRaw"), depth=2)
        if "Kinematics" in data_section:
            summary["Kinematics"] = describe_node(data_section.get("Kinematics"), depth=2)
    return summary


def build_difficulty_summary(data: dict):
    if not isinstance(data, dict):
        return {}
    difficulty = data.get("DifficultyParameters")
    if not isinstance(difficulty, dict):
        return {}
    summary = {}
    for key in ("DirectRelations", "PerformanceEstimators", "DifficultyModulators"):
        payload = difficulty.get(key)
        if payload is not None:
            summary[key] = describe_node(payload, depth=1)
    return summary


def build_log_description(label: str, data: dict) -> list[str]:
    bullets = []
    if not isinstance(data, dict):
        return bullets
    if "LogFileDescription" in data:
        bullets.append("Log file legend and protocol-specific notes.")
    header = data.get("Header")
    if isinstance(header, dict):
        header_bits = []
        if "RgsInfo" in header:
            header_bits.append("RgsInfo metadata")
        if "SessionInfo" in header:
            header_bits.append("SessionInfo (session identifiers and timestamps)")
        if "ProtocolInfo" in header:
            header_bits.append("ProtocolInfo (protocol identifiers and device)")
        if "IRC" in header:
            header_bits.append("IRC user model configuration")
        if header_bits:
            bullets.append("Header includes " + ", ".join(header_bits) + ".")
    if "ProtocolEvents" in data:
        bullets.append("ProtocolEvents for state changes and gameplay interactions.")
    data_section = data.get("Data")
    if isinstance(data_section, dict):
        data_bits = []
        if "CommonEvents" in data_section:
            data_bits.append("CommonEvents (lifecycle + scoring)")
        if "ProtocolEvents" in data_section:
            data_bits.append("ProtocolEvents (protocol-specific cues)")
        if "ObjectEvents" in data_section:
            data_bits.append("ObjectEvents (interaction events)")
        if data_bits:
            bullets.append("Event streams include " + ", ".join(data_bits) + ".")
        if "TrackingRaw" in data_section:
            bullets.append("Raw tracking streams (body joints, sensors).")
        if "Kinematics" in data_section:
            bullets.append("Kinematics mapped into the virtual world.")
    if "DifficultyParameters" in data:
        bullets.append(
            "Difficulty parameters include performance estimators, "
            "and difficulty modulators (DMs). DMs are game parameters for dynamic difficulty adaptation."
        )
    tracking_data = data.get("TrackingData", {})
    if isinstance(tracking_data, dict):
        if "Transforms" in tracking_data:
            bullets.append("TrackingData contains AR camera transforms.")
        if "MediapipeJoints" in tracking_data:
            bullets.append("TrackingData contains Mediapipe hand joints (Hand1/Hand2).")
    return bullets


def collect_schema_paths(value, max_depth=3, max_array_items=1):
    rows = []

    def visit(node, path, depth):
        node_type = type_name(node)
        note = ""
        if node_type == "object":
            note = f"{len(node)} keys"
        elif node_type == "array":
            note = f"{len(node)} items"
        rows.append({"Path": path or "$", "Type": node_type, "Notes": note})
        if depth >= max_depth:
            return
        if isinstance(node, dict):
            for key in sorted(node.keys()):
                visit(node[key], f"{path}.{key}" if path else key, depth + 1)
        elif isinstance(node, list) and node:
            for idx, item in enumerate(node[:max_array_items]):
                visit(item, f"{path}[{idx}]" if path else f"[{idx}]", depth + 1)

    visit(value, "", 0)
    return rows


def render_table_list(tables, table_index, search, show_inline_desc):
    for t in tables:
        table_name = t["table"]
        desc = table_index.get(table_name, {}).get("description", "")
        note = t.get("note", "")
        if not matches_search(table_name, desc, search):
            continue
        label = table_name
        if show_inline_desc and desc:
            label = f"{table_name} — {desc}"
        tooltip = desc if desc else note
        st.markdown(f"- {tooltip_label(label, tooltip)}", unsafe_allow_html=True)


def render_family(family, table_index, search, show_inline_desc):
    variants = family.get("variants", [])
    if not variants:
        return
    with st.expander(f"Family: {family['family']} ({len(variants)})", expanded=False):
        for v in variants:
            desc = table_index.get(v, {}).get("description", "")
            if not matches_search(v, desc, search):
                continue
            label = v
            if show_inline_desc and desc:
                label = f"{v} — {desc}"
            st.markdown(f"- {tooltip_label(label, desc)}", unsafe_allow_html=True)


def build_sunburst(domains, table_index, table_details, max_depth):
    labels = []
    parents = []
    values = []
    ids = []
    hover = []

    def add_node(node_id, label, parent_id, value, hover_text):
        ids.append(node_id)
        labels.append(label)
        parents.append(parent_id)
        values.append(value)
        hover.append(hover_text)

    def table_name(item):
        return item.get("table") if isinstance(item, dict) else item

    # Domain -> Group -> (Subgroup) -> Family -> Table
    for domain in domains:
        domain_id = f"domain::{domain['name']}"
        domain_table_count = 0
        # Calculate tables in domain
        for group in domain["groups"]:
            group_tables = group.get("tables", [])
            group_families = group.get("table_families", [])
            count = len(group_tables) + sum(len(f["variants"]) for f in group_families)
            if group.get("subgroups"):
                for sg in group["subgroups"]:
                    count += len(sg.get("tables", [])) + sum(len(f["variants"]) for f in sg.get("table_families", []))
            domain_table_count += count
        domain_desc = domain.get("description", "") or "Domain"
        add_node(domain_id, domain["name"], "", max(domain_table_count, 1), domain_desc)

        domain_groups = domain["groups"]
        collapse_group = len(domain_groups) == 1 and domain_groups[0]["name"] == domain["name"]
        for group in domain_groups:
            group_id = f"group::{group['name']}"
            group_tables = group.get("tables", [])
            group_families = group.get("table_families", [])
            group_count = len(group_tables) + sum(len(f["variants"]) for f in group_families)
            if group.get("subgroups"):
                for sg in group["subgroups"]:
                    group_count += len(sg.get("tables", [])) + sum(len(f["variants"]) for f in sg.get("table_families", []))
            if not collapse_group:
                add_node(
                    group_id,
                    group["name"],
                    domain_id,
                    max(group_count, 1),
                    group.get("description", ""),
                )
                parent_id = group_id
            else:
                parent_id = domain_id

            if max_depth >= 2:
                flatten_families = {"session", "recording", "prescription"}
                for fam in group_families:
                    fam_id = f"family::{fam['family']}::{group['name']}"
                    if fam["family"] in flatten_families:
                        for t in fam["variants"]:
                            table_id = f"table::{t}"
                            desc = table_index.get(t, {}).get("description", "")
                            add_node(table_id, t, parent_id, 1, desc)
                    else:
                        add_node(
                            fam_id,
                            fam["family"],
                            parent_id,
                            max(len(fam["variants"]), 1),
                            "",
                        )
                        if max_depth >= 3:
                            for t in fam["variants"]:
                                table_id = f"table::{t}"
                                desc = table_index.get(t, {}).get("description", "")
                                add_node(table_id, t, fam_id, 1, desc)

                for t in group_tables:
                    if max_depth >= 2:
                        tname = table_name(t)
                        table_id = f"table::{tname}"
                        desc = table_index.get(tname, {}).get("description", "")
                        add_node(table_id, tname, parent_id, 1, desc)

                if group.get("subgroups"):
                    for sg in group["subgroups"]:
                        sg_id = f"subgroup::{sg['name']}"
                        sg_tables = sg.get("tables", [])
                        sg_families = sg.get("table_families", [])
                        sg_count = len(sg_tables) + sum(len(f["variants"]) for f in sg_families)
                        add_node(
                            sg_id,
                            sg["name"],
                            parent_id,
                            max(sg_count, 1),
                            sg.get("description", ""),
                        )
                        if max_depth >= 2:
                            flatten_families = {"session", "recording", "prescription"}
                            for fam in sg_families:
                                fam_id = f"family::{fam['family']}::{sg['name']}"
                                if fam["family"] in flatten_families:
                                    for t in fam["variants"]:
                                        table_id = f"table::{t}"
                                        desc = table_index.get(t, {}).get("description", "")
                                        add_node(table_id, t, sg_id, 1, desc)
                                else:
                                    add_node(
                                        fam_id,
                                        fam["family"],
                                        sg_id,
                                        max(len(fam["variants"]), 1),
                                        "",
                                    )
                                    if max_depth >= 3:
                                        for t in fam["variants"]:
                                            table_id = f"table::{t}"
                                            desc = table_index.get(t, {}).get("description", "")
                                            add_node(table_id, t, fam_id, 1, desc)
                            for t in sg_tables:
                                if max_depth >= 2:
                                    tname = table_name(t)
                                    table_id = f"table::{tname}"
                                    desc = table_index.get(tname, {}).get("description", "")
                                    add_node(table_id, tname, sg_id, 1, desc)

    fig = go.Figure(
        go.Sunburst(
            labels=labels,
            parents=parents,
            values=values,
            ids=ids,
            hovertext=hover,
            hoverinfo="label+text",
            hovertemplate="%{label}<br>%{hovertext}<extra></extra>",
            branchvalues="total",
            maxdepth=max_depth + 1,
        )
    )
    fig.update_layout(
        margin=dict(t=10, l=10, r=10, b=10),
        height=700,
    )
    return fig


def main():
    st.set_page_config(layout="wide", page_title="Eodyne Data Browser")
    st.title("Eodyne Data Browser")

    data = load_taxonomy()
    domains = data.get("domains", [])
    table_index = data.get("table_index", {})
    table_details = data.get("table_details", {})
    explicit_relationships = data.get("explicit_relationships", [])

    domain_names = [d["name"] for d in domains]
    group_names = []
    for d in domains:
        for g in d["groups"]:
            group_names.append(g["name"])

    st.sidebar.header("Filters")
    search = st.sidebar.text_input("Search tables", placeholder="e.g., patient, session, protocol")
    selected_domains = st.sidebar.multiselect(
        "Domains",
        options=domain_names,
        default=domain_names,
    )
    selected_groups = st.sidebar.multiselect(
        "Groups",
        options=sorted(group_names),
        default=sorted(group_names),
    )
    show_inline_desc = st.sidebar.checkbox("Show descriptions inline", value=False)
    show_misc = st.sidebar.checkbox("Show Miscellaneous domain", value=True)

    if not show_misc:
        selected_domains = [d for d in selected_domains if d != "Miscellaneous"]

    st.sidebar.caption("Hover on a table for description.")

    tab_graph, tab_browse, tab_table, tab_search, tab_logs, tab_specs = st.tabs(
        ["Graph", "Browse", "Table Explorer", "Search", "Logs", "SPECS"]
    )

    with tab_search:
        st.subheader("Search")
        query = st.text_input("Ask about your data", placeholder="e.g., delta dm")
        if query:
            results = []
            for table_name, info in table_index.items():
                table_desc = info.get("description", "")
                base_score = max(
                    fuzzy_score(query, table_name),
                    fuzzy_score(query, table_desc),
                    fuzzy_score(query, " ".join(info.get("groups", []))),
                )
                column_hits = []
                for col in table_details.get(table_name, {}).get("columns", []):
                    col_text = f"{col.get('name','')} {col.get('description','')}"
                    score = fuzzy_score(query, col_text)
                    if score >= 0.4:
                        column_hits.append((score, col.get("name", ""), col.get("description", "")))
                column_hits.sort(reverse=True, key=lambda x: x[0])
                best_column_score = column_hits[0][0] if column_hits else 0.0
                score = max(base_score, best_column_score)
                if score >= 0.35:
                    results.append((score, table_name, info, column_hits[:3]))
            results.sort(reverse=True, key=lambda x: x[0])

            if not results:
                st.info("No matches found. Try another phrasing.")
            else:
                for score, table_name, info, hits in results[:15]:
                    st.markdown(
                        f"**{table_name}** — {info.get('description','') or 'N/A'}"
                    )
                    st.caption(f"Domains: {', '.join(info.get('domains', []))} | Groups: {', '.join(info.get('groups', []))}")
                    if hits:
                        st.write("Top column matches:")
                        for h in hits:
                            st.write(f"- {h[1]}: {h[2]}")
                    st.divider()

    def render_group_content(group):
        group_tables = group.get("tables", [])
        group_families = group.get("table_families", [])
        group_desc = group.get("description", "")
        if group_desc:
            st.caption(group_desc)

        for fam in group_families:
            render_family(fam, table_index, search, show_inline_desc)

        if group_tables:
            st.subheader("Tables")
            render_table_list(group_tables, table_index, search, show_inline_desc)

        if group.get("subgroups"):
            st.subheader("Subgroups")
            for sg in group["subgroups"]:
                sg_name = sg.get("name", "")
                sg_desc = sg.get("description", "")
                sg_tables = sg.get("tables", [])
                sg_families = sg.get("table_families", [])
                sg_count = len(sg_tables) + sum(len(f["variants"]) for f in sg_families)
                with st.expander(f"{sg_name} ({sg_count})", expanded=False):
                    if sg_desc:
                        st.caption(sg_desc)
                    for fam in sg_families:
                        render_family(fam, table_index, search, show_inline_desc)
                    if sg_tables:
                        st.subheader("Tables")
                        render_table_list(sg_tables, table_index, search, show_inline_desc)

    with tab_browse:
        if search:
            st.subheader("Search Results")
            matches = []
            for name, info in table_index.items():
                desc = info.get("description", "")
                if matches_search(name, desc, search):
                    matches.append((name, info))
            if not matches:
                st.info("No tables match your search.")
            else:
                for name, info in sorted(matches):
                    label = name
                    if show_inline_desc and info.get("description"):
                        label = f"{name} — {info['description']}"
                    groups_str = ", ".join(info.get("groups", []))
                    domains_str = ", ".join(info.get("domains", []))
                    tooltip = info.get("description", "")
                    st.markdown(
                        f"- {tooltip_label(label, tooltip)} "
                        f"<span style='color:#666'>[{domains_str} / {groups_str}]</span>",
                        unsafe_allow_html=True,
                    )

        st.divider()

        for d in domains:
            if d["name"] not in selected_domains:
                continue
            st.header(d["name"])
            if len(d["groups"]) == 1 and d["groups"][0]["name"] == d["name"]:
                g = d["groups"][0]
                if g["name"] in selected_groups:
                    render_group_content(g)
                continue

            for g in d["groups"]:
                if g["name"] not in selected_groups:
                    continue
                group_tables = g.get("tables", [])
                group_families = g.get("table_families", [])
                group_count = len(group_tables) + sum(len(f["variants"]) for f in group_families)
                with st.expander(f"{g['name']} ({group_count})", expanded=False):
                    render_group_content(g)

    with tab_table:
        st.subheader("Table Explorer")
        table_names = sorted(table_index.keys())
        selected_table = st.selectbox("Select Table", table_names)
        info = table_index.get(selected_table, {})
        details = table_details.get(selected_table, {})
        st.markdown(f"**Description:** {info.get('description', '') or 'N/A'}")
        st.markdown(f"**Domains:** {', '.join(info.get('domains', []))}")
        st.markdown(f"**Groups:** {', '.join(info.get('groups', []))}")
        st.markdown(f"**Family:** {info.get('family') or '—'}")

        st.subheader("Columns")
        columns = details.get("columns", [])
        if columns:
            st.dataframe(columns, use_container_width=True, hide_index=True)
        else:
            st.info("No column details available.")

        st.subheader("Connections")
        ignore_generic = st.checkbox("Ignore generic columns in links", value=True)
        # Shared columns
        column_to_tables = defaultdict(list)
        for tname, tdetail in table_details.items():
            for col in tdetail.get("columns", []):
                col_name = col.get("name")
                if ignore_generic and col_name in GENERIC_COLUMNS:
                    continue
                if col_name:
                    column_to_tables[col_name].append(tname)

        shared = []
        for col_name, tables in column_to_tables.items():
            if selected_table in tables and len(tables) > 1:
                other_tables = [t for t in tables if t != selected_table]
                shared.append({"column": col_name, "tables": ", ".join(sorted(other_tables))})
        if shared:
            st.markdown("**Shared columns (potential links):**")
            st.dataframe(shared, use_container_width=True, hide_index=True)
        else:
            st.info("No shared columns found for this table.")

        # Explicit relationships
        related = [
            rel
            for rel in explicit_relationships
            if rel.get("source") == selected_table or rel.get("target") == selected_table
        ]
        if related:
            st.markdown("**Explicit relationships:**")
            for rel in related:
                st.write(
                    f"- {rel.get('source')} → {rel.get('target')} "
                    f"({', '.join(rel.get('columns', []))}) — {rel.get('note','')}"
                )

    with tab_graph:
        st.subheader("Hierarchy Graph")
        st.caption("Click segments to drill down. Use Table Explorer for relationship details.")
        if go is None:
            st.error("Plotly is not installed. Please install `plotly` to use the graph view.")
            return
        max_depth = st.slider("Depth", min_value=1, max_value=3, value=2)
        fig = build_sunburst(domains, table_index, table_details, max_depth=max_depth)
        st.plotly_chart(fig, use_container_width=True)

    with tab_logs:

        for label, path in LOG_SOURCES.items():
            st.header(label)
            if not path.exists():
                st.info(f"Missing sample file: {path.name}")
                continue

            data = load_log_file(path)
            if data is None:
                st.warning("Unable to read the selected log file.")
                continue
            if not isinstance(data, dict):
                st.warning("Log file root is not a JSON object.")
                st.write(f"Detected type: {type_name(data)}")
                st.code(truncate_value(data, max_len=1000))
                continue

            bullets = build_log_description(label, data)
            if bullets:
                st.markdown("**Contains**")
                for bullet in bullets:
                    st.markdown(f"- {bullet}")

            header_fields = summarize_header_fields(data.get("Header", {}))
            if header_fields:
                with st.expander("Header fields (keys only)"):
                    st.json(header_fields)

            log_desc = data.get("LogFileDescription", {})
            if isinstance(log_desc, dict):
                with st.expander("Legend & protocol notes"):
                    st.json(log_desc)

            st.markdown("**Structure (click to expand keys)**")
            st.json(build_outline(data, depth=2), expanded=False)

    with tab_specs:
        st.subheader("SPECS")
        with st.expander(
            "Dataset: Critical time window for recovery extends beyond one-year post-stroke",
            expanded=False,
        ):
            st.markdown(
                "**Source:** https://www.dropbox.com/scl/fo/3rx1iy3qx9qxa8zp6ak49/AHyapfttigu_2bAkgaocErA/Data/Belen%202019"
            )

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Patients:** ~280")
            with col2:
                st.markdown("**Unit of analysis:** patient x evaluation time")

            st.markdown("**Evaluation structure (per patient)**")
            st.markdown("- Baseline")
            st.markdown("- Post-treatment")
            st.markdown("- Follow-up")
            st.markdown("Recovery is computed between consecutive evaluations.")

            st.markdown("**Core variables (clinical recovery sheet)**")
            st.markdown("- Time since stroke (days): absolute chronicity at evaluation")
            st.markdown("- FM-UE (score): Upper Extremity Fugl–Meyer score (0–66)")
            st.markdown("- Days since recruitment (days): time since baseline (0 at baseline)")
            st.markdown("- Evaluation time (day): timestamp used for plotting/binning")
            st.markdown(
                "- Norm. Recovery rate (%): % of remaining FM-UE potential recovered per day (N/A at baseline)"
            )
            st.markdown(
                "- Chronicity at Eval (days): duplicate of time since stroke (for binning)"
            )
            st.markdown(
                "- Norm. Recovery rate proportional (%): recovery rate normalized within chronicity groups (for bar plots)"
            )

            st.markdown("**Normalized recovery rate formula**")
            st.code(
                "norm_recovery_rate = (delta_FM_UE / (66 - FM_UE_prev)) * (100 / delta_t)",
                language="text",
            )

            st.markdown("**Additional open files**")
            st.markdown("- PatientsDemographicsAndClinicalScreening.xlsx")
            st.markdown("  - Age, sex")
            st.markdown("  - Stroke type, lesion side")
            st.markdown("  - Dominance, aphasia")
            st.markdown("  - Center ID")
            st.markdown("  - Time since stroke")
            st.markdown("- ClinicalScalesAll.csv")
            st.markdown("  - FM-UE")
            st.markdown("  - CAHAI")
            st.markdown("  - Barthel Index")
            st.markdown("  - (baseline / post-treatment / follow-up)")

        with st.expander("Dataset: RGS@home", expanded=False):
            st.caption("No details added yet.")


if __name__ == "__main__":
    main()
