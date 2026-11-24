I'll help you prepare the submission for the E-600 wire schedule of Building 4210. Let me check the documents now.

The data room contains all the necessary documents in `/filesystem/electrical__lv_cable_sizing__blind/project/`. I'll review the criteria, standards, and specifications to understand the requirements for the wire schedule.I'll start by reading the main task description and understanding the structure of the data room.

```json
{
  "directory": "/filesystem/electrical__lv_cable_sizing__blind/",
  "command": "ls -A && find . -maxdepth 3 -type f | head -50"
}
```

✿RESULT✿
```
./
./task.md
./project/
./project/criteria/
./project/owner/
./project/specs/
./project/drawings/
./project/schedules/
./project/site/
./project/vendor/
./project/procurement/
./LICENSE
./README.md

./project/criteria/NEC_2020.pdf
./project/criteria/IEEE Std 491-2016.pdf
./project/criteria/IEEE Std 519-2014.pdf
./project/criteria/MODEC_Tech_Rules.pdf
./project/owner/Naval_Base_Electrical_Design_Stdd_Supersedes_CHP-1104.pdf
./project/owner/Naval_Base_Electrical_Design_Stdd_CHP-1104M-2020.pdf
./project/specs/DOD_SPEC_4980.0007_ENERGY_TRANSMISSION_AND_DISTRIBUTION_EQUIPMENT.pdf
./project/specs/DODD_2400.01_01-Mar-2015_ISSUANCE_OF_THE_INSTALLATION_ENERGY_DISTRIBUTION_SYSTEM_BASIC_REQUIREMENTS_STATEMENT_IESBRSS_Version_2.1.2.pdf
./project/specs/INSTALLATION_SPECIFICATION_ENERGY_DISTRIBUTION_SYSTEMS_C5210-3800-XXX.pdf
./project/drawings/E-100_One_Line_Diagram.pdf
./project/drawings/E-400_Panel_Riser_Diagram.pdf
./project/schedules/Building_4210_Connected_Load_and_Motor_Schedule.xlsx
./project/schedules/E-400_Panel_Riser_Data.xlsx
./project/site/CONSOLE_SF_Location_Map.pdf
./project/site/Metadata_JointBaseWeatherStn_ConsolidatedSF.pdf
./project/site/NAVY_BASE_CONSOLIDATED_SUPPORT_FACILITY_SiteInvestigation_Report.pdf
./project/site/NDBC_CumberlandIsland_COOP_Station_PrecipitationRainfall_Trend_30Year.xlsx
./project/site/OFFSHORE_wind_speed_2022.csv
./project/site/SITE_investigation_figures/
./project/site/SITE_investigation_figures/Fig_02.jpg
./project/site/SITE_investigation_figures/Fig_03.jpg
./project/site/SITE_investigation_figures/Fig_04.jpg
./project/site/SITE_investigation_figures/Fig_05.jpg
./project/site/SITE_investigation_figures/Fig_06.jpg
./project/site/SITE_investigation_figures/Fig_07.jpg
./project/site/SITE_investigation_figures/Fig_08.jpg
./project/site/SITE_investigation_figures/Fig_09.jpg
./project/site/SITE_investigation_figures/Fig_10.jpg
./project/site/SITE_investigation_figures/Fig_11.jpg
./project/site/SITE_investigation_figures/Fig_12.jpg
./project/site/SITE_investigation_figures/Fig_13.jpg
./project/site/SITE_ininvestigation_tables/Table_01.csv
./project/site/SITE_ininvestigation_tables/Table_02.csv
./project/site/SITE_ininvestigation_tables/Table_03.csv
./project/site/SITE_ininvestigation_tables/Table_04.csv
./project/vendor/Cable_Engineering_Data_and_Price_List_NAVEDTEC_CABLES.pdf
./project/vendor/NAVEDTEC_Cable_Price_List.xlsx
./project/procurement/UNIT_PRICE_BOOK_2024_02.xls
```

Now I'll read the task.md to understand the detailed requirements.

```json
{
  "file": "task.md",
  "command": "cat task.md"
}
```

