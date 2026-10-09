# Field Service Project Playbook

Oct 8, 2026 · @NJ

This playbook turns the practice dataset into a weekend project: nine problem statements tied to the job posting, with step-by-step cleaning, analysis, potential solutions and an interview talk track.

## What you have and a 20-hour weekend plan

You have one messy workbook, four CSV exports of the same rows, reference tables, starter code and a sealed answer key; work in the order below and open the key only at the end.

| File | What it is | Use it for |
| --- | --- | --- |
| FieldService\_Project\_Dataset.xlsx | WO\_Raw (17,797 messy rows, header on row 4) plus Roster, Lkp\_ServiceType, Lkp\_Rates, Lkp\_Center, Lkp\_Geo, tblFleet, Parameters, Data\_Dictionary | Excel cleaning, XLOOKUP, PivotTables |
| PowerQuery\_Sources.zip | The same rows split into 4 quarterly CSVs, each with 3 junk lines on top | Power Query folder combine |
| FieldService\_Macros.bas | Four VBA macros | Macro practice |
| charts\_starter.py | Nine matplotlib charts, one per problem statement | Python visuals |
| Answer\_Key\_and\_Reference.zip | Answer key, a reference cleaned CSV, a reference Python cleaner | Checking your work last |

The data mixes real and simulated parts. Real: Tesla and WA vehicle records, support-ticket fields, robotaxi telemetry values (from the AI4I file). Simulated: the 8 centers, technicians, scheduling, hours, revenue and CSAT. Never present it as Tesla data.

| Block | Hours | Output |
| --- | --- | --- |
| Clean in Excel (Step 1) | 4 | Table tblClean, 17,107 rows, checks passing |
| Power Query rebuild (Step 2) | 2 | One refreshable query that does the same cleaning |
| KPI model (Step 3) | 2 | Helper columns and a center-month capacity table |
| Analysis (Step 4) | 6 | PivotTables and one chart per problem statement you pick |
| Macros (Step 5) | 1 | Two macros running on your copy |
| Dashboard (Step 6) | 3 | One page in Excel or Power BI |
| Memo and rehearsal (talk track) | 2 | One page and a 2-minute walkthrough |

Pick 4 or 5 problem statements, not all nine. Depth beats coverage in an interview. Needs Excel 365 or 2021+ for XLOOKUP and Power Query.

## Nine problem statements

Each statement is a question a field-service leader would ask; the data may or may not confirm it, so test the hypothesis before recommending anything.

| # | Problem statement | Posting bullet it answers | Fields and KPIs | Main tools |
| --- | --- | --- | --- | --- |
| PS1 | Which centers lack technician capacity for their demand, and when did the gap open? | Scheduling and appointment availability, open capacity | Wait days (DUNAA proxy), demand hours vs capacity hours, active techs | XLOOKUP, tech-day formula, PivotTable, heatmap |
| PS2 | Is booked demand spread evenly across the week, and how much capacity sits idle on slow days? | Shop loading, production planning | Appointments per weekday vs appointment slots | PivotTable, NETWORKDAYS.INTL |
| PS3 | How large is the open backlog, how old is it, and how much of it is real work rather than stale records? | Backlog, aging work, work in progress, recovery plans | Open status, age buckets, awaiting-parts share | Helper columns, PivotTable, macro |
| PS4 | What drives low CSAT, and where does follow-through on customer contacts fail? | Customer satisfaction and follow-through with the field | CSAT by wait, repeat, parts delay, callback hours, ticket rate | Pivot, AVERAGEIFS, bar charts |
| PS5 | Where is labor productivity lowest, and what does it cost in capacity and revenue? | Productivity and revenue initiatives, cars per technician | Book hrs / actual hrs, revenue per labor hour, tech level | XLOOKUP to roster, Pivot |
| PS6 | Did the Tri-Cities launch go cleanly, and where should the next market open? | New market deployment, facility readiness, inventory positioning | Demand before and after opening, parts-delay share, uncovered Tesla registrations | Power Query merge, Lkp\_Geo, map or bar chart |
| PS7 | Is the robotaxi fleet ready, and can telemetry predict failures early enough to plan technician time? | Robotaxi fleet readiness, technician efficiency, cycle time | Readiness %, cycle time, failure rate by torque and wear | Pivot, threshold test |
| PS8 | Which vehicles and service types come back, and what do repeat visits cost? | Process improvement, CSAT, bottlenecks | Repeat flag rebuilt with COUNTIFS, repeat rate by model, year, service | COUNTIFS, Pivot |
| PS9 | Can mobile service relieve overloaded shops? | Mobile service response | Mobile share, response hours, mobile-eligible shop jobs, mobile-certified techs | Pivot, sizing table |

Suggested picks if you have time for five: PS1, PS3, PS4, PS6, PS7. They cover scheduling, backlog, CSAT, new markets and robotaxi, which is most of the posting.

## Step 1: Clean the data in Excel (about 4 hours)

Work on a copy, fix structure first, then each column family, and finish with row-count checks that prove you did not lose or invent rows.

