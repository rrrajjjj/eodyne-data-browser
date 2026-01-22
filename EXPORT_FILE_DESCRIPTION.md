# Context.json File Structure Description

This document describes the structure of the `context.json` file exported from the Data Dictionary Builder tool. This file contains comprehensive metadata about your database schema, including human-verified descriptions, groupings, and sample data.

## Overall Structure

The exported JSON file has the following top-level structure:

```json
{
  "metadata": { ... },
  "tables": [ ... ]
}
```

## 1. Metadata Section

The `metadata` object contains:

### 1.1 Groups (`metadata.groups`)
A dictionary where each key is a group name and the value is a group object with:
- **`description`** (string): Human-written description of what this group represents
- **`parent_groups`** (array of strings): List of parent group names. A group can have multiple parents, creating a flexible hierarchy (not just a tree structure)
- **`tables`** (array of strings): List of table names that belong to this group

**Example:**
```json
{
  "Customer Data": {
    "description": "All tables related to customer information and profiles",
    "parent_groups": ["Core Data"],
    "tables": ["customers", "customer_addresses", "customer_preferences"]
  },
  "Core Data": {
    "description": "Fundamental business entities",
    "parent_groups": [],
    "tables": []
  }
}
```

**Key Points:**
- Groups can be hierarchical (groups can have parent groups)
- A group can belong to multiple parent groups (graph structure, not just a tree)
- Parent groups may not directly contain tables (they organize child groups)
- Groups without parent_groups are "root groups"

### 1.2 Export Timestamp (`metadata.export_timestamp`)
ISO 8601 formatted timestamp indicating when the export was generated.

## 2. Tables Section

The `tables` array contains one object for each table in the database. Each table object has:

### 2.1 Table Name (`table`)
The name of the database table (string).

### 2.2 Table Description (`description`)
Human-verified description of what the table contains and its purpose. May be "N/A" if not yet described.

### 2.3 Groups (`groups`)
Array of group names (strings) that this table belongs to. A table can belong to multiple groups.

### 2.4 Columns (`columns`)
Array of strings, where each string describes a column in the format:
```
"column_name (DATA_TYPE): description"
```

**Example:**
```json
[
  "customer_id (INT): Unique identifier",
  "email (VARCHAR): Email address",
  "created_at (DATETIME): Timestamp when the record was created"
]
```

**Key Points:**
- Column descriptions are human-verified or auto-generated based on naming patterns
- Data types are included to help understand the column's purpose
- Descriptions may include sample values if they were available during profiling (e.g., "Status or state of the record (e.g., Active, Inactive, Pending)")

### 2.5 Sample Rows (`sample_rows`)
Array of objects, where each object represents a sample row from the table. Contains up to 2 sample rows to provide context about actual data values.

**Example:**
```json
[
  {
    "customer_id": "123",
    "email": "john@example.com",
    "status": "Active",
    "created_at": "2024-01-15 10:30:00"
  },
  {
    "customer_id": "124",
    "email": "jane@example.com",
    "status": "Inactive",
    "created_at": "2024-01-16 14:20:00"
  }
]
```

**Key Points:**
- Sample data is crucial for understanding the semantic meaning of columns
- Values are converted to strings for JSON serialization
- Only 2 rows are included to save tokens when sending to LLMs
- Sample data helps disambiguate cryptic column names (e.g., seeing "DHL", "FedEx" in a column helps identify it as a shipping carrier)

## Complete Example

```json
{
  "metadata": {
    "groups": {
      "Customer Data": {
        "description": "All tables related to customer information",
        "parent_groups": ["Core Data"],
        "tables": ["customers", "customer_addresses"]
      },
      "Core Data": {
        "description": "Fundamental business entities",
        "parent_groups": [],
        "tables": []
      }
    },
    "export_timestamp": "2024-01-20T15:30:45.123456"
  },
  "tables": [
    {
      "table": "customers",
      "description": "Main customer table storing customer profiles and contact information",
      "groups": ["Customer Data"],
      "columns": [
        "customer_id (INT): Primary key identifier",
        "email (VARCHAR): Email address",
        "first_name (VARCHAR): Customer's first name",
        "last_name (VARCHAR): Customer's last name",
        "status (VARCHAR): Status or state of the record (e.g., Active, Inactive)",
        "created_at (DATETIME): Timestamp when the record was created"
      ],
      "sample_rows": [
        {
          "customer_id": "123",
          "email": "john@example.com",
          "first_name": "John",
          "last_name": "Doe",
          "status": "Active",
          "created_at": "2024-01-15 10:30:00"
        }
      ]
    }
  ]
}
```

## How to Use This for Taxonomy Generation

When providing this file to an LLM for taxonomy generation, the LLM should:

1. **Analyze the Group Hierarchy**: Understand how tables are organized into groups and how groups relate to each other through parent-child relationships.

2. **Infer Semantic Domains**: Group tables into functional areas based on:
   - Existing group structure
   - Table descriptions
   - Column names and descriptions
   - Sample data values

3. **Identify Relationships**: Look for:
   - Foreign key relationships (columns ending in `_id` that might reference other tables)
   - Shared column names across tables (indicating relationships)
   - Sample data patterns (e.g., if Table A has `carrier_code` with values "DHL", "FedEx" and Table B has `shipping_carrier` with the same values, they're likely related)

4. **Create a Knowledge Graph**: Build a structure showing:
   - Semantic domains/categories
   - Table-to-table relationships
   - Column-to-column mappings
   - Data flow and dependencies

5. **Enhance Descriptions**: Use the sample data and context to improve or validate existing descriptions, especially for cryptic table/column names.

## Important Notes

- **Human-Verified Content**: The descriptions in this file have been reviewed and verified by humans, making them more reliable than auto-generated descriptions alone.

- **Sample Data Context**: The sample rows are critical for understanding the actual meaning of data. A column named `v_code` is meaningless until you see it contains "DHL", "FedEx" - then it's clearly a vendor/shipping carrier code.

- **Group Hierarchy**: The groups structure represents a flexible hierarchy where:
  - Root groups have no parents
  - Child groups can have multiple parents (allowing for cross-cutting concerns)
  - Groups can organize both tables and other groups

- **Column Descriptions**: These are global - if `status` is defined once, it applies to all tables that have a `status` column. This reduces redundancy and ensures consistency.
