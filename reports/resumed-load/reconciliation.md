# Reconciliation report

Run: `b4bbce9fafec41c4b9cf2d7a131d0af8`. Status: **succeeded**.

Watermark before: `2012-01-02`. Watermark after: `2012-01-07`.

| Day | Status | Stage | Raw rows | Curated rows | Reason |
| :--- | :--- | :--- | ---: | ---: | :--- |
| 2012-01-03 | passed | readback_reconciliation | 1 | 1 | counts and all sums agree |
| 2012-01-03 / precipitation | sum | readback_reconciliation | 0.8 | 0.8 | compared exactly |
| 2012-01-03 / temp_max | sum | readback_reconciliation | 11.7 | 11.7 | compared exactly |
| 2012-01-03 / temp_min | sum | readback_reconciliation | 7.2 | 7.2 | compared exactly |
| 2012-01-03 / wind | sum | readback_reconciliation | 2.3 | 2.3 | compared exactly |
| 2012-01-04 | passed | readback_reconciliation | 1 | 1 | counts and all sums agree |
| 2012-01-04 / precipitation | sum | readback_reconciliation | 20.3 | 20.3 | compared exactly |
| 2012-01-04 / temp_max | sum | readback_reconciliation | 12.2 | 12.2 | compared exactly |
| 2012-01-04 / temp_min | sum | readback_reconciliation | 5.6 | 5.6 | compared exactly |
| 2012-01-04 / wind | sum | readback_reconciliation | 4.7 | 4.7 | compared exactly |
| 2012-01-05 | passed | readback_reconciliation | 1 | 1 | counts and all sums agree |
| 2012-01-05 / precipitation | sum | readback_reconciliation | 1.3 | 1.3 | compared exactly |
| 2012-01-05 / temp_max | sum | readback_reconciliation | 8.9 | 8.9 | compared exactly |
| 2012-01-05 / temp_min | sum | readback_reconciliation | 2.8 | 2.8 | compared exactly |
| 2012-01-05 / wind | sum | readback_reconciliation | 6.1 | 6.1 | compared exactly |
| 2012-01-06 | passed | readback_reconciliation | 1 | 1 | counts and all sums agree |
| 2012-01-06 / precipitation | sum | readback_reconciliation | 2.5 | 2.5 | compared exactly |
| 2012-01-06 / temp_max | sum | readback_reconciliation | 4.4 | 4.4 | compared exactly |
| 2012-01-06 / temp_min | sum | readback_reconciliation | 2.2 | 2.2 | compared exactly |
| 2012-01-06 / wind | sum | readback_reconciliation | 2.2 | 2.2 | compared exactly |
| 2012-01-07 | passed | readback_reconciliation | 1 | 1 | counts and all sums agree |
| 2012-01-07 / precipitation | sum | readback_reconciliation | 0.0 | 0.0 | compared exactly |
| 2012-01-07 / temp_max | sum | readback_reconciliation | 7.2 | 7.2 | compared exactly |
| 2012-01-07 / temp_min | sum | readback_reconciliation | 2.8 | 2.8 | compared exactly |
| 2012-01-07 / wind | sum | readback_reconciliation | 2.3 | 2.3 | compared exactly |

Failed prepublication checks compare raw against the candidate Parquet. Successful checks compare raw against the read-back S3 curated object.