1. **Protect the original.** Right-click the WO\_Raw tab, choose Move or Copy, tick Create a copy, and name it Work. Never edit WO\_Raw.
2. **Fix the structure.** Delete rows 1 to 3 so the header is row 1. Delete the two footer lines at the bottom ("Total records" and "-- end of export --").
3. **Rename headers with the dictionary.** Insert a helper row above the header and put `=XLOOKUP(A2,tblDictionary[Raw_Header],tblDictionary[Clean_Name])` in A1, fill right, paste values over the real header, delete the helper row. Press Ctrl+T and name the table tblClean.
4. **Remove blank rows.** Filter WO\_ID for (Blanks), select the visible rows, delete them.
5. **Normalise IDs, then remove duplicates.** Put `=UPPER(TRIM([@WO_ID]))` in a helper column, paste values over WO\_ID, then Data > Remove Duplicates on WO\_ID only. Near-duplicates differ in other columns, so a whole-row match misses them. Keep the first occurrence.
6. **Standardise the category columns** (Service\_Center, Service\_Type, Status, Channel, Pay\_Type) with alias tables: copy the column to a new sheet, Remove Duplicates to get the distinct raw values (XLOOKUP ignores case, so you need fewer), type the standard value beside each, make it a table, then look up.
7. **Fix dates, numbers, CSAT and the vehicle block** with the formulas below. Always write the formula in a new column, check it, paste values over the original, delete the helper.
8. **Rebuild the repeat-visit flag** from vehicle history instead of trusting the half-blank raw column.
9. **Add the scope flag and run the checks** at the end of this section.

Standard target values are on the sheets: Lkp\_Center (Center\_Code), Lkp\_ServiceType (Service\_Type), Parameters, and Data\_Dictionary (Target\_Type column).

### Formulas by column

| Column | What is wrong | Formula in a new column |
| --- | --- | --- |
| Created\_Date, Appt\_Date, Completed\_Date | Real dates mixed with text in four formats; "TBD", "N/A", impossible dates | `=IF([@Created_Date]="","",IF(ISNUMBER([@Created_Date]),[@Created_Date],IFERROR(DATEVALUE(TRIM([@Created_Date])),"")))`. Needs a US date setting. A blank result where the raw cell was not blank is an invalid date: review it. |
| Completed before created | Date typos | `=IF(AND(ISNUMBER([@Completed_Date]),ISNUMBER([@Created_Date]),[@Completed_Date]<[@Created_Date]),"CHECK","")` then clear the completed date after review |
| Labor\_Hours\_Actual | "2.5 hrs", "2,5", negatives, values 10x too large | `=IFERROR(ABS(VALUE(SUBSTITUTE(SUBSTITUTE(LOWER(TRIM([@Labor_Hours_Actual]))," hrs",""),",","."))),"")`, then `=IF(x>30,x/10,x)` in a second helper |
| Parts\_Cost\_USD, Invoice\_Total\_USD | "$1,234.50" as text, "N/C" | `=IF(UPPER(TRIM([@Invoice_Total_USD]))="N/C",0,IFERROR(VALUE(SUBSTITUTE(SUBSTITUTE(TRIM([@Invoice_Total_USD]),"$",""),",","")),""))` |
| Cycle\_Time\_Hrs | "5h" | `=IFERROR(VALUE(SUBSTITUTE(LOWER(TRIM([@Cycle_Time_Hrs])),"h","")),"")` |
| Parts\_Wait\_Days | Blank where it should be 0 | `=IF([@Parts_Wait_Days]="",0,[@Parts_Wait_Days])` |
| Service\_Center, Service\_Type, Status, Channel, Pay\_Type | 4 to 8 spellings each | `=XLOOKUP(TRIM([@Service_Center]),tblAliasCenter[Raw],tblAliasCenter[Standard],"CHECK")`; filter the result for CHECK to find spellings you missed |
| Tech\_ID | T1012, T-1012, t1012, 1012, spaces | `=IF(TRIM([@Tech_ID])="","","T"&RIGHT(TRIM([@Tech_ID]),4))` |
| Fleet\_Vehicle\_ID, Fleet\_Type | rt-007, RT007; blank Fleet\_Type | `=IF(TRIM([@Fleet_Vehicle_ID])="","","RT-"&RIGHT(TRIM([@Fleet_Vehicle_ID]),3))`, then `=IF([@Fleet_Vehicle_ID]<>"","Robotaxi","Customer")` |
| CSAT\_Score | Text labels, fractions, words, 0, 6, 10, "N/A" | Helper 1: `=IF(ISNUMBER([@CSAT_Score]),[@CSAT_Score],IFERROR(XLOOKUP(LOWER(TRIM([@CSAT_Score])),{"one","two","three","four","five"},{1,2,3,4,5}),IFERROR(VALUE(LEFT(TRIM([@CSAT_Score]),1)),"")))`. Helper 2: `=IF(AND(ISNUMBER([@H1]),[@H1]>=1,[@H1]<=5),[@H1],"")` |
| Make, Model | TESLA, Tesla Inc., model3 | `=IF(ISNUMBER(SEARCH("tesla",[@Make])),"Tesla",PROPER(TRIM([@Make])))` and `=XLOOKUP(SUBSTITUTE(LOWER(TRIM([@Model]))," ",""),{"model3","modely","models","modelx","roadster"},{"Model 3","Model Y","Model S","Model X","Roadster"},TRIM([@Model]))` |
| State | Wa, Washington, Wash. | `=IF(LEFT(UPPER(TRIM([@State])),2)="WA","WA",UPPER(TRIM([@State])))` |
| County, City | Case, spaces, blank County | `=IF(TRIM([@County])="",XLOOKUP(TRIM([@City]),tblGeo[City],tblGeo[County],""),PROPER(TRIM([@County])))`, and `=PROPER(TRIM([@City]))` |
| Model\_Year | Blank, letter O in "2O22" | `=IF([@Model_Year]="",MAXIFS([Model_Year],[DOL_Vehicle_ID],[@DOL_Vehicle_ID]),VALUE(SUBSTITUTE([@Model_Year],"O","0")))`. Convert DOL\_Vehicle\_ID with `=VALUE([@DOL_Vehicle_ID])` first. A result of 0 means unknown. |
| Postal\_Code | ZIP+4, numbers and text mixed | `=IF([@Postal_Code]="","",LEFT(SUBSTITUTE(TRIM([@Postal_Code]),"-",""),5))` |
| Vehicle\_Location | "POINT (lon lat)" text | Longitude: `=VALUE(MID([@Vehicle_Location],FIND("(",[@Vehicle_Location])+1,FIND(" ",[@Vehicle_Location],FIND("(",[@Vehicle_Location]))-FIND("(",[@Vehicle_Location])-1))`. Latitude: `=VALUE(MID([@Vehicle_Location],FIND(" ",[@Vehicle_Location],FIND("(",[@Vehicle_Location]))+1,FIND(")",[@Vehicle_Location])-FIND(" ",[@Vehicle_Location],FIND("(",[@Vehicle_Location]))-1))`. Or use Data > Text to Columns. |
| Failure\_Flag, Ambient\_Temp\_K, Motor\_Torque\_Nm | Y/N, Celsius values, " Nm" suffix | `=IF([@Failure_Flag]="","",IF(OR([@Failure_Flag]="Y",[@Failure_Flag]=1),1,0))`; `=IF([@Ambient_Temp_K]="","",IF([@Ambient_Temp_K]<100,[@Ambient_Temp_K]+273.15,[@Ambient_Temp_K]))`; `=IF([@Motor_Torque_Nm]="","",VALUE(SUBSTITUTE(LOWER([@Motor_Torque_Nm])," nm","")))` |
| Ticket\_Priority, Ticket\_Subject | Mixed case, double spaces | `=LOWER(TRIM([@Ticket_Priority]))`, `=TRIM([@Ticket_Subject])` (TRIM also collapses double spaces) |
| Repeat\_Visit\_Flag | Half blank, many spellings | `=IF(COUNTIFS([DOL_Vehicle_ID],[@DOL_Vehicle_ID],[Service_Type],[@Service_Type],[Status],"Completed",[Completed_Date],"<="&[@Created_Date],[Completed_Date],">="&[@Created_Date]-30)>0,1,0)`. This is slow on 17K rows: calculate once, paste values. |
| In\_Scope | Non-Tesla and non-WA rows | `=IF(AND([@Make]="Tesla",[@State]="WA"),1,0)` |

