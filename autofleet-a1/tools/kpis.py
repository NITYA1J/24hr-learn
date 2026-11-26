"""Block 3: KPI tool library (plain pandas functions).

Every function has type hints + a docstring. The docstring IS the tool description the LLM
sees (the MCP server in server.py exposes these functions unchanged), so write them for a
model, not for yourself: say what it returns, what the units are, and when to use it.

Dates are ISO strings ("2026-02-09"). Omitted start/end = the full 8-week window.
All return JSON-serialisable dicts so a model (or a test) can read the numbers.
"""
from __future__ import annotations
import os
from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd

DATA_DIR = Path(os.environ.get("AUTOFLEET_DATA", Path(__file__).resolve().parent.parent / "data"))
WINDOW_START, WINDOW_END = pd.Timestamp("2026-01-05"), pd.Timestamp("2026-03-02")  # end exclusive


@lru_cache(maxsize=None)
def _load(name: str) -> pd.DataFrame:
    parse = {"work_orders": ["opened_at", "parts_wait_start", "parts_wait_end", "closed_at"],
             "daily_fleet_status": ["date"]}.get(name, [])
    return pd.read_csv(DATA_DIR / f"{name}.csv", parse_dates=parse)


def _win(start: str | None, end: str | None) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Inclusive date strings -> [t0, t1) timestamps, clipped to the data window."""
    t0 = pd.Timestamp(start) if start else WINDOW_START
    t1 = pd.Timestamp(end) + pd.Timedelta(days=1) if end else WINDOW_END
    return max(t0, WINDOW_START), min(t1, WINDOW_END)


def _r(x: float, nd: int = 2) -> float | None:
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), nd)


def _check_site(site: str | None) -> None:
    if site is not None and site not in set(_load("sites").site_id):
        raise ValueError(f"Unknown site '{site}'. Valid sites: {sorted(_load('sites').site_id)}")


def _downtime_hours(wo: pd.DataFrame, t0: pd.Timestamp, t1: pd.Timestamp) -> pd.Series:
    """Hours each work order kept its vehicle down inside [t0, t1). Open WOs run to t1."""
    s = wo.opened_at.clip(lower=t0)
    e = wo.closed_at.fillna(WINDOW_END).clip(upper=t1)
    return ((e - s).dt.total_seconds() / 3600).clip(lower=0)


def fleet_readiness(site: str | None = None, start: str | None = None, end: str | None = None) -> dict:
    """Fleet readiness = vehicles_available / vehicles_total (as a percent), compared with each site's target.

    Returns, per site and for the whole fleet (or one site if `site` is given): mean readiness %,
    target %, and gap in percentage points (negative = below target). Use this FIRST for questions
    about how ready the fleet is, which sites miss target, or how big the shortfall is.
    Args: site: 'A'..'E' or None for all; start/end: inclusive ISO dates, default full 8 weeks.
    """
    _check_site(site)
    t0, t1 = _win(start, end)
    d = _load("daily_fleet_status")
    d = d[(d.date >= t0) & (d.date < t1)]
    tgt = _load("sites").set_index("site_id").target_readiness * 100
    if site:
        d = d[d.site_id == site]
    rows = []
    for s, g in d.groupby("site_id"):
        rdy = g.vehicles_available.sum() / g.vehicles_total.sum() * 100
        rows.append(dict(site=s, readiness_pct=_r(rdy), target_pct=_r(tgt[s]), gap_pts=_r(rdy - tgt[s]),
                         avg_vehicles_down=_r(g.vehicles_down.mean())))
    out = {"window": [str(t0.date()), str((t1 - pd.Timedelta(days=1)).date())], "sites": rows}
    if not site:
        rdy = d.vehicles_available.sum() / d.vehicles_total.sum() * 100
        tg = (d.groupby("site_id").vehicles_total.sum() * tgt).sum() / d.vehicles_total.sum()
        out["fleet"] = dict(readiness_pct=_r(rdy), target_pct=_r(tg), gap_pts=_r(rdy - tg))
    return out


def downtime_by_category(site: str | None = None, start: str | None = None, end: str | None = None) -> dict:
    """Vehicle downtime hours by failure category, with each category's share of total downtime.

    Downtime = hours from work-order open to close (open orders count up to the end of the window).
    Returns categories sorted largest first: hours, share_pct, work_orders. Use to answer 'what causes the most downtime?'.
    Args: site: 'A'..'E' or None for all sites; start/end: inclusive ISO dates.
    """
    _check_site(site)
    t0, t1 = _win(start, end)
    wo = _load("work_orders")
    if site:
        wo = wo[wo.site_id == site]
    wo = wo.assign(h=_downtime_hours(wo, t0, t1))
    g = wo.groupby("failure_category").agg(hours=("h", "sum"), work_orders=("wo_id", "count")).sort_values("hours", ascending=False)
    tot = g.hours.sum()
    return {"total_downtime_hours": _r(tot, 1), "categories": [
        dict(category=c, hours=_r(r.hours, 1), share_pct=_r(r.hours / tot * 100, 1), work_orders=int(r.work_orders))
        for c, r in g.iterrows()]}


def service_cycle_time(site: str | None = None, category: str | None = None,
                       start: str | None = None, end: str | None = None) -> dict:
    """Service cycle time in hours (closed_at minus opened_at): median, p90 and count of CLOSED work orders opened in the window.

    Use for 'how long do repairs take?', cycle-time comparisons between sites/categories, or to check
    whether a parts shortage slowed a category (compare two date ranges). Also returns the share of
    orders that had a parts wait.
    Args: site 'A'..'E' or None; category e.g. 'brakes','sensor_calibration' or None; start/end inclusive ISO dates.
    """
    _check_site(site)
    t0, t1 = _win(start, end)
    wo = _load("work_orders")
    wo = wo[(wo.opened_at >= t0) & (wo.opened_at < t1) & wo.closed_at.notna()]
    if site:
        wo = wo[wo.site_id == site]
    if category:
        valid = set(_load("work_orders").failure_category)
        if category not in valid:
            raise ValueError(f"Unknown category '{category}'. Valid: {sorted(valid)}")
        wo = wo[wo.failure_category == category]
    h = (wo.closed_at - wo.opened_at).dt.total_seconds() / 3600
    return dict(site=site, category=category, count=int(len(wo)), median_hours=_r(h.median()),
                p90_hours=_r(h.quantile(0.9)), mean_hours=_r(h.mean()),
                pct_with_parts_wait=_r(wo.parts_wait_start.notna().mean() * 100, 1) if len(wo) else None)


def backlog_aging(site: str | None = None, as_of: str | None = None) -> dict:
    """Open work-order backlog bucketed by days open: 0-2, 3-5, 6+ days, plus mean age in days.

    A snapshot as of `as_of` (ISO date; default = end of data). The mean_age_days_avg_daily field averages the
    daily snapshots over the whole 8 weeks and is the more stable measure of chronic backlog aging.
    Use for 'where is work piling up?' and queue / technician-capacity questions.
    Args: site 'A'..'E' or None for all.
    """
    _check_site(site)
    wo = _load("work_orders")
    if site:
        wo = wo[wo.site_id == site]
    asof = pd.Timestamp(as_of) if as_of else WINDOW_END

    def open_age(t):
        o = wo[(wo.opened_at < t) & (wo.closed_at.isna() | (wo.closed_at > t))]
        return (t - o.opened_at).dt.total_seconds() / 86400
    age = open_age(asof)
    daily = [open_age(WINDOW_START + pd.Timedelta(days=d)).mean() for d in range(7, 57)]
    return dict(site=site, as_of=str(asof.date()), open_work_orders=int(len(age)),
                buckets={"0-2_days": int((age < 3).sum()), "3-5_days": int(((age >= 3) & (age < 6)).sum()),
                         "6+_days": int((age >= 6).sum())},
                mean_age_days=_r(age.mean()), mean_age_days_avg_daily=_r(np.nanmean(daily)))


def technician_productivity(site: str | None = None, start: str | None = None, end: str | None = None) -> dict:
    """Technician productivity = work orders closed per technician-shift, split by day and night shift.

    A technician works 5 of 7 days, so tech-shifts = technicians x days x 5/7. A very high rate on one
    shift with few technicians signals understaffing/overload. Returns, per site and shift: technicians,
    work orders closed, WOs per technician-shift. Use for staffing and capacity questions.
    Args: site 'A'..'E' or None for all; start/end inclusive ISO dates.
    """
    _check_site(site)
    t0, t1 = _win(start, end)
    days = (t1 - t0).days
    wo = _load("work_orders")
    wo = wo[wo.closed_at.notna() & (wo.closed_at >= t0) & (wo.closed_at < t1)]
    te = _load("technicians")
    if site:
        wo, te = wo[wo.site_id == site], te[te.site_id == site]
    wo = wo.merge(te[["tech_id", "shift"]], on="tech_id")
    rows = []
    for (s, sh), t in te.groupby(["site_id", "shift"]):
        closed = int(((wo.site_id == s) & (wo["shift"] == sh)).sum())
        shifts = len(t) * days * 5 / 7
        rows.append(dict(site=s, shift=sh, technicians=len(t), closed_work_orders=closed,
                         wos_per_tech_shift=_r(closed / shifts)))
    return {"window_days": days, "rows": rows}


def top_bottlenecks(start: str | None = None, end: str | None = None, n: int = 3, site: str | None = None) -> dict:
    """Rank failure categories by READINESS POINTS LOST (downtime hours / total vehicle-hours x 100).

    One point = 1% of the fleet's vehicle-hours lost to that cause, so the numbers sum to the total
    shortfall from 100%. Use this for 'what is preventing readiness?' / 'top causes' questions; follow up with
    fleet_readiness, backlog_aging and readiness_trend to locate WHERE and WHEN.
    Args: start/end inclusive ISO dates; n = how many to return (default 3); site optional.
    """
    _check_site(site)
    t0, t1 = _win(start, end)
    wo, sites = _load("work_orders"), _load("sites")
    veh = _load("vehicles")
    if site:
        wo, veh = wo[wo.site_id == site], veh[veh.site_id == site]
    vh = len(veh) * (t1 - t0).total_seconds() / 3600
    wo = wo.assign(h=_downtime_hours(wo, t0, t1))
    g = wo.groupby("failure_category").h.sum().sort_values(ascending=False)
    return {"total_points_lost": _r(g.sum() / vh * 100), "top": [
        dict(rank=i + 1, category=c, readiness_points_lost=_r(h / vh * 100), share_of_downtime_pct=_r(h / g.sum() * 100, 1))
        for i, (c, h) in enumerate(g.head(n).items())]}


def readiness_trend(region: str | None = None) -> dict:
    """Weekly fleet readiness (%) per region with a linear slope in percentage points per week.

    A clearly negative slope (e.g. -1.5) means readiness is deteriorating. Use for 'is it getting worse?',
    'which region is declining?' questions.
    Args: region 'R1' or 'R2', or None for both regions and the whole fleet.
    """
    if region is not None and region not in ("R1", "R2"):
        raise ValueError("Unknown region. Valid: 'R1', 'R2'")
    d = _load("daily_fleet_status").merge(_load("sites")[["site_id", "region"]], on="site_id")
    d["week"] = (d.date - WINDOW_START).dt.days // 7 + 1
    groups = {region: d[d.region == region]} if region else {"R1": d[d.region == "R1"], "R2": d[d.region == "R2"], "fleet": d}
    out = {}
    for name, g in groups.items():
        w = g.groupby("week").apply(lambda x: x.vehicles_available.sum() / x.vehicles_total.sum() * 100, include_groups=False)
        out[name] = dict(weekly_readiness_pct=[_r(v) for v in w.values],
                         slope_pts_per_week=_r(np.polyfit(w.index, w.values, 1)[0]))
    return out


TOOLS = [fleet_readiness, downtime_by_category, service_cycle_time, backlog_aging,
         technician_productivity, top_bottlenecks, readiness_trend]
