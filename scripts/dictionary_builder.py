import streamlit as st
import pandas as pd
import json
import os
import re
from collections import defaultdict

# --- DATA LOADING & SAVING ---
DATA_FILE = 'data_dictionary_state.json'
RAW_FILE = 'raw_profile.json'

def generate_starter_description(column_name, data_type=None, sample_values=None):
    """
    Generate a starter description based on column name patterns and sample data.
    Uses heuristics to infer common column meanings.
    """
    col_lower = column_name.lower()
    
    # Common patterns with their descriptions
    patterns = {
        # IDs
        r'.*_id$': lambda m: "Unique identifier",
        r'^id$': lambda m: "Primary key identifier",
        
        # Timestamps
        r'.*_at$': lambda m: "Timestamp indicating when the record was created or updated",
        r'.*created.*': lambda m: "Timestamp when the record was created",
        r'.*updated.*': lambda m: "Timestamp when the record was last updated",
        r'.*date$': lambda m: "Date value",
        r'.*time$': lambda m: "Time value",
        r'.*datetime$': lambda m: "Date and time value",
        
        # Status/State
        r'.*status$': lambda m: "Status or state of the record",
        r'.*state$': lambda m: "State of the record",
        r'.*flag$': lambda m: "Boolean flag indicator",
        r'.*active$': lambda m: "Whether the record is active",
        
        # Names
        r'.*name$': lambda m: "Name of the entity",
        r'.*_name$': lambda m: "Name field",
        r'^name$': lambda m: "Name",
        r'.*title$': lambda m: "Title of the entity",
        
        # Email/Contact
        r'.*email$': lambda m: "Email address",
        r'.*phone$': lambda m: "Phone number",
        r'.*address$': lambda m: "Address information",
        
        # Codes
        r'.*code$': lambda m: "Code or identifier",
        r'.*_code$': lambda m: "Code value",
        
        # Counts/Amounts
        r'.*count$': lambda m: "Count or quantity",
        r'.*amount$': lambda m: "Monetary amount",
        r'.*price$': lambda m: "Price value",
        r'.*cost$': lambda m: "Cost value",
        r'.*total$': lambda m: "Total value",
        r'.*quantity$': lambda m: "Quantity or count",
        
        # Descriptions/Notes
        r'.*description$': lambda m: "Description or details",
        r'.*note$': lambda m: "Notes or comments",
        r'.*comment$': lambda m: "Comments or remarks",
        r'.*detail$': lambda m: "Detailed information",
        
        # User/Person
        r'.*user.*': lambda m: "User-related information",
        r'.*person.*': lambda m: "Person-related information",
        r'.*customer.*': lambda m: "Customer-related information",
        r'.*client.*': lambda m: "Client-related information",
        
        # Type/Category
        r'.*type$': lambda m: "Type or category classification",
        r'.*category$': lambda m: "Category classification",
        r'.*class$': lambda m: "Classification",
        
        # Order/Sequence
        r'.*order$': lambda m: "Order or sequence number",
        r'.*rank$': lambda m: "Ranking or position",
        r'.*sort$': lambda m: "Sort order",
        
        # URLs/Paths
        r'.*url$': lambda m: "URL or web address",
        r'.*path$': lambda m: "File or directory path",
        r'.*link$': lambda m: "Link or reference",
    }
    
    # Try to match patterns
    for pattern, desc_func in patterns.items():
        if re.match(pattern, col_lower):
            base_desc = desc_func(None)
            
            # Enhance with sample data if available
            if sample_values:
                unique_samples = set(str(v).strip() for v in sample_values if v and str(v).strip())
                if len(unique_samples) <= 5 and len(unique_samples) > 0:
                    samples_str = ", ".join(list(unique_samples)[:5])
                    return f"{base_desc} (e.g., {samples_str})"
            
            return base_desc
    
    # If no pattern matches, try to infer from column name structure
    # Split on underscores and capitalize
    if '_' in column_name:
        words = column_name.split('_')
        # Remove common suffixes
        words = [w for w in words if w not in ['id', 'code', 'num', 'no']]
        if words:
            inferred = ' '.join(w.capitalize() for w in words)
            return f"{inferred} field"
    
    # Last resort: capitalize and add "field"
    if column_name:
        inferred = column_name.replace('_', ' ').title()
        return f"{inferred} field"
    
    return ""