✿RESULT✿
```
# Low-voltage wire schedule — Building 4210, Consolidated Support Facility

This brief has two parts. **Engineering brief** is the job, as the engineer of record would
receive it. **Benchmark submission requirements** says how the package is filed and scored here;
it is scaffolding of this benchmark, not part of a real project.

# Part 1 — Engineering brief

You are the electrical engineer of record for a new consolidated support facility at a naval
installation. The project data room — the folder of project documents issued to the design
team — is in `/filesystem/electrical__lv_cable_sizing__blind/project/`: the governing federal criteria in `/filesystem/electrical__lv_cable_sizing__blind/criteria/`, the installation's own
electrical design standard in `/filesystem/electrical__lv_cable_sizing__blind/owner/`, the contract
specifications in `/filesystem/electrical__lv_cable_sizing__blind/specs/`, the issued-for-construction drawing set in `/filesystem/electrical__lv_cable_sizing__blind/drawings/`, the
equipment, connected-load and motor schedules in `/filesystem/electrical__lv_cable_sizing__blind/schedules/`, the site investigation, climate
record, coordination memoranda and the utility's service letter in `/filesystem/electrical__lv_cable_sizing__blind/site/`, the cable
engineering data and price list in `/filesystem/electrical__lv_cable_sizing__blind/vendor/`, and the unit price book in `/filesystem/electrical__lv_cable_sizing__blind/procurement/`.

The one-line series is drawn, the equipment is procured and released for manufacture, and the
overcurrent devices are set. **What is missing is the wire.** Specify the type, material and
size of every low-voltage feeder and branch circuit in the scope, using parallel sets when
necessary, the equipment grounding conductor, the raceway and — for the circuits that run
underground — the ductbanks, as well. Publish the result as the wire schedule sheet of the
E-600 series, and **minimise the installed cost of the conductor package** while satisfying
every requirement the data room imposes, including the codes of record the project was
designed under.

Nothing in this brief tells you a design value, a limit, a formula or a temperature. Every
number you need — the ampacity model and its constants, the corrections, the thermal properties
of the ground, the ambient temperatures, the voltage-drop limits and the load each class of
circuit is calculated at, the termination ratings, the routing and length rules, the
standardisation and procurement limits, the codes of record and their editions, and the
prices — is in the documents, and finding which document carries which is part of the work.
Circuit lengths are not tabulated anywhere: they are measured from the plans and the riser
diagram. Where two documents disagree, or where one has been superseded, the data room says
which governs, and your design basis has to say what you resolved and why.

The circuits are not decided independently of one another. They share a voltage-drop budget
along each path from the source, they share the thermal environment of a duct bank and of a
roof cable tray.

## Deliverables

Five files.

### 1. `wire_schedule.csv`

One row per circuit, every circuit in the connected load schedule, 32 rows. Columns, exactly
these names:

```
circuit, description, from, to, install_class, length_ft, sets, size, material, egc_size,
raceway_trade_in, duct_ids, design_current_a, corrected_ampacity_a, vd_load_a, vd_pct,
cumulative_vd_pct, ambient_c, ccc, governing_constraint, ocpd_a, system_voltage_v, phases,
power_factor, r_ohm_per_kft, x_ohm_per_kft, drop_v
```

* `size` and `egc_size` are trade sizes: `12`, `10`, `8`, `6`, `4`, `3`, `2`, `1`, `1/0`, `2/0`,
  `3/0`, `4/0`, `250 kcmil` … `750 kcmil`. `material` is `CU` or `AL`.
* `length_ft` is the length your calculation used. `sets` is the number of parallel sets.
* `raceway_trade_in` is the conduit trade size in inches, for circuits in interior raceway only.
  `duct_ids` names the duct each set occupies, for duct-bank circuits only.
* `design_current_a` is the current the conductor's corrected ampacity had to carry;
  `corrected_ampacity_a` is the ampacity per set that your selection actually has after every
  correction, adjustment and limit; `vd_load_a` is the current your voltage-drop calculation
  used, which is not necessarily either of the other two.
* `vd_pct` is this circuit's own voltage drop; `cumulative_vd_pct` is the voltage drop at the
  load at the end of this circuit, counted from the calculation starting point. Voltage drop is
  not held to one number: feeders, branch circuits and the total at the load each have their
  own limit, and some equipment has limits of its own. Which limit applies to which circuit is
  set by the governing criteria in the data room.
* `ambient_c` and `ccc` are the ambient temperature and the number of current-carrying
  conductors the design assumed for this circuit.
* `governing_constraint` names, in your own words, the requirement or requirements that decided
  this conductor's size. More than one can bind at once; name the ones that did.
* The last seven columns let a reviewer audit the schedule. `ocpd_a` is the rating, in amperes,
  of the overcurrent protective device of the circuit. `system_voltage_v`, `phases`,
  `power_factor`, `r_ohm_per_kft` and `x_ohm_per_kft` (the conductor resistance and reactance per
  1000 ft) are the values your voltage-drop calculation used for this circuit, and `drop_v` is the
  circuit's own voltage drop in volts.

### 2. `E-621_wire_schedule.dxf`

The contract sheet. A DXF carrying a title block that names the project number and the sheet
number E-621, and the schedule itself: one line per circuit, starting with the circuit
designation, carrying the columns of `wire_schedule.csv` in the same order (abbreviated headers
and values are fine, with an abbreviation list on the sheet), and agreeing with
`wire_schedule.csv` on the circuit designation and the conductor size.

### 3. `calc_book.xlsx`

The calculation front sheet — the parameters your calculation stands on, so that a reviewer can
reproduce it. A workbook with exactly these three sheets, each with the header row shown as its
first row.

Sheet `front_sheet`:

```
parameter, value, unit, source_document, clause
```

one row per parameter, with at least these parameters:

```
outdoor_design_dry_bulb_c, roof_ambient_c, earth_ambient_c,
soil_thermal_resistivity_k_m_w, encasement_thermal_resistivity_k_m_w,
solar_irradiance_w_m2, load_factor, termination_allowance_ft, vd_start_point,
vd_limit_feeder_pct, vd_limit_branch_pct, vd_limit_total_pct, mutual_heating_rise_k,
tray_sum_od_in, distinct_large_sizes, ampacity_basis, total_usd
```

`ampacity_basis` states the basis of the ampacities used: the method, and the code article that
permits it. `soil_thermal_resistivity_k_m_w` is the resistivity your earth and mutual-heating
terms actually used; a value you considered and rejected goes in a row of its own. `source_document` and `clause` say where each value came from.

Sheet `duct_assignment`:

```
circuit, set, duct
```

one row per parallel set of each duct-bank circuit. Write duct identifiers as the duct-bank
sections label them.

Sheet `cost_ledger`:

```
line, quantity, unit, material_usd, labor_usd, amount_usd
```

your ledger — conductor, terminations and raceway, with any project-wide price adjustment as a
line of its own — at the project's own unit prices, each line showing its material and its
labour content, and a last row whose `line` is `Total`. `total_usd` on the front sheet is the
installed cost of the package and equals the ledger total.

### 4. `design_basis.md`

The engineering narrative, opening with a fenced ```json block carrying at least:

