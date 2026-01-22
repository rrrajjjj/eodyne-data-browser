# Prompt for LLM Taxonomy Generation

Use this prompt with your exported `context.json` file to generate a comprehensive data taxonomy and knowledge graph.

---

## Prompt Template

```
I have attached a context.json file representing a database schema with human-verified metadata. This file contains:

1. **Table Information**: For each table, it includes:
   - Table name and human-written description
   - All columns with their data types and descriptions
   - Sample data rows (2 rows per table) showing actual values
   - Group memberships (which groups each table belongs to)

2. **Group Hierarchy**: A flexible grouping system where:
   - Tables are organized into named groups with descriptions
   - Groups can have parent groups (creating hierarchies)
   - A group can belong to multiple parent groups (graph structure, not just a tree)
   - Groups help organize related tables semantically

3. **Column Descriptions**: Human-verified or pattern-inferred descriptions for all columns. These are global - if a column name appears in multiple tables, it has the same description everywhere.

Please analyze this file and generate a comprehensive Data Taxonomy and Knowledge Graph with the following components:

## 1. Semantic Domains
Group the tables into high-level functional areas (semantic domains). These should be broader than the existing groups and represent major business or functional areas. For example:
- Customer Management
- Order Processing
- Inventory Management
- Financial Transactions
- etc.

For each domain, provide:
- Domain name
- Description
- List of tables that belong to it
- Rationale for why these tables belong together

## 2. Enhanced Group Hierarchy
Based on the existing groups in the metadata, create an enhanced hierarchy that:
- Validates and improves the existing group structure
- Identifies missing relationships
- Suggests new parent groups if needed
- Documents the purpose of each group level

## 3. Table Relationships
Identify relationships between tables by analyzing:
- Column names (especially those ending in `_id` suggesting foreign keys)
- Shared column names across tables
- Sample data patterns (e.g., if Table A has `carrier_code` with "DHL" and Table B has `shipping_carrier` with "DHL", they're related)
- Table and column descriptions

For each relationship, specify:
- Source table and column
- Target table and column
- Relationship type (one-to-one, one-to-many, many-to-many)
- Business meaning of the relationship

## 4. Data Dictionary Enhancement
Review all column descriptions and:
- Identify any columns that still need better descriptions
- Suggest improvements for vague descriptions
- Note any inconsistencies
- Highlight columns that are particularly important (primary keys, foreign keys, status fields, etc.)

## 5. Knowledge Graph Structure
Create a knowledge graph representation showing:
- Nodes: Tables, Groups, and Semantic Domains
- Edges: Relationships between tables, group memberships, and domain assignments
- Properties: Descriptions, data types, sample values

## 6. Data Flow and Dependencies
Identify:
- Which tables depend on others (foreign key relationships)
- Data creation order (which tables must be populated before others)
- Critical data paths (important business processes that span multiple tables)

## 7. Recommendations
Provide recommendations for:
- Missing relationships that should be documented
- Tables that might need additional columns
- Groups that could be reorganized
- Any data quality concerns based on sample data

## Output Format
Please provide the output as structured JSON with the following schema:

```json
{
  "semantic_domains": [
    {
      "name": "Domain Name",
      "description": "Description of the domain",
      "tables": ["table1", "table2"],
      "rationale": "Why these tables belong together"
    }
  ],
  "enhanced_groups": {
    "group_name": {
      "description": "Enhanced description",
      "parent_groups": ["parent1", "parent2"],
      "tables": ["table1"],
      "suggestions": "Any improvements or notes"
    }
  },
  "table_relationships": [
    {
      "source_table": "table1",
      "source_column": "column1",
      "target_table": "table2",
      "target_column": "column2",
      "relationship_type": "one-to-many",
      "business_meaning": "What this relationship represents"
    }
  ],
  "data_dictionary_enhancements": [
    {
      "table": "table1",
      "column": "column1",
      "current_description": "Current description",
      "suggested_description": "Improved description",
      "reason": "Why the improvement is needed"
    }
  ],
  "knowledge_graph": {
    "nodes": [
      {
        "id": "table1",
        "type": "table",
        "label": "Table Name",
        "properties": {
          "description": "...",
          "domain": "...",
          "groups": ["..."]
        }
      }
    ],
    "edges": [
      {
        "source": "table1",
        "target": "table2",
        "type": "foreign_key",
        "properties": {
          "source_column": "...",
          "target_column": "...",
          "relationship_type": "..."
        }
      }
    ]
  },
  "data_flow": {
    "creation_order": [
      {
        "step": 1,
        "tables": ["table1"],
        "reason": "Why these tables must be created first"
      }
    ],
    "critical_paths": [
      {
        "process": "Process name",
        "tables": ["table1", "table2", "table3"],
        "description": "What this process does"
      }
    ]
  },
  "recommendations": [
    {
      "type": "missing_relationship" | "reorganization" | "data_quality" | "enhancement",
      "description": "What should be done",
      "rationale": "Why it's important"
    }
  ]
}
```

Please be thorough and use the sample data to infer meanings that might not be obvious from names alone. Pay special attention to cryptic table/column names and use the sample data to decipher them.
```

---

## Usage Instructions

1. **Export your context.json** from the Streamlit app (Tab 3: Export for LLM)

2. **Open your LLM** (Claude, GPT-4, etc.)

3. **Upload the context.json file** as an attachment

4. **Copy and paste the prompt above** into the chat

5. **Review the generated taxonomy** and iterate if needed

## Tips for Better Results

- **Provide context**: If you have domain knowledge about your business, add it to the prompt (e.g., "This is an e-commerce database for a retail company")

- **Specify priorities**: If certain relationships or domains are more important, mention them in the prompt

- **Iterate**: The first pass might miss some relationships. Review the output and ask follow-up questions like "Can you identify any additional relationships I might have missed?"

- **Validate**: Cross-check the LLM's suggestions with your actual database schema and business logic
