"""
Script to generate context.json from data_dictionary_state.json
This can be run independently if you need to regenerate the export file.
"""
import json
import pandas as pd
from collections import defaultdict

# File paths
STATE_FILE = 'data_dictionary_state.json'
OUTPUT_FILE = 'context.json'

def generate_context_json():
    """Generate context.json from the saved state file"""
    
    # Load the state
    print(f"Loading state from {STATE_FILE}...")
    with open(STATE_FILE, 'r') as f:
        state = json.load(f)
    
    # Build table to groups mapping
    table_to_groups = {}
    groups = state.get('groups', {})
    for group_name, group_data in groups.items():
        for table in group_data.get('tables', []):
            if table not in table_to_groups:
                table_to_groups[table] = []
            table_to_groups[table].append(group_name)
    
    # Get all tables
    tables = sorted(list(state['table_desc'].keys()))
    
    # Build the export structure
    print("Generating export structure...")
    final_export = {
        "metadata": {
            "groups": groups,
            "export_timestamp": pd.Timestamp.now().isoformat()
        },
        "tables": []
    }
    
    # Process each table
    for t in tables:
        # Gather columns for this table
        t_cols = [x for x in state['schema'] if x['TABLE_NAME'] == t]
        col_details = []
        for col in t_cols:
            c_name = col['COLUMN_NAME']
            col_desc = state['master_dict'].get(c_name, 'No description')
            col_details.append(f"{c_name} ({col['DATA_TYPE']}): {col_desc}")
        
        # Add sample data (just the values, formatted for tokens)
        samples = state['samples'].get(t, [])
        
        # Get groups this table belongs to
        table_groups = table_to_groups.get(t, [])
        
        final_export["tables"].append({
            "table": t,
            "description": state['table_desc'].get(t, "N/A"),
            "groups": table_groups,
            "columns": col_details,
            "sample_rows": samples[:2]  # Limit to 2 rows to save tokens
        })
    
    # Write the output file
    print(f"Writing to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_export, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully generated {OUTPUT_FILE}!")
    print(f"   - {len(final_export['tables'])} tables")
    print(f"   - {len(groups)} groups")
    print(f"   - Export timestamp: {final_export['metadata']['export_timestamp']}")

if __name__ == "__main__":
    try:
        generate_context_json()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"   Make sure {STATE_FILE} exists in the current directory.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
