# AutoFleet schema and KPI definitions

| Table | Columns |
|---|---|
| `sites` | site_id, region, bays, mobile_units, target_readiness |
| `vehicles` | vehicle_id, site_id, model_year, status (in_service / in_shop / waiting_parts) |
| `technicians` | tech_id, site_id, shift (day/night), skill_level |
| `work_orders` | wo_id, vehicle_id, site_id, failure_category, severity, opened_at, parts_wait_start, parts_wait_end, closed_at, tech_id, status |
| `parts_availability` | part, site_id, week, in_stock, lead_time_days |
| `daily_fleet_status` | date, site_id, vehicles_total, vehicles_available, vehicles_down |

Sites A-E; region R1 = A,B,C; R2 = D,E. Window: 2026-01-05 to 2026-03-01 (8 weeks, Monday start).

## KPIs
- **Fleet readiness** = vehicles_available / vehicles_total per site per day; compare to `target_readiness`.
- **Service cycle time** = closed_at - opened_at (median and p90, closed orders only).
- **Backlog aging** = open work orders bucketed by days open (0-2, 3-5, 6+).
- **Technician productivity** = work orders closed per technician-shift.
- **Readiness points lost by cause** = downtime hours of a category / total vehicle-hours x 100.