### Checks before you move on

- Table has 17,107 rows after de-duplication; In\_Scope = 1 on 16,071 of them.
- A PivotTable of each category column shows only the standard values: 8 centers, 15 service types, 7 statuses, 3 channels, 4 pay types.
- Every date column holds real dates only (`=COUNT([Created_Date])` equals the row count) and no completed date is earlier than its created date.
- CSAT is blank or 1 to 5; labor hours are blank or between 0.2 and 30.
- Keep a Cleaning\_Log sheet: one line per issue, how many rows it touched, and what you decided. Interviewers like this more than the clean file.

## Step 2: Rebuild the cleaning in Power Query (about 2 hours)

Power Query repeats Step 1 as a refreshable pipeline, so next month's export cleans itself; build it once as four small queries and explain each applied step in the interview.

1. **Load the lookups first.** Open the workbook, select each table (tblDictionary, tblServiceType, tblCenter, tblGeo, tblRoster, tblFleet), Data > From Table/Range, then Close & Load To > Only Create Connection. In the Lkp\_Geo query add a column `KeyL` = `Text.Lower([Key])`.
2. **Combine the four CSVs.** Unzip PowerQuery\_Sources.zip to a folder, Data > Get Data > From File > From Folder, then Transform Data. Paste the query below into the Advanced Editor and change the folder path.
3. **Rename headers** with the dictionary, then trim, type and standardise columns (queries below).
4. **De-duplicate** on WO\_ID after upper-casing and trimming it.
5. **Merge** the lookups: Home\_Center from the geo key, Book\_Hours from service type, technician Level from the roster.
6. **Turn on full profiling.** In the status bar choose Column profiling based on entire data set, then check null counts and distinct values per column.
7. **Load.** Name the final query `clean_wo`, Close & Load To > Table and Add this data to the Data Model. Keep the staging queries connection-only.

If you prefer the workbook route instead of CSVs: Get Data > From Table/Range on the WO\_Raw sheet, Remove Top Rows = 3, Use First Row as Headers, then filter WO ID to rows that begin with WO-.

Query 1, combine the files:

