# Data quality warnings
Use when: counts look inconsistent, work orders have no close time, or failure codes are spelled differently.
Actions: 1) Deduplicate work orders by vehicle, category and open time. 2) Normalise failure-code spellings to the controlled list. 3) Flag work orders open longer than 30 days as probable missing closes. 4) Report the share of affected records alongside any KPI. 5) Fix the intake form so the problem stops at the source.
Owner: Data owner. Review: weekly.
