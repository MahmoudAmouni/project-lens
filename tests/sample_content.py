"""Text and numbers used to build sample_docs/. Tests use the same values to check answers."""

# (item, description, unit, qty, unit rate, total) - total is always qty x rate
BOQ_PHASE1_ITEMS = [
    ("1.1", "Site clearance", "m2", 15000, 12, 180000),
    ("1.2", "Excavation in all soils", "m3", 42000, 28, 1176000),
    ("1.3", "Backfilling and compaction", "m3", 18000, 22, 396000),
    ("2.1", "Blinding concrete C15", "m3", 900, 310, 279000),
    ("2.2", "Reinforced concrete C40 foundations", "m3", 6200, 780, 4836000),
    ("2.3", "Reinforced concrete columns", "m3", 1450, 920, 1334000),
    ("2.4", "Reinforced concrete slabs", "m3", 5100, 850, 4335000),
    ("2.5", "Waterproofing membrane", "m2", 9800, 65, 637000),
    ("3.1", "Structural steel frame", "t", 1150, 5600, 6440000),
    ("3.2", "Steel roof deck", "m2", 7400, 145, 1073000),
    ("3.3", "Fire protection paint to steel", "m2", 21000, 38, 798000),
    ("4.1", "Blockwork walls 200mm", "m2", 16500, 95, 1567500),
    ("4.2", "External cladding panels", "m2", 8800, 410, 3608000),
    ("4.3", "Aluminium windows", "m2", 2600, 980, 2548000),
    ("4.4", "Main entrance canopy", "item", 1, 865000, 865000),
    ("5.1", "Precast boundary wall", "m", 1200, 690, 828000),
    ("5.2", "Asphalt paving", "m2", 11000, 85, 935000),
]

# (item no, section, description, unit, quantity, amount as typed by a person)
# Rows start at Excel row 5. Section cells B5:B7 and B8:B10 are merged.
BOQ_PHASE2_ITEMS = [
    ("4.1", "Mechanical", "Chillers 500 TR", "No", "2", "SAR 2,400,000"),
    ("4.2", None, "Air handling units", "No", "12", "1.8M"),
    ("4.3", None, "Ductwork, galvanised", "m2", "3,500", "SAR 875,000"),
    ("5.1", "Electrical", "Main LV switchboard", "No", "1", "٩٥٠٬٠٠٠"),
    ("5.2", None, "Cable trays", "m", "4 200", "SAR 630,000.00"),
    ("5.3", None, "LED lighting fixtures", "No", "1,850", "1,110,000"),
    ("6.1", "Finishes", "Porcelain floor tiles", "m2", "8,000", "SAR 1,200,000"),
    ("6.2", "Finishes", "Gypsum ceiling", "m2", "6,500", "Lump sum"),
    ("6.3", "Finishes", "Internal painting", "m2", "22,000", "SAR 920,000"),
]
BOQ_PHASE2_AMOUNTS = [2400000, 1800000, 875000, 950000, 630000, 1110000, 1200000, None, 920000]

# (ref, equipment, qty, price) - this sheet is in US dollars, not SAR
IMPORTED_EQUIPMENT_ITEMS = [
    ("E-1", "Passenger elevators", 4, "USD 310,000"),
    ("E-2", "Escalators", 2, "USD 185,000"),
    ("E-3", "BMS controllers", 1, "$ 95,500"),
]

# (item, description, unit, qty, amount) - printed as a ruled table over two PDF pages
ELECTRICAL_ITEMS = [
    ["E.1", "Medium voltage ring main unit", "No", "2", "SAR 1,450,000"],
    ["E.2", "Transformers 1500 kVA", "No", "3", "2,250,000"],
    ["E.3", "Diesel generator 1250 kVA", "No", "1", "SAR 1,980,000"],
    ["E.4", "Automatic transfer switches", "No", "4", "SAR 360,000"],
    ["E.5", "Sub-main distribution boards", "No", "28", "840,000"],
    ["E.6", "Power cables XLPE", "m", "18,500", "SAR 1,295,000"],
    ["E.7", "Small power outlets", "No", "2,400", "SAR 288,000"],
    ["E.8", "Earthing and lightning protection", "item", "1", "SAR 410,000"],
    ["E.9", "Fire alarm system", "item", "1", "SAR 1,125,000"],
    ["E.10", "CCTV system", "item", "1", "SAR 690,000"],
    ["E.11", "Access control", "item", "1", "SAR 455,000"],
    ["E.12", "Structured cabling", "item", "1", "SAR 980,000"],
]
ELECTRICAL_AMOUNTS = [
    1450000,
    2250000,
    1980000,
    360000,
    840000,
    1295000,
    288000,
    410000,
    1125000,
    690000,
    455000,
    980000,
]