```m
let
    Source   = Folder.Files("C:\FS\power_query_sources"),
    CsvOnly  = Table.SelectRows(Source, each Text.EndsWith([Name], ".csv")),
    Parsed   = Table.AddColumn(CsvOnly, "Data", each
        let
            Raw      = Csv.Document([Content], [Delimiter = ",", Columns = 53, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
            FromHdr  = Table.Skip(Raw, each [Column1] <> "WO ID"),
            Promoted = Table.PromoteHeaders(FromHdr, [PromoteAllScalars = true])
        in
            Promoted),
    Combined = Table.Combine(Parsed[Data]),
    NoBlank  = Table.SelectRows(Combined, each [WO ID] <> null and Text.Trim([WO ID]) <> ""),
    Renamed  = Table.RenameColumns(NoBlank, List.Zip({tblDictionary[Raw_Header], tblDictionary[Clean_Name]}))
in
    Renamed
```

Query 2, text, dates, numbers. Name Query 1 `raw_wo` and this query `clean_step2`:

```m
let
    Source = raw_wo,
    Ids    = Table.TransformColumns(Source, {{"WO_ID", each Text.Upper(Text.Trim(_)), type text}}),
    Dedup  = Table.Distinct(Ids, {"WO_ID"}),
    Dates  = Table.TransformColumns(Dedup, List.Transform({"Created_Date", "Appt_Date", "Completed_Date"},
               (c) => {c, each try Date.FromText(Text.Trim(_), [Culture = "en-US"]) otherwise null, type nullable date})),
    fnMoney = (t) => if t = null then null
                      else if Text.Upper(Text.Trim(Text.From(t))) = "N/C" then 0
                      else try Number.FromText(Text.Remove(Text.From(t), {"$", ","}), "en-US") otherwise null,
    fnHours = (t) => if t = null then null
                      else try Number.Abs(Number.FromText(Text.Replace(Text.Remove(Text.Lower(Text.From(t)), {"h", "r", "s", " "}), ",", "."), "en-US")) otherwise null,
    Nums   = Table.TransformColumns(Dates, {{"Parts_Cost_USD", fnMoney, type nullable number}, {"Invoice_Total_USD", fnMoney, type nullable number},
               {"Labor_Hours_Actual", fnHours, type nullable number}, {"Cycle_Time_Hrs", fnHours, type nullable number}}),
    Fixed  = Table.TransformColumns(Nums, {{"Labor_Hours_Actual", each if _ <> null and _ > 30 then _ / 10 else _, type nullable number}})
in
    Fixed
```

Query 3, standardise categories and merge lookups. Build alias tables (Raw, Standard) in Excel for center, service type, status, channel and pay type, load each as a query, and merge on the trimmed, lower-cased raw value:

```m
let
    Source  = clean_step2,
    WithKey = Table.AddColumn(Source, "Geo_Key", each Text.Lower(Text.Trim(Text.From([County])) & "|" & Text.Trim(Text.From([City]))), type text),
    Merged  = Table.NestedJoin(WithKey, {"Geo_Key"}, Lkp_Geo, {"KeyL"}, "Geo", JoinKind.LeftOuter),
    Result  = Table.ExpandTableColumn(Merged, "Geo", {"Home_Center", "Dist_To_Nearest_Center_Mi"})
in
    Result
```

Power Query matches text case-sensitively, which is why both keys are lower-cased. A null Home\_Center after the merge means no center within 35 miles (or a city missing from the lookup: test both).

## Step 3: Build the KPI model with XLOOKUP and helper columns (about 2 hours)

Add the helper columns once to tblClean, add a center-by-month capacity table on its own sheet, and every later PivotTable becomes a drag-and-drop job.

### Helper columns in tblClean

| Column | Formula | Why |
| --- | --- | --- |
| Month | `=TEXT([@Created_Date],"yyyy-mm")` | Pivot rows and chart axis |
| Wait\_Days | `=IF(AND(ISNUMBER([@Appt_Date]),ISNUMBER([@Created_Date])),[@Appt_Date]-[@Created_Date],"")` | DUNAA proxy: average it for Channel = Shop |
| Wait\_Bucket | `=IF([@Wait_Days]="","",LOOKUP([@Wait_Days],{0,3,6,11,21},{"0-2","3-5","6-10","11-20","20+"}))` | CSAT by wait |
| Book\_Hours | `=XLOOKUP([@Service_Type],tblServiceType[Service_Type],tblServiceType[Book_Hours],"")` | Flat-rate hours: demand and efficiency |
| Mobile\_Eligible | `=XLOOKUP([@Service_Type],tblServiceType[Service_Type],tblServiceType[Mobile_Eligible],"")` | Mobile sizing |
| Tech\_Level | `=XLOOKUP([@Tech_ID],tblRoster[Tech_ID],tblRoster[Level],"Unknown")` | Productivity by seniority |
| Home\_Center | `=LET(r,XLOOKUP([@County]&"\|"&[@City],tblGeo[Key],tblGeo[Home_Center]&"","Not in lookup"),IF(r="","No center within 35 mi",r))` | Coverage and new-market work. Write the key with a plain pipe character between County and City |
| Book\_Hrs\_Done, Actual\_Hrs\_Done | `=IF(AND([@Status]="Completed",ISNUMBER([@Labor_Hours_Actual])),[@Book_Hours],0)` and the same with `[@Labor_Hours_Actual]` | Efficiency = sum of book / sum of actual, on rows where both exist |
| Is\_Open | `=IF(OR([@Status]="Scheduled",[@Status]="In Progress",[@Status]="Awaiting Parts",[@Status]="Awaiting Customer"),1,0)` | Backlog |
| Age\_Days | `=IF([@Is_Open]=1,Report_Date-[@Created_Date],"")` | Aging. Report\_Date is a named cell on Parameters |
| Age\_Bucket | `=IF([@Age_Days]="","",LOOKUP([@Age_Days],{0,8,15,31,91},{"0-7","8-14","15-30","31-90","90+"}))` | Aging pivot columns |
| Appt\_Weekday | `=TEXT([@Appt_Date],"ddd")` | Shop loading |
| Parts\_Delay | `=IF([@Parts_Wait_Days]>=3,1,0)` | CSAT driver, inventory signal |

