I have completed the structural design for the roof deck of Building A of the DC-2 Helena Data Centre and generated the required submission package at `output/submission.zip`.

### Summary of Deliverables & Key Results

1. **`deck_design.xlsx`** (located at the root of `output/submission.zip`):
   - **Zones**: Defined 9 non-overlapping rectangular zones (grouped into 3 distinct zones: `ZONE-PERIM`, `ZONE-INT`, `ZONE-DRIFT`) utilizing 20 gage and 18 gage NORDECK B-36 steel deck (16 gage excluded due to a 14-week lead time exceeding the Owner's 9-week procurement allowance). All perimeter and opening boundaries comply with the mandatory `36/7` support pattern and 3 sidelap connectors per span.
   - **DesignBasis**: Tabulated all required design parameters, including ground snow load $p_g = 63\text{ psf}$, flat roof snow load $p_f = 43.66\text{ psf}$, snow density $\gamma = 22.19\text{ pcf}$, unreduced roof live load $L_r = 20\text{ psf}$, velocity pressure $q_h = 29.93\text{ psf}$, $S_{DS} = 0.44$, $I_e = 1.25$, $R = 3.25$, effective seismic weight $w_{seismic} = 26.73\text{ psf}$, roof diaphragm design force $F_{px} = 195.42\text{ kips}$, wind forces ($X = 118.0\text{ kips}$, $Y = 152.0\text{ kips}$), and diaphragm classification (**Semi-rigid**).
   - **Drifts**: Tabulated peak surcharges and plan bounding bands for `MEP-PH-1` face `W` ($104.28\text{ psf}$ surcharge), `SCR-N` face `S` ($89.48\text{ psf}$ surcharge), `PARAPET` face `N` ($34.01\text{ psf}$ surcharge), and `RTU-1` face `E` ($42.42\text{ psf}$ surcharge).
   - **CalcSummary & Diaphragm**: Documented governing scenarios, shear, gravity, and uplift demands and capacities across all zones, and diaphragm responses across all lateral scenarios ($S05$–$S10$). Maximum in-plane shear is $440.0\text{ plf}$ (Scenario $S08$) with a maximum deflection of $0.75\text{ in}$ (well within the $1.60\text{ in}$ limit).
   - **BOM**: Quantified total deck areas by gage, support fasteners, and sidelap connectors.

2. **`roof_deck_plan.dxf`** (located at the root of `output/submission.zip`):
   - Drawn in feet on project grid coordinates, featuring framing on `S-FRAMING`, roof openings on `S-OPENING`, zone rectangles on `S-DECK-ZONE`, and zone ID text labels on `S-DECK-TEXT`.

3. **`constraint_register.xlsx`** (located at the root of `output/submission.zip`):
   - Sheet `Register` containing 26 rigorous compliance rows citing governing clauses from `EOR-DC-RD-01 Rev 2`, `LAT-2026-003 Rev 1`, `SNOW-2026-014 Rev 0`, `OBD-DC2-A`, and technical manuals.

4. **`design_basis.md`** (located at the root of `output/submission.zip`):
   - A comprehensive engineering narrative explaining document governance, snow/seismic loading derivations, diaphragm analysis and semi-rigid classification, and the zoning/procurement decisions.