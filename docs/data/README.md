# Data Folder

**Purpose:** Sample data files and example queries for testing and demonstration

---

## Contents

### Sample SQL Queries

**Sample1-Query.sql** (3.7KB)
- Example SQL query for testing data engine
- Demonstrates complex query patterns
- Use for manual testing of SQL execution

**Sample2-Query.sql** (802 bytes)
- Additional SQL example
- Simpler query pattern
- Use for basic SQL validation

---

## Usage

### Testing Data Engine

```bash
# Load sample query
curl -X POST http://localhost:8000/api/sessions/create

# Execute query from sample file
cat docs/data/Sample1-Query.sql | \
  curl -X POST http://localhost:8000/api/sessions/{session_id}/query \
    -H "Content-Type: application/json" \
    -d @-
```

### Development

Use these samples for:
- Manual testing of SQL endpoints
- Validating query execution
- Performance benchmarking
- Example queries for documentation

---

## Adding New Samples

### Guidelines

1. **Naming:** Use descriptive names (e.g., `SampleCustomerAnalysis-Query.sql`)
2. **Format:** Plain SQL files with `.sql` extension
3. **Comments:** Include comments explaining query purpose
4. **Size:** Keep under 10KB for quick loading
5. **Complexity:** Vary from simple to complex for different test scenarios

### Example

```sql
-- Sample Query: Customer Analysis
-- Purpose: Demonstrate JOIN and aggregation
-- Complexity: Medium

SELECT
    c.customer_id,
    c.name,
    COUNT(o.order_id) as order_count,
    SUM(o.total) as total_spent
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_spent DESC
LIMIT 10;
```

---

## Future Additions

### Planned Sample Data

- CSV sample files (customer data, sales data)
- Excel sample files (multi-sheet examples)
- JSON sample files (nested structure examples)
- Parquet sample files (big data examples)

### Sample Use Cases

- Data analysis workflows
- ETL pipeline examples
- Report generation samples
- Dashboard query templates

---

## Related Documentation

- **Data Engine:** `/docs/architecture/SYSTEM_ARCHITECTURE.md` (Section: Neutron Star Engine)
- **SQL/JSON Migration:** `/docs/migrations/completed/COMPLETE_MIGRATION_HISTORY.md`
- **Database Schema:** `/docs/database/SCHEMA.md`

---

**Last Updated:** 2025-11-12
**Maintainer:** ElohimOS Team
