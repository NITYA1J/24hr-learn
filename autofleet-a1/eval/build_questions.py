"""Block 4: build eval/questions.jsonl (30 questions) from the tool library, so expected values
always match the data. Fields: id, question, type, expected_tool, tool_args, also_tools,
expected_values {name: number}, expected_text [substrings], tolerance (relative; abs floor 0.05)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import kpis as k

Q = []
EARLY = {"site": "B", "category": "brakes", "start": "2026-01-05", "end": "2026-02-01"}
def add(type_, question, tool, args, values=None, text=None, also=None, tol=0.02, extra=None):
    Q.append(dict(id=f"q{len(Q)+1:02d}", question=question, type=type_, expected_tool=tool, tool_args=args or {},
                  also_tools=also or [], expected_values=values or {}, expected_text=text or [], tolerance=tol, extra_calls=extra or []))

fr = {r["site"]: r for r in k.fleet_readiness()["sites"]}
fleet = k.fleet_readiness()["fleet"]
tb = k.top_bottlenecks()["top"]
ba = {s: k.backlog_aging(s) for s in "ABCDE"}
tp = {(r["site"], r["shift"]): r for r in k.technician_productivity()["rows"]}
brk_late = k.service_cycle_time("B", "brakes", "2026-02-02", "2026-02-15")
brk_early = k.service_cycle_time("B", "brakes", "2026-01-05", "2026-02-01")
tr = k.readiness_trend()
dbc = k.downtime_by_category()["categories"]

# ---- 10 lookups
add("lookup", "What is the average fleet readiness at Site C?", "fleet_readiness", {"site": "C"}, {"readiness_pct": fr["C"]["readiness_pct"]})
add("lookup", "What is the average fleet readiness at Site A?", "fleet_readiness", {"site": "A"}, {"readiness_pct": fr["A"]["readiness_pct"]})
add("lookup", "What is overall fleet readiness across all sites?", "fleet_readiness", {}, {"readiness_pct": fleet["readiness_pct"]})
add("lookup", "How far is Site D from its readiness target, in percentage points?", "fleet_readiness", {"site": "D"}, {"gap_pts": fr["D"]["gap_pts"]})
add("lookup", "What is the median cycle time in hours for brake repairs at Site B?", "service_cycle_time", {"site": "B", "category": "brakes"},
    {"median_hours": k.service_cycle_time("B", "brakes")["median_hours"]})
add("lookup", "What is the p90 cycle time in hours for sensor calibration work orders fleet-wide?", "service_cycle_time", {"category": "sensor_calibration"},
    {"p90_hours": k.service_cycle_time(category="sensor_calibration")["p90_hours"]})
add("lookup", "How many work orders are open at Site C at the end of the data?", "backlog_aging", {"site": "C"}, {"open_work_orders": ba["C"]["open_work_orders"]})
add("lookup", "How many night-shift technicians does Site C have?", "technician_productivity", {"site": "C"}, {"technicians": tp[("C", "night")]["technicians"]})
add("lookup", "How many work orders per technician-shift does the Site C night shift close?", "technician_productivity", {"site": "C"}, {"wos_per_tech_shift": tp[("C", "night")]["wos_per_tech_shift"]})
add("lookup", "How many total downtime hours were caused by sensor calibration?", "downtime_by_category", {}, {"hours": dbc[0]["hours"]}, ["sensor_calibration"])

# ---- 8 rankings / comparisons
add("ranking", "What are the top 3 causes of lost readiness, and how many readiness points does each cost?", "top_bottlenecks", {"n": 3},
    {f"rank{t['rank']}_points": t["readiness_points_lost"] for t in tb}, [tb[0]["category"], tb[1]["category"], tb[2]["category"]])
add("ranking", "Which site has the lowest readiness, and what is it?", "fleet_readiness", {}, {"readiness_pct": fr["C"]["readiness_pct"]}, ["C"])
add("ranking", "Which site is furthest below its readiness target?", "fleet_readiness", {}, {"gap_pts": fr["C"]["gap_pts"]}, ["C"])
add("ranking", "Compare mean backlog age (daily average) at Site C versus Site A.", "backlog_aging", {"site": "C"},
    {"C_mean_age_days": ba["C"]["mean_age_days_avg_daily"], "A_mean_age_days": ba["A"]["mean_age_days_avg_daily"]},
    extra=[{"name": "backlog_aging", "args": {"site": "A"}}])
add("ranking", "Which shift and site has the highest work orders per technician-shift?", "technician_productivity", {}, {"wos_per_tech_shift": tp[("C", "night")]["wos_per_tech_shift"]}, ["C", "night"])
add("ranking", "Did brake repair median cycle time at Site B get longer in weeks 5-6 (2026-02-02 to 2026-02-15) compared with weeks 1-4?", "service_cycle_time",
    {"site": "B", "category": "brakes", "start": "2026-02-02", "end": "2026-02-15"}, {"weeks5_6_median_h": brk_late["median_hours"], "weeks1_4_median_h": brk_early["median_hours"]},
    extra=[{"name": "service_cycle_time", "args": EARLY}])
add("ranking", "What are the top 2 failure categories by share of downtime?", "downtime_by_category", {}, {"top1_share_pct": dbc[0]["share_pct"], "top2_share_pct": dbc[1]["share_pct"]}, [dbc[0]["category"], dbc[1]["category"]])
add("ranking", "Which site has the highest average number of vehicles down per day?", "fleet_readiness", {}, {"avg_vehicles_down": fr["C"]["avg_vehicles_down"]}, ["C"])

# ---- 6 root cause
add("root_cause", "What is preventing our robotaxi fleet from achieving target operational readiness, and what actions would improve it?", "top_bottlenecks", {"n": 3},
    {"fleet_gap_pts": fleet["gap_pts"], "sensor_points": tb[0]["readiness_points_lost"], "sensor_share_pct": tb[0]["share_of_downtime_pct"]},
    ["sensor_calibration"], also=["fleet_readiness", "search_playbooks"])
add("root_cause", "Why is Site C below its readiness target?", "technician_productivity", {"site": "C"},
    {"night_technicians": tp[("C", "night")]["technicians"], "night_wos_per_tech_shift": tp[("C", "night")]["wos_per_tech_shift"]}, ["night"], also=["backlog_aging"])
add("root_cause", "Why did Site B brake repairs slow down in weeks 5-6?", "service_cycle_time", {"site": "B", "category": "brakes", "start": "2026-02-02", "end": "2026-02-15"},
    {"weeks5_6_median_h": brk_late["median_hours"], "weeks1_4_median_h": brk_early["median_hours"]}, ["parts"], also=["search_playbooks"], extra=[{"name": "service_cycle_time", "args": EARLY}])
add("root_cause", "Why is Region 2 readiness falling?", "readiness_trend", {"region": "R2"}, {"slope_pts_per_week": tr["R2"]["slope_pts_per_week"]}, ["R2"])
add("root_cause", "Is Site A healthy, and by how much does it beat its readiness target?", "fleet_readiness", {"site": "A"}, {"readiness_pct": fr["A"]["readiness_pct"], "gap_pts": fr["A"]["gap_pts"]})
add("root_cause", "What single fix would recover the most readiness points?", "top_bottlenecks", {"n": 1}, {"sensor_points": tb[0]["readiness_points_lost"]}, ["sensor_calibration"], also=["search_playbooks"])

# ---- 3 trend
add("trend", "How fast is Region 2 readiness changing per week?", "readiness_trend", {"region": "R2"}, {"slope_pts_per_week": tr["R2"]["slope_pts_per_week"]})
add("trend", "Is Region 1 readiness improving or declining? Give the weekly slope.", "readiness_trend", {"region": "R1"}, {"slope_pts_per_week": tr["R1"]["slope_pts_per_week"]})
add("trend", "What is the fleet-wide weekly readiness slope?", "readiness_trend", {}, {"slope_pts_per_week": tr["fleet"]["slope_pts_per_week"]})

# ---- 3 out of scope
for q in ["What's our revenue in Dallas?", "Which competitor has the best robotaxi fleet?", "Predict next quarter's ridership by city."]:
    add("out_of_scope", q, None, {})

assert len(Q) == 30, len(Q)
out = Path(__file__).parent / "questions.jsonl"
out.write_text("\n".join(json.dumps(q) for q in Q) + "\n")
print(f"wrote {len(Q)} questions -> {out}")
