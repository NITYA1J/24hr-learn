"""Block 2: seeded synthetic data generator with PLANTED root causes.

Run:  python data/generate.py
Writes CSVs + truth.json (the answer key) next to this file.

Planted truths (see truth.json for the measured numbers):
  1. sensor_calibration causes ~35% of total downtime hours.
  2. Site C has a night-shift technician shortage -> backlog ~2x older.
  3. Site B has a brake-pad parts shortage in weeks 5-6 -> brake cycle time ~+60%.
  4. Region 2 (sites D, E) readiness trends down ~1.5 points/week.
  5. Site A is healthy (control).
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).parent
START = pd.Timestamp("2026-01-05")          # a Monday
DAYS = 56                                   # 8 weeks
END = START + pd.Timedelta(days=DAYS)       # data extract time (exclusive)

SITES = {  # site_id: (region, bays, mobile_units, vehicles)
    "A": ("R1", 8, 2, 60), "B": ("R1", 8, 2, 60), "C": ("R1", 8, 2, 60),
    "D": ("R2", 8, 2, 60), "E": ("R2", 8, 2, 60),
}
TARGET = 0.92
TECHS = {"A": (7, 5), "B": (7, 5), "C": (10, 2), "D": (7, 5), "E": (7, 5)}  # (day, night)

# category: (weight, median service hours)
CATS = {
    "sensor_calibration": (0.16, 3.0), "brakes": (0.12, 3.5),
    "battery_charging": (0.14, 2.5), "tires": (0.13, 1.5),
    "software_ota": (0.12, 1.0), "hvac": (0.08, 2.5), "body_damage": (0.09, 6.0),
    "steering_suspension": (0.07, 5.0), "electrical_wiring": (0.09, 3.5),
}
PART_FOR = {"sensor_calibration": "lidar_sensor", "brakes": "brake_pads",
            "battery_charging": "battery_module", "tires": "tires", "hvac": "hvac_compressor"}
BASE_RATE = 11.6          # work orders / site / day
R2_RAMP_PER_WEEK = 0.28   # region-2 arrival-rate growth per week (drives the readiness decline)
SENSOR_SHARE = 0.35
C_NIGHT_WAIT_H = 30.0      # mean extra wait for night-opened WOs at site C (PLANT 2)
BRAKE_SHORTAGE_K = 0.5     # extra parts-wait fraction for B brakes in weeks 5-6 (PLANT 3)
HOUR_W = np.array([1.0] * 6 + [2.0] * 12 + [1.4] * 6)  # night hours 18-06 get ~35% of WOs
HOUR_W = HOUR_W / HOUR_W.sum()


def is_night(h): return (h >= 18) | (h < 6)


def build(seed: int = 42):
    rng = np.random.default_rng(seed)
    cats, w = list(CATS), np.array([v[0] for v in CATS.values()])

    # ---- reference tables
    sites = pd.DataFrame([dict(site_id=s, region=r, bays=b, mobile_units=m, target_readiness=TARGET)
                          for s, (r, b, m, _) in SITES.items()])
    vehicles = pd.DataFrame([dict(vehicle_id=f"{s}-V{i:03d}", site_id=s,
                                  model_year=int(rng.choice([2022, 2023, 2024, 2025])))
                             for s, (_, _, _, n) in SITES.items() for i in range(n)])
    techs = pd.DataFrame([dict(tech_id=f"{s}-T{i:02d}", site_id=s, shift="day" if i < d else "night",
                               skill_level=int(rng.integers(1, 4)))
                          for s, (d, n) in TECHS.items() for i in range(d + n)])

    # ---- work-order skeleton
    rows = []
    for s, (region, *_ ) in SITES.items():
        for d in range(DAYS):
            lam = BASE_RATE * (1 + R2_RAMP_PER_WEEK * d / 7 if region == "R2" else 1)
            for _ in range(rng.poisson(lam)):
                hr = rng.choice(24, p=HOUR_W)
                opened = START + pd.Timedelta(days=d, hours=int(hr), minutes=int(rng.integers(0, 60)))
                rows.append((s, opened, rng.choice(cats, p=w)))
    wo = pd.DataFrame(rows, columns=["site_id", "opened_at", "failure_category"]).sort_values("opened_at", ignore_index=True)
    n = len(wo)
    wo["severity"] = rng.choice(["minor", "major", "critical"], size=n, p=[.6, .3, .1])
    wo["week"] = ((wo.opened_at - START).dt.days // 7) + 1
    night = is_night(wo.opened_at.dt.hour)

    # ---- durations (hours) = queue + service + parts wait
    med = wo.failure_category.map(lambda c: CATS[c][1]).to_numpy()
    service = 0.65 * med * rng.lognormal(0, 0.5, n)
    queue = rng.exponential(0.7, n)
    queue = queue + np.where((wo.site_id == "C") & night, rng.exponential(C_NIGHT_WAIT_H, n), 0)  # PLANT 2
    has_parts = rng.random(n) < 0.02
    parts = np.where(has_parts, rng.lognormal(np.log(60), 0.5, n), 0.0)
    # PLANT 3: site B brake-pad shortage in weeks 5-6 -> +60% cycle time, via parts wait
    shortage = ((wo.site_id == "B") & (wo.failure_category == "brakes") & wo.week.isin([5, 6])).to_numpy()
    parts = parts + np.where(shortage, BRAKE_SHORTAGE_K * (queue + service + parts), 0.0)
    wo["_queue"], wo["_service"], wo["_parts"] = queue, service, parts

    def total(): return wo._queue + wo._service + wo._parts
    def clipped_hours():
        end = wo.opened_at + pd.to_timedelta(total(), unit="h")
        return (end.clip(upper=END) - wo.opened_at).dt.total_seconds() / 3600
    # PLANT 1: scale sensor_calibration so it is ~35% of in-window downtime hours
    is_sensor = wo.failure_category == "sensor_calibration"
    for _ in range(8):
        h = clipped_hours()
        share = h[is_sensor].sum() / h.sum()
        k = (SENSOR_SHARE / (1 - SENSOR_SHARE)) / (share / (1 - share))
        wo.loc[is_sensor, ["_queue", "_service", "_parts"]] *= k

    # ---- timestamps, assignment
    closed = wo.opened_at + pd.to_timedelta(total(), unit="h")
    wo["closed_at"] = closed.where(closed <= END)
    ps = wo.opened_at + pd.to_timedelta(wo._queue + wo._service * 0.5, unit="h")
    pe = ps + pd.to_timedelta(wo._parts, unit="h")
    has = wo._parts > 0
    wo["parts_wait_start"] = ps.where(has & (ps < END))
    wo["parts_wait_end"] = pe.where(has & (pe <= END))
    wo["status"] = np.where(wo.closed_at.notna(), "closed",
                            np.where(wo.parts_wait_start.notna() & wo.parts_wait_end.isna(), "waiting_parts", "open"))
    free_at = {v: START for v in vehicles.vehicle_id}
    by_site = {s: vehicles.vehicle_id[vehicles.site_id == s].tolist() for s in SITES}
    vid = []
    for s, t0, t1 in zip(wo.site_id, wo.opened_at, wo.closed_at.fillna(END + pd.Timedelta(days=30))):
        ok = [v for v in by_site[s] if free_at[v] <= t0] or by_site[s]
        v = ok[rng.integers(len(ok))]
        free_at[v] = t1
        vid.append(v)
    wo["vehicle_id"] = vid
    tid = []
    for s, h in zip(wo.site_id, wo.opened_at.dt.hour):
        pool = techs[(techs.site_id == s) & (techs["shift"] == ("night" if is_night(h) else "day"))].tech_id.to_numpy()
        tid.append(rng.choice(pool))
    wo["tech_id"] = tid
    wo.insert(0, "wo_id", [f"WO{i:05d}" for i in range(1, n + 1)])
    wo = wo[["wo_id", "vehicle_id", "site_id", "failure_category", "severity", "opened_at",
             "parts_wait_start", "parts_wait_end", "closed_at", "tech_id", "status"]]

    # ---- daily fleet status: vehicles with an open WO at noon are down
    recs = []
    for s, (_, _, _, nveh) in SITES.items():
        w_s = wo[wo.site_id == s]
        for d in range(DAYS):
            t = START + pd.Timedelta(days=d, hours=12)
            down = int(((w_s.opened_at <= t) & (w_s.closed_at.isna() | (w_s.closed_at > t))).sum())
            recs.append(dict(date=(START + pd.Timedelta(days=d)).date().isoformat(), site_id=s,
                             vehicles_total=nveh, vehicles_available=nveh - down, vehicles_down=down))
    daily = pd.DataFrame(recs)

    # final vehicle status snapshot
    st = wo[wo.status != "closed"].set_index("vehicle_id").status
    vehicles["status"] = vehicles.vehicle_id.map(st).map({"open": "in_shop", "waiting_parts": "waiting_parts"}).fillna("in_service")

    # ---- parts availability (PLANT 3 also visible here)
    parts_rows = []
    for s in SITES:
        for wk in range(1, 9):
            for p in ["brake_pads", "lidar_sensor", "battery_module", "tires", "hvac_compressor"]:
                out = (s == "B" and p == "brake_pads" and wk in (5, 6))
                parts_rows.append(dict(part=p, site_id=s, week=wk, in_stock=not out,
                                       lead_time_days=7 if out else int(rng.integers(1, 3))))
    return sites, vehicles, techs, wo, pd.DataFrame(parts_rows), daily


def truth(wo, daily):
    h = ((wo.closed_at.fillna(END).clip(upper=END) - wo.opened_at).dt.total_seconds() / 3600)
    by_cat = h.groupby(wo.failure_category).sum()
    total_vh = sum(v[3] for v in SITES.values()) * 24 * DAYS
    age = lambda site, asof: ((asof - wo[(wo.site_id == site) & wo.opened_at.lt(asof) &
                                         (wo.closed_at.isna() | (wo.closed_at > asof))].opened_at).dt.total_seconds() / 86400)
    snaps = [START + pd.Timedelta(days=d) for d in range(7, DAYS + 1)]
    mean_age = {s: float(np.nanmean([age(s, t).mean() for t in snaps])) for s in SITES}
    b = wo[(wo.site_id == "B") & (wo.failure_category == "brakes") & wo.closed_at.notna()].copy()
    b["wk"] = ((b.opened_at - START).dt.days // 7) + 1
    ct = (b.closed_at - b.opened_at).dt.total_seconds() / 3600
    d2 = daily.assign(wk=pd.to_datetime(daily.date).sub(START).dt.days // 7,
                      r=daily.vehicles_available / daily.vehicles_total)
    region = {"R1": ["A", "B", "C"], "R2": ["D", "E"]}
    slope = {}
    for r, ss in region.items():
        wk = d2[d2.site_id.isin(ss)].groupby("wk").r.mean() * 100
        slope[r] = float(np.polyfit(wk.index, wk.values, 1)[0])
    return {
        "n_work_orders": int(len(wo)),
        "sensor_calibration_downtime_share": float(by_cat["sensor_calibration"] / by_cat.sum()),
        "readiness_points_lost_by_category": {k: float(v / total_vh * 100) for k, v in by_cat.sort_values(ascending=False).items()},
        "site_C_backlog_mean_age_days_vs_others": {"mean_age_by_site": mean_age,
            "ratio_C_to_mean_of_others": mean_age["C"] / np.mean([mean_age[s] for s in "ABDE"]),
            "note": "average of daily snapshots, days 7-56"},
        "site_B_brake_cycle_time": {"median_h_weeks_5_6": float(ct[b.wk.isin([5, 6])].median()),
            "median_h_other_weeks": float(ct[~b.wk.isin([5, 6])].median()),
            "ratio": float(ct[b.wk.isin([5, 6])].median() / ct[~b.wk.isin([5, 6])].median())},
        "region_readiness_slope_points_per_week": slope,
        "site_mean_readiness_pct": {s: float(g.vehicles_available.sum() / g.vehicles_total.sum() * 100)
                                     for s, g in daily.groupby("site_id")},
        "target_readiness_pct": TARGET * 100,
    }


if __name__ == "__main__":
    sites, vehicles, techs, wo, parts, daily = build()
    for name, df in dict(sites=sites, vehicles=vehicles, technicians=techs, work_orders=wo,
                         parts_availability=parts, daily_fleet_status=daily).items():
        df.to_csv(OUT / f"{name}.csv", index=False)
    t = truth(wo, daily)
    (OUT / "truth.json").write_text(json.dumps(t, indent=2))
    print(json.dumps(t, indent=2))
