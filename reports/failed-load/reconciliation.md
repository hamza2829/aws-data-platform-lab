# Reconciliation report

Run: `ed5474ed1c464510b6fed91b96e02163`. Status: **failed**.

Watermark before: `None`. Watermark after: `2012-01-02`.

| Day | Status | Stage | Raw rows | Curated rows | Reason |
| :--- | :--- | :--- | ---: | ---: | :--- |
| 2012-01-01 | passed | readback_reconciliation | 1 | 1 | counts and all sums agree |
| 2012-01-01 / precipitation | sum | readback_reconciliation | 0.0 | 0.0 | compared exactly |
| 2012-01-01 / temp_max | sum | readback_reconciliation | 12.8 | 12.8 | compared exactly |
| 2012-01-01 / temp_min | sum | readback_reconciliation | 5.0 | 5.0 | compared exactly |
| 2012-01-01 / wind | sum | readback_reconciliation | 4.7 | 4.7 | compared exactly |
| 2012-01-02 | passed | readback_reconciliation | 1 | 1 | counts and all sums agree |
| 2012-01-02 / precipitation | sum | readback_reconciliation | 10.9 | 10.9 | compared exactly |
| 2012-01-02 / temp_max | sum | readback_reconciliation | 10.6 | 10.6 | compared exactly |
| 2012-01-02 / temp_min | sum | readback_reconciliation | 2.8 | 2.8 | compared exactly |
| 2012-01-02 / wind | sum | readback_reconciliation | 4.5 | 4.5 | compared exactly |
| 2012-01-03 | failed | prepublication_reconciliation | 1 | 0 | ValueError: reconciliation mismatch: row count: raw=1, curated=0; precipitation sum: raw=0.8, curated=0.0; temp_max sum: raw=11.7, curated=0.0; temp_min sum: raw=7.2, curated=0.0; wind sum: raw=2.3, curated=0.0 |
| 2012-01-03 / precipitation | sum | prepublication_reconciliation | 0.8 | 0.0 | compared exactly |
| 2012-01-03 / temp_max | sum | prepublication_reconciliation | 11.7 | 0.0 | compared exactly |
| 2012-01-03 / temp_min | sum | prepublication_reconciliation | 7.2 | 0.0 | compared exactly |
| 2012-01-03 / wind | sum | prepublication_reconciliation | 2.3 | 0.0 | compared exactly |

Failure: `ValueError: reconciliation mismatch: row count: raw=1, curated=0; precipitation sum: raw=0.8, curated=0.0; temp_max sum: raw=11.7, curated=0.0; temp_min sum: raw=7.2, curated=0.0; wind sum: raw=2.3, curated=0.0`

Failed prepublication checks compare raw against the candidate Parquet. Successful checks compare raw against the read-back S3 curated object.