CONTRACT_PAGES = [
    """CONSTRUCTION CONTRACT - RIYADH OFFICE TOWER

Contract No. RT-2026-014
This contract is made on 12 January 2026 between Al Noor Development Company ("the Employer")
and Gulf Build Contracting LLC ("the Contractor").

1. Contract Price
The total contract price is SAR 64,500,000 (sixty-four million five hundred thousand Saudi Riyals),
excluding Value Added Tax. The price is a fixed lump sum for the scope described in Section 2.""",
    """2. Scope of Work
The Contractor shall design, supply, construct and commission a 24-storey office tower with three
basement levels, including:
- substructure and superstructure works (concrete and structural steel),
- facade, cladding and glazing,
- mechanical, electrical and plumbing (MEP) systems,
- internal finishes for common areas,
- external works, landscaping and boundary walls.
Tenant fit-out works are excluded from this contract.""",
    """3. Programme and Key Dates
Commencement date: 1 February 2026.
Completion of substructure: 30 September 2026.
Completion of superstructure: Q2 2027.
Practical completion of the whole works: 31 March 2028.
Defects liability period: 12 months after practical completion.

4. Deliverables
The Contractor shall submit the detailed design drawings by 15 March 2026, the baseline
programme within 28 days of commencement, monthly progress reports by the 5th day of each
month, and the as-built drawings and O&M manuals before practical completion.""",
    """5. Payment Terms
Advance payment: 10% of the contract price against an advance payment guarantee.
Interim payments are made monthly against certified progress, within 45 days of each
approved invoice. Retention of 5% is deducted from each interim payment; half of the
retention is released at practical completion and the rest at the end of the defects liability period.

6. Delay Damages
Delay damages are SAR 50,000 per day, capped at 10% of the contract price.

7. Governing Law
This contract is governed by the laws of the Kingdom of Saudi Arabia.""",
]

SPEC_TOPICS = [
    "concrete",
    "reinforcement",
    "structural steel",
    "masonry",
    "waterproofing",
    "doors and windows",
    "plastering",
    "painting",
    "tiling",
    "ceilings",
    "HVAC",
    "electrical",
]


def long_spec_page(number: int) -> str:
    """One page of the 220-page technical specification."""
    topic = SPEC_TOPICS[(number - 1) % len(SPEC_TOPICS)]
    text = (
        f"TECHNICAL SPECIFICATIONS - SECTION {number:03d}: {topic.upper()}\n\n"
        f"{number}.1 General. This section covers the requirements for {topic} works. "
        "All materials shall comply with the Saudi Building Code (SBC) and approved samples.\n"
        f"{number}.2 Submittals. Submit shop drawings and method statements for {topic} "
        "at least 21 days before starting the work.\n"
        f"{number}.3 Quality control. Inspection and testing shall follow the approved ITP.\n"
    )
    if number == 137:
        text += "137.4 Curing. Concrete shall be kept continuously moist for a curing period of 7 days.\n"
    return text


ARABIC_SCOPE_HTML = """
<div dir="rtl">
<h2>نطاق العمل - مشروع برج الرياض</h2>
<p>يقوم المقاول بتنفيذ أعمال الهيكل الخرساني والواجهات والأعمال الكهروميكانيكية للبرج.</p>
<p>تبلغ قيمة أعمال الواجهات ٢٥٠٠٠٠٠ ريال سعودي</p>
<p>تاريخ البدء: ١ فبراير ٢٠٢٦، ومدة التنفيذ ٢٦ شهراً.</p>
</div>
"""
