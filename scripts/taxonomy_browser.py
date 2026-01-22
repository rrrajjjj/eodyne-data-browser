"""
Streamlit UI to browse taxonomy.json with checkable structure and tooltips.
Run: streamlit run scripts/taxonomy_browser.py
"""
import json
import os
import html
import re
from collections import defaultdict
from difflib import SequenceMatcher
import streamlit as st

try:
    import plotly.graph_objects as go
except Exception:
    go = None

DATA_FILE = "taxonomy.json"


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

    tab_graph, tab_browse, tab_table, tab_search = st.tabs(
        ["Graph", "Browse", "Table Explorer", "Search"]
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


if __name__ == "__main__":
    main()