### Capacity and utilisation by center and month

On a new sheet put the 8 center codes down column A (A2:A9) and the first day of each month across B1:M1 (2025-10-01 to 2026-09-01). Technician capacity must come from hire and termination dates, because headcount changed during the year.

| Cell block | Formula | Meaning |
| --- | --- | --- |
| Tech-days (B2:M9) | `=LET(som,B$1,eom,EOMONTH(som,0),h,tblRoster[Hire_Date],t,tblRoster[Term_Date],s,IF(h>som,h,som),e,IF(t="",eom,IF(t>eom,eom,t)),d,IF(e-s+1<0,0,e-s+1),SUM(IF(tblRoster[Center]=$A2,d,0)))` | Calendar days each technician was employed in the month, summed per center |
| Capacity hours (second block) | `=B2/7*Wrench_Hrs_Per_Tech_Week` | Productive hours: tech-days to tech-weeks times 30 |
| Demand hours (third block) | `=SUMIFS(tblClean[Book_Hours],tblClean[Service_Center],$A2,tblClean[Created_Date],">="&B$1,tblClean[Created_Date],"<="&EOMONTH(B$1,0),tblClean[In_Scope],1)` | Flat-rate hours requested, customers and robotaxi together |
| Utilisation (fourth block) | `=IFERROR(demand/capacity,"")` with a red-yellow-green color scale | Above about 0.9 means the center cannot absorb demand without waiting or overtime |

### Shop loading by weekday

Build a PivotTable of Count of WO\_ID with Service\_Center in rows and Appt\_Weekday in columns, filtered to Channel = Shop. Divide each weekday column by how many of that weekday exist in the window, using `=NETWORKDAYS.INTL(DATE(2025,10,1),DATE(2026,9,30),"0111111")` for Mondays (move the single 0 for other days). Then divide by `=XLOOKUP(center,tblCenter[Center_Code],tblCenter[Appt_Slots_Per_Day])`.

Other KPIs worth defining once: cars per technician per day = completed work orders / tech-days; revenue per labor hour = sum of Invoice\_Total\_USD / sum of Labor\_Hours\_Actual; no-show rate = No Show / (Completed + No Show) for shop appointments; fleet readiness = 1 - robotaxi downtime hours / (fleet vehicles x hours in the month).

## Step 4: Analysis and potential solutions, one problem statement at a time (about 6 hours)

For each statement you pick: build the pivot, find the pattern, size two or three solutions with a formula, and finish with one recommendation and its trade-off. Filter to In\_Scope = 1 everywhere, and use Fleet\_Type = Customer unless the statement is about robotaxi.

### PS1: Capacity versus demand

- **Build.** PivotTable with Month in rows, Service\_Center in columns, Average of Wait\_Days, filtered to Channel = Shop. Chart it as a line chart with a 5-day target line. Put the utilisation table from Step 3 beside it as a heatmap.
- **Look for.** Centers where the line is flat and then bends; whether the bend lines up with utilisation passing about 0.9 and with a Hire\_Date or Term\_Date on the roster; whether demand grew or capacity shrank (chart demand hours and capacity hours separately).
- **Solutions to test.**
  1. Backfill or hire: technicians needed = weekly demand hours / (30 x 0.85); gap = needed minus active.
  2. Rebalance appointments to nearby centers with slack: slack hours = 0.85 x capacity minus demand. Distance between centers = `=3958.8*ACOS(SIN(RADIANS(lat1))*SIN(RADIANS(lat2))+COS(RADIANS(lat1))*COS(RADIANS(lat2))*COS(RADIANS(lon2-lon1)))` using Lkp\_Center coordinates; only route customers whose city is within about 25 miles of the slack center.
  3. Bridge with overtime: weekly gap hours / active technicians. Flag anything above 8 extra hours per technician per week as unsustainable.
  4. Throttle booking: release slots weekly so booked hours stay under 90% of capacity.
- **Size it.** Recovery table with one row per lever: hours freed per week, weeks to clear the backlog = open book hours / hours freed, cost or risk.

### PS2: Shop loading across the week

- **Build.** The weekday loading pivot from Step 3 as a heatmap (center by weekday, value = booked appointments / slots).
- **Look for.** The ratio between the busiest and quietest day, whether every center shows the same shape, and open capacity hours on slow days = (slots minus average booked) x average book hours per job.
- **Solutions to test.** Stagger shifts (for example four 10-hour days with different off-days) so capacity follows demand; release slots by weekday so bookings are pushed toward slow days; offer reminders or small incentives for midweek slots; reserve slow-day capacity for mobile dispatch and robotaxi scheduled work. Size: extra jobs per week if slow days were filled to 85% loading.

### PS3: Backlog, aging and stale records