def build_column_to_tables_mapping(schema):
    """Build a mapping from column names to the tables they belong to."""
    col_to_tables = defaultdict(list)
    for item in schema:
        col_to_tables[item['COLUMN_NAME']].append(item['TABLE_NAME'])
    return col_to_tables

def load_state():
    # If we have saved progress, load it
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            state = json.load(f)
            # Ensure column_to_tables exists for backward compatibility
            if 'column_to_tables' not in state:
                state['column_to_tables'] = build_column_to_tables_mapping(state['schema'])
            # Ensure groups exists for backward compatibility
            if 'groups' not in state:
                state['groups'] = {}
            return state
    
    # Otherwise, initialize from raw profile
    if os.path.exists(RAW_FILE):
        with open(RAW_FILE, 'r') as f:
            raw = json.load(f)
            
        # Build column to tables mapping
        col_to_tables = build_column_to_tables_mapping(raw['schema'])
        
        # Create Master Column Dictionary with starter descriptions
        unique_cols = set(x['COLUMN_NAME'] for x in raw['schema'])
        master_dict = {}
        
        # Group schema by column name for sample data lookup
        col_schema_map = defaultdict(list)
        for item in raw['schema']:
            col_schema_map[item['COLUMN_NAME']].append(item)
        
        for col in unique_cols:
            # Get sample values for this column from all tables
            sample_values = []
            for table in col_to_tables[col]:
                if table in raw['samples']:
                    for row in raw['samples'][table]:
                        if col in row:
                            sample_values.append(row[col])
            
            # Get data type (use first occurrence)
            data_type = col_schema_map[col][0]['DATA_TYPE'] if col_schema_map[col] else None
            
            # Generate starter description
            starter_desc = generate_starter_description(col, data_type, sample_values[:10])
            master_dict[col] = starter_desc
        
        # Table Descriptions
        unique_tables = set(x['TABLE_NAME'] for x in raw['schema'])
        table_desc = {t: "" for t in unique_tables}
        
        # Initialize groups structure
        # Format: {group_name: {"description": "", "parent_groups": [group_names], "tables": [table_names]}}
        groups = {}
        
        return {
            "master_dict": master_dict,
            "table_desc": table_desc,
            "schema": raw['schema'],
            "samples": raw['samples'],
            "column_to_tables": dict(col_to_tables),
            "groups": groups
        }

state = load_state()

def save_state():
    with open(DATA_FILE, 'w') as f:
        json.dump(state, f)
    st.toast("Progress Saved!", icon="💾")

# --- UI LAYOUT ---
st.set_page_config(layout="wide")
st.title("Taxonomy Curator")

if state is None:
    st.error("❌ No data found! Please run `data_profiler.py` first to generate `raw_profile.json`.")
    st.stop()

tab0, tab1, tab2, tab3 = st.tabs(["0. Table Grouping", "1. Global Dictionary (Bulk Edit)", "2. Table Review", "3. Export for LLM"])

