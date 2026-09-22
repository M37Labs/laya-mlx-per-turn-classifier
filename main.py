import laya_mlx as laya

agent = laya.load("aac6fef/laya-mlx")
result = agent.predict(
    "I was billed twice. Please refund the duplicate today.",
    {
        "department": {
            "type": "choice",
            "instructions": "Which team handles this?",
            "criteria": {
                "billing": "invoices, charges, refunds on existing accounts",
                "technical": "bugs, errors, outages",
                "sales": "purchases, pricing, plans, upgrades, new customers",
            },
        },
        "urgency": {
            "type": "score",
            "instructions": "How urgent?",
            "criteria": ["not urgent", "soon", "critical"],
        },
        "refund": {
            "type": "noul",
            "instructions": "Does the customer ask for money back?",
        },
    },
)
print(result["answers"])