```
codes_of_record {nfpa70_edition, ibc_edition, adopted_by, precedence},
environment {outdoor_design_dry_bulb_c, roof_ambient_c, earth_ambient_c,
            soil_thermal_resistivity_k_m_w, solar_irradiance_w_m2},
sources     {which document each of those came from},
voltage_drop {start_point, transformer_reset, feeder_chain_pct, branch_limit_pct,
             total_limit_pct},
cost        {conductor_usd, termination_usd, raceway_usd, material_usd, labor_usd, total_usd},
duct_assignment, mutual_heating_rise_k
```

In that block `precedence` is the rule that decides between two criteria that set different
limits, `adopted_by` names the document that adopts the two codes, `transformer_reset` says
whether the voltage-drop count restarts at the low-voltage transformer, `feeder_chain_pct` is
the voltage drop your feeder chains actually spend (one number, or one per chain) and
`duct_assignment` maps each duct-bank circuit to the ducts its sets occupy.

and then the prose: the codes of record the design was prepared against, the document that
adopts them and the order of precedence among the criteria; the environmental parameters and
their provenance; how the voltage-drop budget was allocated along the chain, what the
starting point is, whether the count restarts at the low-voltage transformer and how many branch
circuits inherit the budget spent upstream of their panel; the service-entrance sizing decision; the duct-bank assignment, how many
ducts of the service duct bank were available to it, and its thermal consequence for the other
circuits in the bank; the material and standardisation
decisions; and the cost ledger, material and labour.

### 5. `constraint_register.xlsx` — the code-compliance matrix

A federal Basis of Design carries a criteria log: the requirements the design was held to, each
traced to its document and clause. Here it is filed as a workbook and scored, because it is how
this benchmark tells a design that was engineered to a requirement from one that met it by
chance. One requirement per row, in a sheet whose header row carries exactly these columns:

```
req_id, document, clause, requirement, value, unit, kind, applies_to, resolution
```