# --- TAB 0: TABLE GROUPING ---
with tab0:
    st.markdown("### Organize Tables into Groups")
    st.info("💡 Select tables using checkboxes, then click 'Create Group'. Same for grouping groups into parent groups.")
    
    # Ensure groups structure exists
    if 'groups' not in state:
        state['groups'] = {}
    
    groups = state['groups']
    all_tables = sorted(list(state['table_desc'].keys()))
    
    # Initialize session state for selections
    if 'selected_tables' not in st.session_state:
        st.session_state.selected_tables = set()
    if 'selected_groups' not in st.session_state:
        st.session_state.selected_groups = set()
    
    # Create two main sections: Tables and Groups
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📊 Tables")
        st.caption(f"Total: {len(all_tables)} tables | Selected: {len(st.session_state.selected_tables)}")
        
        # Select All / Deselect All buttons
        col_select1, col_select2 = st.columns(2)
        with col_select1:
            if st.button("Select All Tables", use_container_width=True):
                st.session_state.selected_tables = set(all_tables)
                st.rerun()
        with col_select2:
            if st.button("Deselect All", use_container_width=True):
                st.session_state.selected_tables = set()
                st.rerun()
        
        st.divider()
        
        # Display all tables with checkboxes
        # Use columns to create a grid layout
        num_cols = 2
        for i in range(0, len(all_tables), num_cols):
            cols = st.columns(num_cols)
            for j, table in enumerate(all_tables[i:i+num_cols]):
                with cols[j]:
                    is_selected = table in st.session_state.selected_tables
                    checked = st.checkbox(
                        table,
                        value=is_selected,
                        key=f"table_cb_{table}",
                        help=state['table_desc'].get(table, "No description")
                    )
                    # Update selection state
                    if checked:
                        st.session_state.selected_tables.add(table)
                    else:
                        st.session_state.selected_tables.discard(table)
        
        # Create group from selected tables
        st.divider()
        selected_count = len(st.session_state.selected_tables)
        
        if selected_count > 0:
            st.info(f"✓ {selected_count} table(s) selected")
        else:
            st.warning("No tables selected. Check the boxes above to select tables.")
        
        with st.form("create_group_from_tables", clear_on_submit=True):
            group_name = st.text_input("Group Name", key="new_group_name", placeholder="e.g., Customer Data, Orders, etc.")
            group_description = st.text_area("Group Description (optional)", key="new_group_desc", height=80)
            
            # Re-check selected count inside form (form context might have different state)
            current_selected = len(st.session_state.selected_tables)
            
            # Only disable if no tables selected (group name validation happens in submit handler)
            create_group_btn = st.form_submit_button(
                f"➕ Create Group with {current_selected} Selected Table(s)",
                disabled=current_selected == 0,
                use_container_width=True
            )
            
            if create_group_btn:
                group_name_clean = group_name.strip() if group_name else ""
                if not group_name_clean:
                    st.error("Please provide a group name.")
                elif group_name_clean in groups:
                    st.error(f"Group '{group_name_clean}' already exists! Please choose a different name.")
                else:
                    selected_tables_list = list(st.session_state.selected_tables.copy())
                    groups[group_name_clean] = {
                        "description": group_description.strip() if group_description else "",
                        "parent_groups": [],
                        "tables": selected_tables_list
                    }
                    save_state()
                    st.session_state.selected_tables = set()  # Clear selection
                    st.success(f"Group '{group_name_clean}' created with {len(selected_tables_list)} table(s)!")
                    st.rerun()
    
    with col2:
        st.subheader("📁 Groups")
        st.caption(f"Total: {len(groups)} groups | Selected: {len(st.session_state.selected_groups)}")
        
        if groups:
            # Select All / Deselect All buttons
            col_select1, col_select2 = st.columns(2)
            with col_select1:
                if st.button("Select All Groups", use_container_width=True, key="select_all_groups"):
                    st.session_state.selected_groups = set(groups.keys())
                    st.rerun()
            with col_select2:
                if st.button("Deselect All", use_container_width=True, key="deselect_all_groups"):
                    st.session_state.selected_groups = set()
                    st.rerun()
            
            st.divider()
            
            # Display all groups with checkboxes
            group_names = sorted(list(groups.keys()))
            for group_name in group_names:
                group_data = groups[group_name]
                tables = group_data.get("tables", [])
                desc = group_data.get("description", "")
                parents = group_data.get("parent_groups", [])
                
                is_selected = group_name in st.session_state.selected_groups
                checked = st.checkbox(
                    f"**{group_name}** ({len(tables)} tables)" + (f" ← {', '.join(parents)}" if parents else ""),
                    value=is_selected,
                    key=f"group_cb_{group_name}",
                    help=desc if desc else f"Contains {len(tables)} table(s)"
                )
                # Update selection state
                if checked:
                    st.session_state.selected_groups.add(group_name)
                else:
                    st.session_state.selected_groups.discard(group_name)
            
            # Create parent group from selected groups
            st.divider()
            selected_groups_count = len(st.session_state.selected_groups)
            
            if selected_groups_count > 0:
                st.info(f"✓ {selected_groups_count} group(s) selected")
            else:
                st.warning("No groups selected. Check the boxes above to select groups.")
            
            with st.form("create_parent_group", clear_on_submit=True):
                parent_group_name = st.text_input("Parent Group Name", key="new_parent_group_name", placeholder="e.g., Core Data, External Systems")
                parent_group_desc = st.text_area("Parent Group Description (optional)", key="new_parent_group_desc", height=80)
                
                # Re-check selected count inside form
                current_selected_groups = len(st.session_state.selected_groups)
                
                # Only disable if no groups selected (name validation happens in submit handler)
                create_parent_btn = st.form_submit_button(
                    f"🔗 Create Parent Group for {current_selected_groups} Selected Group(s)",
                    disabled=current_selected_groups == 0,
                    use_container_width=True
                )
                
                if create_parent_btn:
                    parent_group_name_clean = parent_group_name.strip() if parent_group_name else ""
                    if not parent_group_name_clean:
                        st.error("Please provide a parent group name.")
                    elif parent_group_name_clean in groups:
                        st.error(f"Group '{parent_group_name_clean}' already exists! Please choose a different name.")
                    else:
                        # Create new parent group
                        groups[parent_group_name_clean] = {
                            "description": parent_group_desc.strip() if parent_group_desc else "",
                            "parent_groups": [],
                            "tables": []  # Parent groups don't directly contain tables
                        }
                        
                        # Set selected groups as children
                        selected_groups_list = list(st.session_state.selected_groups.copy())
                        for child_group in selected_groups_list:
                            if parent_group_name_clean not in groups[child_group].get("parent_groups", []):
                                if "parent_groups" not in groups[child_group]:
                                    groups[child_group]["parent_groups"] = []
                                groups[child_group]["parent_groups"].append(parent_group_name_clean)
                        
                        save_state()
                        st.session_state.selected_groups = set()  # Clear selection
                        st.success(f"Parent group '{parent_group_name_clean}' created with {len(selected_groups_list)} child group(s)!")
                        st.rerun()
        else:
            st.info("No groups created yet. Select tables on the left to create your first group.")
    
    st.divider()
    
    # Display all groups with edit/delete options
    if groups:
        st.subheader("Group Details & Management")
        
        # Group management section
        for group_name in sorted(groups.keys()):
            group_data = groups[group_name]
            tables = group_data.get("tables", [])
            desc = group_data.get("description", "")
            parents = group_data.get("parent_groups", [])
            
            with st.expander(f"📁 **{group_name}** ({len(tables)} tables)" + (f" ← {', '.join(parents)}" if parents else "")):
                col_edit1, col_edit2, col_edit3 = st.columns([2, 1, 1])
                
                with col_edit1:
                    # Edit description
                    new_desc = st.text_area(
                        "Description",
                        value=desc,
                        key=f"edit_desc_{group_name}",
                        height=60
                    )
                    if new_desc != desc:
                        group_data["description"] = new_desc
                        save_state()
                
                with col_edit2:
                    # Edit tables
                    current_tables = group_data.get("tables", [])
                    updated_tables = st.multiselect(
                        "Tables",
                        options=all_tables,
                        default=current_tables,
                        key=f"edit_tables_{group_name}"
                    )
                    if set(updated_tables) != set(current_tables):
                        group_data["tables"] = updated_tables
                        save_state()
                
                with col_edit3:
                    # Edit parent groups
                    available_parents = [g for g in groups.keys() if g != group_name]
                    current_parents = group_data.get("parent_groups", [])
                    updated_parents = st.multiselect(
                        "Parent Groups",
                        options=available_parents,
                        default=current_parents,
                        key=f"edit_parents_{group_name}",
                        help="Groups this group belongs to"
                    )
                    if set(updated_parents) != set(current_parents):
                        group_data["parent_groups"] = updated_parents
                        save_state()
                    
                    # Delete button
                    if st.button("🗑️ Delete", key=f"delete_{group_name}", use_container_width=True):
                        # Remove from other groups' parent lists
                        for g in groups.values():
                            if group_name in g.get("parent_groups", []):
                                g["parent_groups"].remove(group_name)
                        del groups[group_name]
                        save_state()
                        st.success(f"Group '{group_name}' deleted!")
                        st.rerun()
                
                # Show tables in group
                if tables:
                    st.caption(f"**Tables in this group:** {', '.join(tables)}")
                else:
                    st.caption("No tables in this group")

