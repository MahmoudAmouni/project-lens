"""The accuracy evaluation set: 20 questions about sample_docs/ with the facts each answer must contain.

`must` is a list of groups; every group must match, and a group matches when ANY of its texts appears in
the answer or its table. Texts are compared without case, commas or spaces, so "SAR 41,527,500" and
"41527500" both match "41527500". A text starting with "re:" is a regular expression (for whole numbers).
`source` is a file that must appear in the sources or the table.
"""

QUESTIONS = [
    {
        "q": "List all cost items above SAR 1 million",
        "must": [["41527500"], [r"re:\b18\b"]],
        "source": "BOQ_Phase1.xlsx",
    },
    {"q": "Summarize the scope of work", "must": [["24-storey", "24 storey"], ["fit-out"]], "source": "Contract_A.pdf"},
    {
        "q": "Extract all dates and deliverables",
        "must": [["31 march 2028"], ["15 march 2026"], ["as-built", "as built"], ["28 days"]],
        "source": "Contract_A.pdf",
    },
    {
        "q": "What is the warranty period for the elevators?",
        "must": [["not find", "not found", "no specific", "does not", "do not", "not stated", "not mention"]],
    },
    {"q": "ما هي قيمة أعمال الواجهات؟", "must": [["2500000", "٢٥٠٠٠٠٠", "۲٥۰۰۰۰۰"]], "source": "Arabic_Scope.pdf"},
    {
        "q": "What is the total cost of imported equipment and all BOQ items combined?",
        "must": [["53843500"], ["590500"], ["usd"]],
    },
    {
        "q": "What is the total contract price?",
        "must": [["64500000", "64.5 million", "64.5m"]],
        "source": "Contract_A.pdf",
    },
    {"q": "What are the delay damages?", "must": [["50000"], ["10%"]], "source": "Contract_A.pdf"},
    {"q": "How much retention is deducted from interim payments?", "must": [["5%"]], "source": "Contract_A.pdf"},
    {
        "q": "Which BOQ item has the highest amount?",
        "must": [["structural steel frame"], ["6440000", "6.44 million", "6.44m"]],
        "source": "BOQ_Phase1.xlsx",
    },
    {
        "q": "How many items are in the BOQ Phase 2 sheet and what is their total?",
        "must": [["9885000", "9.885 million"]],
        "source": "BOQ_Phase2.xlsx",
    },
    {
        "q": "What is the concrete curing period?",
        "must": [["7 days", "seven days"]],
        "source": "Technical_Specifications.pdf",
    },
    {
        "q": "What does the scanned drawing show?",
        "must": [["scanned", "cannot be read", "could not be read", "can't read", "no readable text", "image"]],
    },
    {
        "q": "What does the protected annex say?",
        "must": [["password", "protected", "encrypted", "cannot be read", "could not be read"]],
    },
    {"q": "What is the price of the escalators in SAR?", "must": [["185000"], ["usd"]], "source": "BOQ_Phase2.xlsx"},
    {"q": "When is practical completion due?", "must": [["31 march 2028"]], "source": "Contract_A.pdf"},
    {
        "q": "List the items in the electrical BOQ that cost less than SAR 500,000",
        "must": [["1513000"], [r"re:\b4\b", "four"]],
        "source": "BOQ_Electrical.pdf",
    },
    {
        "q": "What is the weather in Riyadh today?",
        "must": [["only answer", "loaded documents", "not in the documents", "not related", "cannot", "can't"]],
    },
    {"q": "Who is the contractor?", "must": [["gulf build"]], "source": "Contract_A.pdf"},
    {
        "q": "What is the total quantity of concrete in m3 in BOQ Phase 1?",
        "must": [["13650"]],
        "source": "BOQ_Phase1.xlsx",
    },
]
