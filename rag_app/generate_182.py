#!/usr/bin/env python3
"""Generate 182_final.xls (CSV-format) with examples and edge-cases.
Writes the file next to this script.
"""
from pathlib import Path
import csv

rows = [
    ["part_no","Part name","slno","section name","total electors","total part votes"],
    ["1","GovernmentTribalResidanceMiddleSchool-Thalvallam-636138,TerracedBuildingFacingwestNorthWing","1","1-Koilputhur(R.V),PeriyakalrayanMelnadu(P),Ward1,Koilputhur 1","749","224"],
    ["1","GovernmentTribalResidanceMiddleSchool-Thalvallam-636138,TerracedBuildingFacingwestNorthWing","2","2-Koilputhur(R.V),PeriyakalrayanMelnadu(P),Ward1,Melvallam 220","749","151"],
    ["1","GovernmentTribalResidanceMiddleSchool-Thalvallam-636138,TerracedBuildingFacingwestNorthWing","3","3-Koilputhur(R.V),PeriyakalrayanMelnadu(P),Ward1,Perandoor 368","749","374"],
    ["2","GovernmentTribalResidanceMiddleSchool-Thalvallam-636138,TerracedBuildingFacingNorthWestWing","1","1-Koilputhur(R.V),PeriyakalrayanMelnadu(P),Ward1,Morasampatty 1","790","169"],
    ["2","GovernmentTribalResidanceMiddleSchool-Thalvallam-636138,TerracedBuildingFacingNorthWestWing","2","2-Koilputhur(R.V),PeriyakalrayanMelnadu(P),Ward1,Thalvallam 165","790","621"],
    # Edge case: dot characters in part name and multi-line section name
    ["3","c.s.v. Hall Building","1","1-EdgeSection,ExampleWard,LineA\nContinuation of section name on second line","500","123"],
]

out = Path(__file__).resolve().parent / "182_final.xls"
with open(out, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    for r in rows:
        writer.writerow(r)

print(f"Wrote: {out}")