- **Build.** With Is\_Open = 1: Service\_Center in rows, Age\_Bucket in columns, Count of WO\_ID; a second pivot of Status by Age\_Bucket; a third with Sum of Book\_Hours (open work in hours).
- **Look for.** Which statuses make up the oldest buckets, whether any open record is older than a realistic repair could be (compare with the 90-day Stale\_WO\_Days parameter), and which centers hold future-dated appointments versus parts holds.
- **Solutions to test.** A weekly aged-work review with a named owner per center; a stale-record sweep (use the FlagStaleBacklog macro) to close or re-date records that are not real work; expedite or stock parts that cause long holds; targets by bucket. Size: weeks to recover = open book hours / (weekly capacity minus weekly demand), and the share of the backlog that disappears if stale records are closed.

### PS4: CSAT drivers and follow-through

- **Build.** Average CSAT by Wait\_Bucket (shop only), by Repeat\_Visit\_Flag, by Parts\_Delay, by Channel and by center. Response rate = count of CSAT / count of completed orders. For tickets: ticket rate by center and average CSAT with and without a ticket; split tickets by Ticket\_Callback\_Hrs above or below 48.
- **Look for.** The size of each CSAT gap and how many orders it touches (a big gap on few orders matters less than a small gap on many). Remember only a minority of customers respond, so say so when you present.
- **Solutions to test.** Proactive outreach when a customer's wait passes a threshold; a second-look quality check before release on jobs with a high repeat rate; parts-delay messaging; a 24-hour callback standard. Size: expected CSAT gain = sum over drivers of (share of orders affected x CSAT gap x share you can fix).

### PS5: Labor productivity and revenue

- **Build.** Efficiency = Sum of Book\_Hrs\_Done / Sum of Actual\_Hrs\_Done, by center and by Tech\_Level, plus a per-technician list sorted ascending (join the roster for Hire\_Date). Revenue per labor hour by center. Cars per technician per day from the capacity sheet.
- **Look for.** Whether the spread is between centers or inside them, how seniority mix and new-hire ramp (first 90 days after Hire\_Date) explain it, and whether a few individuals drive most of the shortfall.
- **Solutions to test.** Pair low-efficiency technicians with senior mentors; route complex job types to senior technicians; a structured 90-day ramp plan; weekly book-versus-actual review by job type. Size: hours recovered = actual hours minus book hours / 0.90 target; extra jobs = hours recovered / average book hours per job; revenue = extra jobs x revenue per job.

### PS6: New market launch and coverage gaps

- **Build.** Merge Home\_Center from Lkp\_Geo, then chart monthly work orders for customers whose Home\_Center is the new center, with the Open\_Date from tblCenter marked, and show which center served them before and after. Add monthly parts-delay share, CSAT and utilisation for the new center. Second view: Lkp\_Geo filtered to blank Home\_Center, sorted by Tesla\_Registered\_WA, with distance.
- **Look for.** Demand unlocked by the opening, a launch-period penalty in the first eight weeks, and staffing against demand. Do not compare work orders per registered vehicle across centers: the rows were sampled by service area, so counts do not show true volume.
- **Solutions to test.** A launch checklist: pre-position the top parts by service-type volume for the first eight weeks; hire and train before the open date; add technicians only when utilisation stays above 0.8 for four weeks; temporary mobile cover. For the next market, score cities by Tesla\_Registered\_WA x MIN(1, distance / 60) and recommend a mobile-first pilot where registrations are too thin for a fixed site.

### PS7: Robotaxi readiness and predictive visits

- **Build.** Robotaxi rows only. Monthly readiness by depot = 1 minus summed Cycle\_Time\_Hrs / (fleet vehicles from tblFleet x hours in the month). Cycle time for failure versus scheduled visits. Failure rate by torque band (0 to 30, 30 to 45, 45 to 60, over 60 Nm) and by wear band (under 100, 100 to 150, 150 to 200, over 200 min). Failure mode against service type.
- **Look for.** Where the failure rate jumps; whether a simple threshold would have caught most failures (recall = failures above the threshold / all failures) without flagging too many healthy visits (precision = failures above the threshold / all visits above it); the trend in readiness against the 95% target; the robotaxi share of each depot's booked hours.
- **Solutions to test.** A rule that books a preventive visit when torque or wear passes the threshold you chose; night-window scheduling at the depot; reserved technician hours; spares for the top failure modes. Size: failures avoided x (failure cycle hours minus scheduled cycle hours) / fleet hours = readiness points gained.

### PS8: Repeat visits

- **Build.** Repeat rate by service type, then by Model x Model\_Year for the worst service types. Book hours spent on repeat visits, and CSAT on repeat versus first visits.
- **Look for.** A small set of model-year and service combinations with several times the average rate, and whether repeats cluster by center or technician level.
- **Solutions to test.** Send hotspot combinations to engineering with the evidence; a parts kit or procedure fix; a second-look check before release on those combinations; track repeat rate as a weekly KPI. Size: repeat hours x expected reduction = capacity returned.

### PS9: Mobile service

- **Build.** Mobile share by center, median Mobile\_Response\_Hrs by center (use `=MEDIAN(IF(...))` or load the data to the Data Model), shop book hours that are mobile-eligible by center, and mobile-certified technicians per center from the roster.
- **Look for.** Centers with slow response and few mobile-certified technicians, and the CSAT gap between fast and slow arrivals.
- **Solutions to test.** Move a share of mobile-eligible shop jobs from overloaded centers to mobile; certify more technicians; set a response target under 24 hours. Size: hours moved per week, mobile technicians needed = hours moved / (30 x 0.8), then feed the freed hours back into the utilisation table to see the effect on waiting time.

