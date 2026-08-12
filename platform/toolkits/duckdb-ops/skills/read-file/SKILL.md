---
name: read-file
description: Profile a data file (CSV, JSON, Parquet, Excel, spatial, SQLite) from local or cloud storage before ingesting it.
---
# Reading files

Profile before you scaffold a pipeline. Guessing a schema is how a filesystem
source ends up with every column typed VARCHAR.

```sql
DESCRIBE SELECT * FROM read_csv('data.csv', sample_size=-1);
SELECT count(*) FROM 'data.csv';
FROM 'data.parquet' SELECT * LIMIT 5;
SELECT * FROM read_json_auto('nested.json');
```

Remote: `s3://`, `gs://`, `az://`, `https://` via the `httpfs` extension.
Credentials go through `secrets_update_fragment`, never inline in a query.

Hand the profile to `create-filesystem-pipeline`: column names, types, null rates,
row count, and any column that looks like a key, a timestamp or money — those
become the annotation roles.