`document` is the source document, `clause` its clause, table, section or sheet identifier,
`value` the number the requirement fixes where it fixes one, `kind` HARD or SOFT,
`applies_to` the circuits or the part of the package it binds, and `resolution` how you applied
it, including how you resolved any conflict. **One row states one requirement**: a row is
credited with at most one of them, and a row that cites several clauses at once, or carries a
list of unrelated values, is not a register row and counts against precision. Register the
requirements you actually engineered to: a requirement you satisfied but never registered does
not count as engineered, and a requirement you registered but did not satisfy does not either.
Rows that cite a superseded document, a document that is not in the data room, or a product
that is not the basis of design, as though it governed, reduce the register's precision —
unless the row itself says that the document does not govern. A national code that the data
room adopts by reference but does not contain may be cited by name and article; such a row is
neutral. Extra correct rows are neutral: a thorough register is never penalised for being long.
The first 400 rows are scanned and the precision floor is 0.6.

# Part 2 — Benchmark submission requirements

Write `output/submission.zip` (at most 25 MB and 200 files) containing the four files above and
the register below, five files at the top level.

### 5. `constraint_register.xlsx` — the code-compliance matrix

A federal Basis of Design carries a criteria log: the requirements the design was held to, each
traced to its document and clause. Here it is filed as a workbook and scored, because it is how
this benchmark tells a design that was engineered to a requirement from one that met it by
chance. One requirement per row, in a sheet whose header row carries exactly these columns:

```
req_id, document, clause, requirement, value, unit, kind, applies_to, resolution
```

`document` is the source document, `clause` its clause, table, section or sheet identifier,
`value` the number the requirement fixes where it fixes one, `kind` HARD or SOFT,
`applies_to` the circuits or the part of the package it binds, and `resolution` how you applied
it, including how you resolved any conflict. **One row states one requirement**: a row is
credited with at most one of them, and a row that cites several clauses at once, or carries a
list of unrelated values, is not a register row and counts against precision. Register the
requirements you actually engineered to: a requirement you satisfied but never registered does
not count as engineered, and a requirement you registered but did not satisfy does not either.
Rows that cite a superseded document, a document that is not in the data room, or a product
that is not the basis of design, as though it governed, reduce the register's precision —
unless the row itself says that the document does not govern. A national code that the data
room adopts by reference but does not contain may be cited by name and article; such a row is
neutral. Extra correct rows are neutral: a thorough register is never penalised for being long.
The first 400 rows are scanned and the precision floor is 0.6.

## How this is graded

Each of the circuits in the graded set is scored

```
score = 0.4 · p  +  0.6 · [h = 1* , else 0. A row that is missing or unreadable scores 0. The hard families include
  the declaration of the codes of record, the voltage-drop budget allocation and the duct
  assignment in the design basis, not only the conductor selections.
* `O′` is the credit for the installed cost of the package, measured against a certified lower
  bound on the cost of any compliant design and rescaled onto the band between a named naive
  baseline and a package cheaper than the reference design. A hard violation withholds it: a cheap
  package that fails any of its hard families keeps none of it. An incomplete package gains nothing
  either: a circuit left out of the schedule is charged at
  the naive baseline's cost for it.
* The cost that is scored is the one the grader recomputes from your own selections and the
  project's unit prices, not the one you declare — but the two must agree, and where the ledger
  shows material and labour they must add up to it.

Feasibility is judged on what your selections actually do when the project's own methods are
applied to them, and the declared columns are judged on whether they show the right rule was
applied. Both matter.

How the files are read: the schedule on E-621 is read from the sheet's text entities (TEXT or
MTEXT), not from its geometry. Workbook cells are read as stored values, so write numbers, not
formulas. Limits are judged with a small allowance for the rounding of the published cable
data: an ampacity may be taken as the vendor's tables print it or as their stated method computes
it, and a voltage-drop limit counts as met within 0.02 of a percentage point. In the ledger the
conductor line may be shown before or after any project-wide price adjustment.

You have no access to the verifier and no scoring oracle. Write a first complete version of all
five files early, then improve it in place: the last version on disk when the run ends is what
gets graded, and a run that exhausts its step or token budget with no file scores 0.Let's start by reviewing the main documents that will guide this design.

```json
{
  "directory": "/filesystem/electrical__lv_cable_sizing__blind/",
  "command": "find project -type f -name '*.pdf' -o -name '*.xls*' -o -name '*.xlsx' -print | head -20"
}
```

✿RESULT✿
```
project/criteria/NEC_2020.pdf
project/criteria/IEEE Std 491-2016.pdf
project/criteria/IEEE Std 519-2014.pdf
project/criteria/MODEC_Tech_Rules.pdf
project/owner/Naval_Base_Electrical_Design_Stdd_Supersedes_CHP-1104.pdf
project/owner/Naval_Base_Electrical_Design_Stdd_CHP-1104M-2020.pdf
project/specs/DOD_SPEC_4980.0007_ENERGY_TRANSMISSION_AND_DISTRIBUTION_EQUIPMENT.pdf
project/specs/DODD_2400.01_01-Mar-2015_ISSUANCE_OF_THE_INSTALLATION_ENERGY_DISTRIBUTION_SYSTEM_BASIC_REQUIREMENTS_STATEMENT_IESBRSS_Version_2.1.2.pdf
project/specs/INSTALLATION_SPECIFICATION_ENERGY_DISTRIBUTION_SYSTEMS_C5210-3800-XXX.pdf
project/site/NDBC_CumberlandIsland_COOP_Station_PrecipitationRainfall_Trend_30Year.xlsx
project/vendor/Cable_Engineering_Data_and_Price_List_NAVEDTEC_CABLES.pdf
project/vendor/NAVEDTEC_Cable_Price_List.xlsx
project/procurement/UNIT_PRICE_BOOK_2024_02.xls
```

Now let's read the important supporting documents.

```json
{
  "file": "project/site/NDBC_CumberlandIsland_COOP_Station_PrecipitationRainfall_Trend_30Year.xlsx",
  "command": "file {file}; head -20 {file}"
}
```

✿RESULT✿
```
project/site/NDBC_CumberlandIsland_COOP_Station_PrecipitationRainfall_Trend_30Year.xlsx: Excel HTML worksheet data, v1.0
  Year Rainfall (inches)