## Step 5: Macros (about 1 hour)

FieldService\_Macros.bas holds four small macros; import it, run each on a copy of your workbook, and be ready to explain what each loop does.

1. Save your workbook as .xlsm (File > Save As > Excel Macro-Enabled Workbook).
2. Press Alt+F11, then File > Import File, and choose FieldService\_Macros.bas.
3. Make sure the workbook has the named cells Report\_Date and Stale\_WO\_Days (they are on Parameters) and that your clean table is named tblClean with columns Status, Created\_Date and a blank Stale\_Flag column.
4. Run a macro from Developer > Macros, or assign it to a button (Insert > Shapes, right-click, Assign Macro).

| Macro | What it does | Needs | Try this |
| --- | --- | --- | --- |
| CleanSelectedText | Trims, strips line breaks and non-breaking spaces in the selected text cells | A selection | Select the Ticket\_Subject column and run it |
| RemoveBlankAndFooterRows | Deletes blank rows and the footer lines ("Total records", "--") below the header on the raw sheet, working bottom-up | A sheet named WO\_Raw, header on row 4 | Run on a copy of WO\_Raw and compare the row count |
| FlagStaleBacklog | Marks open work orders older than Stale\_WO\_Days in Stale\_Flag and shades the row | tblClean, the named cells | Count the flags and compare with your aging pivot |
| RefreshAndExportDashboard | Refreshes queries and PivotTables, then exports the Dashboard sheet to a dated PDF | A sheet named Dashboard | Add it to a button on the dashboard |

Good extensions to practise: loop through the 8 centers and write one summary row per center; add an InputBox so the stale threshold can be typed; log every run (time, rows touched) to a sheet called Macro\_Log.

The macros were written but not run in Excel in this environment. Test each on a copy, and read the error message if one fails: the most common causes are a different sheet or table name and dates still stored as text.

## Step 6: Dashboards in Excel, Power BI and Python (about 3 hours)

Build one operating page with seven KPI cards, two or three charts and four slicers, and give every chart a title that states its finding rather than its subject.

### Page layout (same idea in Excel or Power BI)

| Zone | Content |
| --- | --- |
| Slicers | Service center, month, channel, fleet type |
| KPI cards | Average days to appointment, utilisation, open work orders and aged open work orders, average CSAT, efficiency, revenue per labor hour, robotaxi readiness. Show each against its target from Parameters |
| Middle | Days-to-appointment line by center; utilisation matrix with red-yellow-green formatting |
| Bottom | Backlog aging stacked bars; CSAT by wait bucket |
| Extra pages | Robotaxi (readiness, cycle time, failure rate by torque and wear); New market (launch ramp, coverage gaps) |

Chart rules that read well in interviews: one message per chart; grey for the centers that are fine and one strong color for the center you are talking about; a dashed target line; centers always in the same order; no pie charts; sort bars.

### Excel version

Insert PivotCharts from the pivots in Step 4, put them on a sheet named Dashboard, then Insert > Slicer for Service\_Center, Month and Channel and connect each slicer to every pivot (right-click the slicer > Report Connections). KPI cards can be cells with `=GETPIVOTDATA(...)` or simple `AVERAGEIFS` formulas, plus conditional formatting icons against the targets.

### Power BI version

1. Get Data from your cleaned CSV or from the Power Query output; also import the lookup tables.
2. Model: Clean\[Service\_Center\] to Lkp\_Center\[Center\_Code\] (many to one); Clean\[Tech\_ID\] to Roster\[Tech\_ID\]; a Calendar table related to Clean\[Created\_Date\]; tblFleet\[Depot\] to Lkp\_Center\[Center\_Code\].
3. Add a CenterMonth table (the tech-days block from Step 3, unpivoted to Center, MonthStart, TechDays) so capacity can be measured.
4. Add these measures and calculated columns (untested here, so check each against your Excel pivots):

```dax
Calendar = CALENDAR(DATE(2025,10,1), DATE(2026,9,30))

-- calculated columns on Clean
Wait_Days = DATEDIFF(Clean[Created_Date], Clean[Appt_Date], DAY)
Age_Days  = DATEDIFF(Clean[Created_Date], DATE(2026,9,30), DAY)

-- measures
Avg DUNAA = CALCULATE(AVERAGE(Clean[Wait_Days]), Clean[Channel] = "Shop")

Open WOs = CALCULATE(COUNTROWS(Clean),
    Clean[Status] IN {"Scheduled", "In Progress", "Awaiting Parts", "Awaiting Customer"})

Aged Open WOs = CALCULATE([Open WOs], Clean[Age_Days] > 14)

Avg CSAT = AVERAGE(Clean[CSAT_Score])

Efficiency = DIVIDE(SUM(Clean[Book_Hrs_Done]), SUM(Clean[Actual_Hrs_Done]))

Revenue per Labor Hr = DIVIDE(SUM(Clean[Invoice_Total_USD]), SUM(Clean[Actual_Hrs_Done]))

Repeat Rate = DIVIDE(CALCULATE(COUNTROWS(Clean), Clean[Repeat_Visit_Flag] = 1), COUNTROWS(Clean))

Demand Hrs = SUM(Clean[Book_Hours])
Capacity Hrs = SUM(CenterMonth[TechDays]) / 7 * 30
Utilisation = DIVIDE([Demand Hrs], [Capacity Hrs])

Robotaxi Downtime Hrs = CALCULATE(SUM(Clean[Cycle_Time_Hrs]), Clean[Fleet_Type] = "Robotaxi")
Fleet Hours = COUNTROWS(tblFleet) * 24 * DAY(EOMONTH(MAX('Calendar'[Date]), 0))
Fleet Readiness = 1 - DIVIDE([Robotaxi Downtime Hrs], [Fleet Hours])
```

