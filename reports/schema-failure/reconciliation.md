# Reconciliation report

Run: `b99b2d6457624432ba980337cbbff46c`. Status: **failed**.

Watermark before: `2012-01-07`. Watermark after: `2012-01-07`.

| Day | Status | Stage | Raw rows | Curated rows | Reason |
| :--- | :--- | :--- | ---: | ---: | :--- |
| 2012-01-03 | failed | schema_validation | unknown | unknown | ContractError: schema columns changed: expected ['date', 'precipitation', 'temp_max', 'temp_min', 'wind', 'weather'], got ['date', 'precipitation', 'temp_max', 'temp_min', 'gust', 'weather'] |

Failure: `ContractError: schema columns changed: expected ['date', 'precipitation', 'temp_max', 'temp_min', 'wind', 'weather'], got ['date', 'precipitation', 'temp_max', 'temp_min', 'gust', 'weather']`

Failed prepublication checks compare raw against the candidate Parquet. Successful checks compare raw against the read-back S3 curated object.