0  2024    45.39
1  2023    62.95
2  2022    46.44
3  2021    52.98
4  2020    49.79
5  2019    54.25
6  2018    43.48
7  2017    50.97
8  2016    49.08
9  2015    44.41
```

Looks like precipitation data, possibly relevant for outdoor exposure considerations.

Let's examine the Connected Load Schedule.

```json
{
  "file": "project/schedules/Building_4210_Connected_Load_and_Motor_Schedule.xlsx",
  "command": "file {file}; head -20 {file}"
}
```

✿RESULT✿
```
project/schedules/Building_4210_Connected_Load_and_Motor_Schedule.xlsx: Microsoft Excel Worksheet
A         B          C     D      E               F
Circuit   Description Equipment Type kW kVA PF @ Base HP
1        ACQ-100A    Panel A   50.0 62.5 0.80 3
2        ACQ-100B    Panel B   50.0 62.5 0.80 3
3        ACQ-101A    Panel A   50.0 62.5 0.80 3
4        ACQ-101B    Panel B   50.0 62.5 0.80 3
5        ACQ-200A    Panel A   50.0 62.5 0.80 3
6        ACQ-200B    Panel B   50.0 62.5 0.80 3
7        ACQ-201A    Panel A   50.0 62.5 0.80 3
8        ACQ-201B    Panel B   50.0 62.5 0.80 3
9        ACQ-300A    Panel A   50.0 62.5 0.80 3
10       ACQ-300B    Panel B   50.0 62.5 0.80 3
11       ACQ-301A    Panel A   50.0 62.5 0.80 3
12       ACQ-301B    Panel B   50.0 62.5 0.80 3
13       ACQ-400A    Panel A   50.0 62.5 0.80 3
14       ACQ-400B    Panel B   50.0 62.5 0.80 3
15       ACQ-401A    Panel A   50.0 62.5 0.80 3
16       ACQ-401B    Panel B   50.0 62.5 0.80 3
17       ACQ-500A    Panel A   50.0 62.5 0.80 3
18       ACQ-500B    Panel B   50.0 62.5 0.80 3
19       ACQ-501A    Panel A   50.0 62.5 0.80 3
20       ACQ-501B    Panel B   50.0 62.5 0.80 3
```

This is the main load schedule with 32 circuits, each having an A and B panel.

Now let's look at the Panel Riser Data.

```json
{
  "file": "project/schedules/E-400_Panel_Riser_Data.xlsx",
  "command": "file {file}; head -20 {file}"
}
```

✿RESULT✿
```
project/schedules/E-400_Panel_Riser_Data.xlsx: Microsoft Excel Worksheet
A        B          C   D   E   F   G   H
Panel  Location Feeder  Ckt Circuit Descr  Phase Amps Volts
A         HQ Feed    FA  1    MAIN_A           3   200 480
A         HQ Feed    FA  2    XFRR_A           3   200 480
A         HQ Feed    FA  3    GEN_A            3   200 480
A         HQ Feed    FA  4    PS_A             3   200 480
A         HQ Feed    FA  5    SMPL_A           3   200 480
A         HQ Feed    FA  6    PDU_A            3   200 480
A         HQ Feed    FA  7    ACQ-100A         3   100 480
A         HQ Feed    FA  8    ACQ-101A         3   100 480
A         HQ Feed    FA  9    ACQ-200A         3   100 480
A         HQ Feed    FA  10   ACQ-201A         3   100 480
A         HQ Feed    FA  11   ACQ-300A         3   100 480
A         HQ Feed    FA  12   ACQ-301A         3   100 480
A         HQ Feed    FA  13   ACQ-400A         3   100 480
A         HQ Feed    FA  14   ACQ-401A         3   100 480
A         HQ Feed    FA  15   ACQ-500A         3   100 480
A         HQ Feed    FA  16   ACQ-501A         3   100 480
B         HQ Feed    FB  1    MAIN_B           3   200 480
B         HQ Feed    FB  2    XFRR_B           3   200 480
B         HQ Feed    FB  3    GEN_B            3   200 480
B         HQ Feed    FB  4    PS_B             3   200 480
```

This shows the panel-to-feeder relationships and also identifies our 32 circuits across Panels A and B.

Now let's verify the drawings exist.

```json
{
  "file": "project/drawings/E-100_One_Line_Diagram.pdf",
  "command": "file {file} || echo Not found"
}
```

✿RESULT✿
```
project/drawings/E-100_One_Line_Diagram.pdf: PDF document, version 1.4
```

The one-line diagram is present.

```json
{
  "file": "project/drawings/E-400_Panel_Riser_Diagram.pdf",
  "command": "file {file} || echo Not found"
}
```

✿RESULT✿
```
project/drawings/E-400_Panel_Riser_Diagram.pdf: PDF document, version 1.4
```

The panel riser diagram is also present, which will allow us to measure circuit lengths.

Before proceeding, let's list the owner standards for wire and cable selection.

```json
{
  "file": "project/owner/Naval_Base_Electrical_Design_Stdd_CHP-1104M-2020.pdf",
  "command": "grep -i \"wire.*cable\" {file} | head -50"
}
```

✿RESULT✿
```
%!PS-Adobe-3.0 EPSF-3.0
%%BoundingBox: 0 0 612 792
%%HiResBoundingBox: 0.000000 0.000000 612.000000 792.000000
%APL Finally this is an automatically generated file.  Do NOT modify this file.
%Warning: Font Helvetica not found. Using Font Arial instead.
...
Section 3. Wire and Cable
3.1 General
Wire and cable used in the construction of new power and communication systems shall be rated 
for the applicable voltage, temperature, and load conditions and shall conform to the appropr...
3.2 Standard Types
Standard types of wires and cables specified in this section shall be used whenever practica...
3.2.1 Copper Conductors
Copper conductors shall comply with ASTM B3, standard specifications for soft-drawn copper co...
3.2.2 Conductors - Thermoplastic and Synthetic Polymer Insulated Cables
Conductors rated 0 through 2000 volts nominal shall be thermoplastic insulated, except as indic...
3.3 Special Types
When special types of wire and cable are required due to specific environmental, mechanical, or ...
3.3.1 Underground Buried Cables
Underground cables used for feeders and branch circuits shall be direct buried or placed in con...
3.3.2 Underground Conduit System
Underground cables shall be run in raceways (conduit) where physical damage protection is requir...
3.3.3 Overhead Cables
Overhead cables shall be used only where underground or cable tray is impractical and shall b...
3.3.4 Explosion-Proof and Hazardous Location
Wires and cables installed in hazardous (classified) locations shall comply with Article 501, 50...
3.3.5 Fire-Resistance Ratings
Wires and cables rated 600 volts or less intended for use in fire-resistance-rated power distri...
3.3.6 Communication Cables
Communication cables (voice, data, video) shall comply with TIA-568-C.2 balanced twisted-pair c...
3.3.7 Fiber Optic Cables
Fiber optic cables shall comply with industry standards, such as TIA-568-C.3, TIA-569-C, and ...