### Python version

Save your own cleaned table as CSV using the Clean\_Name headers from Data\_Dictionary (plus Latitude, Longitude and In\_Scope), then run:

```bash
pip install pandas numpy matplotlib seaborn openpyxl
python charts_starter.py WO_Clean.csv FieldService_Project_Dataset.xlsx charts/
```

| Chart file | Statement |
| --- | --- |
| 01\_dunaa\_trend.png | PS1 |
| 02\_utilisation\_heatmap.png | PS1 |
| 03\_shop\_loading\_weekday.png | PS2 |
| 04\_backlog\_aging.png | PS3 |
| 05\_csat\_drivers.png | PS4 |
| 06\_productivity.png | PS5 |
| 07\_new\_market\_ramp.png, 08\_coverage\_gaps.png | PS6 |
| 09\_robotaxi.png | PS7 |

The script is a starter: change the colors, add the target lines you want, and add charts for PS8 and PS9 yourself. It was tested on the reference-cleaned file, so a column-name mismatch is the usual cause of an error.

## Interview packaging (about 2 hours)

Tell the project as one decision story in two minutes, say plainly that the data is simulated, and keep the workbook open and ready for any formula question.

### Two-minute talk track

1. **Why (15 sec).** "The posting is about scheduling, backlog, CSAT, productivity and new markets, so I built a practice territory to show how I would analyse them."
2. **Honest framing (15 sec).** "Vehicles are real Washington Tesla registrations; operations are simulated, so the numbers are practice numbers, not Tesla's."
3. **The mess (20 sec).** "The export had duplicates, mixed date formats, text numbers and eight spellings of each center. I cleaned it in Excel, then rebuilt the same cleaning in Power Query so it refreshes, and kept a log of every fix."
4. **One insight (40 sec).** Pick your strongest statement. Give the number, the cause, and how you checked it ("waiting time rose from X to Y days while utilisation passed 1.0, and it lined up with a technician leaving").
5. **One recommendation (30 sec).** State the lever, the sized effect and the trade-off ("overtime bridges four weeks but cannot last; backfill fixes it; rebalancing to Bellevue works for customers within 25 miles").
6. **Next step (10 sec).** "With real data I would first validate the capacity assumptions with the service managers."

### One-page memo

Headline sentence; three findings with one number each; two recommendations with sizing and trade-offs; risks and data limits; what you would do next. Attach two charts, no more.

### Questions to rehearse

| Likely question | Strong answer |
| --- | --- |
| Why simulated data? | Real service data is internal. I used real vehicle records and simulated the operations layer so I could practise the full workflow, and I labelled it everywhere. |
| How do you know your cleaning is right? | Row-count checks (before and after de-duplication), category pivots that show only standard values, and a cleaning log. I rebuilt it in Power Query and compared the totals. |
| Walk me through one formula. | Pick the repeat-visit COUNTIFS or the capacity LET formula and explain each argument. Do not show a formula you cannot explain. |
| What would you check first with real data? | Definitions: how DUNAA, capacity hours and a completed order are defined, and whether open orders include future-dated appointments. |
| How did you use AI? | The posting asks for it, so be direct: AI helped generate the practice dataset and draft the playbook; you did the cleaning, analysis and recommendations and verified every number against your own pivots. Only say what is true for you. |
| What are the limits of this analysis? | Simulated relationships, a survey with about 38% response, a sample stratified by service area, and no cost data. |

## What was tested and what was not

The data and the Python parts were run end to end; the Excel formulas, Power Query code, VBA and DAX in this playbook were written carefully but not run in Excel or Power BI, so treat them as drafts to verify.

| Item | Status |
| --- | --- |
| Dataset generation and messy export | Run. 17,797 raw rows, 6 blank rows, 684 duplicate rows |
| Reference cleaning (Python) | Run. Reproduces 17,107 rows and 16,071 in-scope rows; about 99% of cells match the ideal clean values, and the rest were destroyed on purpose (for example blank technician IDs) |
| Workbook and the 4 CSVs | Loaded back and row counts checked (17,797 rows in both) |
| Findings in the answer key | Computed from the reference-cleaned data |
| charts\_starter.py | Run on the reference-cleaned data; all nine charts produced |
| Excel formulas (XLOOKUP, LET, COUNTIFS, DATEVALUE) | Not run in Excel. The Python reference applies the same logic |
| Power Query M code | Not run. Check the folder path and column count (53) |
| VBA macros | Not run. Test on a copy |
| DAX measures | Not run. Compare each with your Excel pivots |

Known limits of the data: technician counts are scaled to the sample (a center has 3 to 7 technicians); work orders were sampled by service area, so volume per center is not realistic; CSAT, hours, revenue and parts delays are simulated; slot counts and rates are assumptions. Date text conversion with DATEVALUE assumes US regional settings.
