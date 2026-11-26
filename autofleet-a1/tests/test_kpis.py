"""Block 3 done-criterion: every planted truth is recovered by a tool (checked against data/truth.json)."""
import json
from pathlib import Path
from tools import kpis as k

TRUTH = json.loads((Path(__file__).resolve().parent.parent / "data" / "truth.json").read_text())


def test_1_sensor_calibration_is_35pct_of_downtime():
    top = k.top_bottlenecks(n=3)["top"]
    assert top[0]["category"] == "sensor_calibration"
    assert abs(top[0]["share_of_downtime_pct"] - 35.0) < 0.5
    assert top[0]["readiness_points_lost"] > 2 * top[1]["readiness_points_lost"]


def test_2_site_c_backlog_is_about_2x_and_night_is_understaffed():
    c, others = k.backlog_aging("C")["mean_age_days_avg_daily"], [k.backlog_aging(s)["mean_age_days_avg_daily"] for s in "ABDE"]
    assert 1.6 <= c / (sum(others) / 4) <= 2.5
    rows = {(r["site"], r["shift"]): r for r in k.technician_productivity()["rows"]}
    assert rows[("C", "night")]["technicians"] == 2
    assert rows[("C", "night")]["wos_per_tech_shift"] > 2 * rows[("A", "night")]["wos_per_tech_shift"]


def test_3_site_b_brake_cycle_time_up_about_60pct_in_weeks_5_6():
    late = k.service_cycle_time("B", "brakes", "2026-02-02", "2026-02-15")["median_hours"]
    early = k.service_cycle_time("B", "brakes", "2026-01-05", "2026-02-01")["median_hours"]
    assert 1.4 <= late / early <= 1.9


def test_4_region_2_declines_about_1_5_pts_per_week():
    t = k.readiness_trend()
    assert -1.8 <= t["R2"]["slope_pts_per_week"] <= -1.3
    assert t["R1"]["slope_pts_per_week"] > -0.5


def test_5_site_a_is_healthy_control():
    sites = {r["site"]: r for r in k.fleet_readiness()["sites"]}
    assert sites["A"]["gap_pts"] > 0
    assert min(sites.values(), key=lambda r: r["readiness_pct"])["site"] == "C"


def test_fleet_is_below_target_and_tools_match_truth_file():
    f = k.fleet_readiness()["fleet"]
    assert f["gap_pts"] < 0
    assert abs(k.readiness_trend()["R2"]["slope_pts_per_week"] - TRUTH["region_readiness_slope_points_per_week"]["R2"]) < 0.05


def test_bad_site_gives_helpful_error():
    try:
        k.fleet_readiness("Z")
    except ValueError as e:
        assert "Valid sites" in str(e)
    else:
        raise AssertionError("expected ValueError")