# --- TAB 1: GLOBAL DICTIONARY ---
with tab1:
    st.markdown("### Define columns once, apply everywhere.")
    st.info("💡 If you see 'st_col', define it here as 'Status Column'. All tables with 'st_col' will inherit this.")
    
    # Build dataframe with column name, tables, and description
    col_data = []
    for col_name, desc in state['master_dict'].items():
        tables = state.get('column_to_tables', {}).get(col_name, [])
        tables_str = ", ".join(sorted(set(tables))) if tables else "N/A"
        col_data.append({
            'Column Name': col_name,
            'Tables': tables_str,
            'Description': desc
        })
    
    df_master = pd.DataFrame(col_data)
    
    # Data Editor allows bulk copy-paste from Excel
    edited_df = st.data_editor(
        df_master, 
        num_rows="dynamic", 
        use_container_width=True, 
        height=500,
        column_config={
            "Column Name": st.column_config.TextColumn("Column Name", width="medium"),
            "Tables": st.column_config.TextColumn("Tables", width="large", disabled=True),
            "Description": st.column_config.TextColumn("Description", width="large")
        },
        hide_index=True
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Update Global Dictionary"):
            # Convert back to dict
            state['master_dict'] = dict(zip(edited_df['Column Name'], edited_df['Description']))
            save_state()
            st.success("Dictionary updated!")
    
    with col2:
        if st.button("🔄 Regenerate Starter Descriptions"):
            # Regenerate descriptions for empty or auto-generated ones
            col_to_tables = state.get('column_to_tables', {})
            col_schema_map = defaultdict(list)
            for item in state['schema']:
                col_schema_map[item['COLUMN_NAME']].append(item)
            
            updated_count = 0
            for col_name in state['master_dict'].keys():
                # Get sample values
                sample_values = []
                for table in col_to_tables.get(col_name, []):
                    if table in state['samples']:
                        for row in state['samples'][table]:
                            if col_name in row:
                                sample_values.append(row[col_name])
                
                # Get data type
                data_type = col_schema_map[col_name][0]['DATA_TYPE'] if col_schema_map[col_name] else None
                
                # Generate new description
                new_desc = generate_starter_description(col_name, data_type, sample_values[:10])
                
                # Only update if current description is empty or looks auto-generated
                current_desc = state['master_dict'][col_name]
                if not current_desc or current_desc.endswith(" field") or "field" in current_desc.lower():
                    state['master_dict'][col_name] = new_desc
                    updated_count += 1
            
            save_state()
            st.success(f"Regenerated {updated_count} descriptions!")

# --- TAB 2: TABLE REVIEW ---
with tab2:
    st.markdown("### Review specific tables and sample data")
    
    # Selector
    tables = sorted(list(state['table_desc'].keys()))
    selected_table = st.selectbox("Select Table", tables)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Table Description Input
        current_desc = state['table_desc'].get(selected_table, "")
        new_desc = st.text_area("Table Description", value=current_desc, height=100)
        if new_desc != current_desc:
            state['table_desc'][selected_table] = new_desc
            save_state()
        
        # Show which groups this table belongs to
        groups = state.get('groups', {})
        table_groups = [g for g, g_data in groups.items() if selected_table in g_data.get('tables', [])]
        if table_groups:
            st.subheader("Groups")
            for group_name in table_groups:
                group_desc = groups[group_name].get('description', '')
                if group_desc:
                    st.write(f"**{group_name}**: {group_desc}")
                else:
                    st.write(f"**{group_name}**")
        else:
            st.info("This table is not assigned to any groups yet. Use the 'Table Grouping' tab to assign it.")
            
        # Show Sample Data (Crucial for Context!)
        st.subheader("Sample Data")
        if selected_table in state['samples'] and state['samples'][selected_table]:
            st.dataframe(pd.DataFrame(state['samples'][selected_table]).head(3))
        else:
            st.warning("No sample data found.")

    with col2:
        # Column View
        st.subheader("Columns")
        
        # Prepare table specific data
        table_cols = [x for x in state['schema'] if x['TABLE_NAME'] == selected_table]
        
        display_data = []
        for col in table_cols:
            c_name = col['COLUMN_NAME']
            # Inherit from Master Dict
            global_desc = state['master_dict'].get(c_name, "")
            display_data.append({
                "Column": c_name,
                "Type": col['DATA_TYPE'],
                "Description": global_desc # Editable
            })
            
        df_table_cols = pd.DataFrame(display_data)
        
        # Allow overriding specific columns for this table only? 
        # For simplicity, we just edit the global dict here for now, 
        # but in a pro tool, you'd separate "Global" vs "Local" desc.
        edited_table_cols = st.data_editor(
            df_table_cols, 
            column_config={
                "Description": st.column_config.TextColumn("Description (Global)", width="large")
            },
            hide_index=True,
            key=f"editor_{selected_table}"
        )
        
        # Sync changes back to global dict
        # (Note: In a real app, you might want a 'Save' button to prevent lag)
        changed = False
        for index, row in edited_table_cols.iterrows():
            if state['master_dict'][row['Column']] != row['Description']:
                state['master_dict'][row['Column']] = row['Description']
                changed = True
        
        if changed:
            save_state()

# --- TAB 3: EXPORT ---
with tab3:
    st.markdown("### Ready for the LLM?")
    st.write("This generates the Context JSON. Upload this file to Claude/GPT-4 to build your Semantic Graph.")
    
    # Build table to groups mapping
    table_to_groups = {}
    groups = state.get('groups', {})
    for group_name, group_data in groups.items():
        for table in group_data.get('tables', []):
            if table not in table_to_groups:
                table_to_groups[table] = []
            table_to_groups[table].append(group_name)
    
    if st.button("Generate Final Context JSON"):
        final_export = {
            "metadata": {
                "groups": groups,
                "export_timestamp": pd.Timestamp.now().isoformat()
            },
            "tables": []
        }
        
        for t in tables:
            # Gather columns for this table
            t_cols = [x for x in state['schema'] if x['TABLE_NAME'] == t]
            col_details = []
            for col in t_cols:
                c_name = col['COLUMN_NAME']
                col_details.append(f"{c_name} ({col['DATA_TYPE']}): {state['master_dict'].get(c_name, 'No description')}")
            
            # Add sample data (just the values, formatted for tokens)
            samples = state['samples'].get(t, [])
            
            # Get groups this table belongs to
            table_groups = table_to_groups.get(t, [])
            
            final_export["tables"].append({
                "table": t,
                "description": state['table_desc'].get(t, "N/A"),
                "groups": table_groups,
                "columns": col_details,
                "sample_rows": samples[:2] # Limit to 2 rows to save tokens
            })
        
        json_str = json.dumps(final_export, indent=2)
        st.download_button("Download Context.json", json_str, "context.json", "application/json")
        
        # Show summary
        st.success("Export generated!")
        st.info(f"📊 Exported {len(final_export['tables'])} tables, {len(groups)} groups")