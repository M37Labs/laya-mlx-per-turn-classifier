"""Demo use cases. Loaded by migration 0002 and `manage.py seed_use_cases`.

Each field is (key, label, type, instructions, options, min_confidence). Options use the same
one-per-line format as the admin: "label: description" for choices, levels lowest-first for
scores, optional "true: …" / "false: …" for yes/no.
"""

USE_CASES = [
    {
        "slug": "support-triage",
        "name": "Customer Support Triage",
        "industry": "Customer Experience",
        "tagline": "Route every inbound ticket to the right team the moment it arrives.",
        "description": (
            "Every support message is read once and answered on three questions at the same time: "
            "which team owns it, how urgent it is, and whether money is on the line."
        ),
        "business_value": (
            "Removes the manual triage queue. Tickets reach the right desk in milliseconds, urgent "
            "issues skip the line, and refund requests are flagged for finance straight away."
        ),
        "input_label": "Customer message",
        "fields": [
            ("department", "Department", "choice", "Which team handles this?",
             "billing: invoices, charges, refunds on existing accounts\n"
             "technical: bugs, errors, outages\n"
             "sales: purchases, pricing, plans, upgrades, new customers", 0.3),
            ("urgency", "Urgency", "score", "How urgent?",
             "not urgent\nsoon\ncritical", None),
            ("refund", "Refund requested", "noul", "Does the customer ask for money back?", "", 0.7),
        ],
        "examples": [
            ("Duplicate charge", "I was billed twice. Please refund the duplicate today."),
            ("Outage", "Production is down, none of our users can log in! Fix this now!"),
            ("Invoice copy", "Can you send me a copy of last month's invoice when you get a chance?"),
            ("Upgrade", "I'd like to buy 50 more seats for my team. What's the pricing?"),
        ],
    },
    {
        "slug": "banking-servicing",
        "name": "Card & Account Servicing",
        "industry": "Banking",
        "tagline": "Spot fraud reports and disputes in the first message, not the third call.",
        "description": (
            "Classifies secure-message and chat requests from retail banking customers, and flags "
            "the ones that report unauthorised activity."
        ),
        "business_value": (
            "Fraud reports reach the fraud team in real time, which cuts losses and meets "
            "regulatory response windows. Routine requests go straight to self-service."
        ),
        "input_label": "Customer secure message",
        "fields": [
            ("request", "Request type", "choice", "What is the customer asking the bank to do?",
             "fraud: report charges or activity the customer did not make, e.g. card used by "
             "someone else, unknown transactions\n"
             "dispute: a purchase the customer did make but has a problem with the merchant, "
             "e.g. item never arrived, wrong amount\n"
             "access: locked out, password, card blocked, app login problems\n"
             "lending: loans, mortgages, credit limit increases\n"
             "general: statements, fees, branch hours, other questions", 0.3),
            ("unauthorised", "Unauthorised activity", "noul",
             "Does the customer report transactions they did not make or recognise?", "", 0.7),
            ("risk", "Customer financial risk", "score",
             "How much financial harm could the customer suffer if this waits?",
             "none\nsome inconvenience\nongoing loss of money", None),
        ],
        "examples": [
            ("Unknown charges", "There are three charges on my card from a store in another country. "
                                "I've never been there and my card is in my wallet."),
            ("Item not received", "I paid a merchant $240 two weeks ago and the order never arrived. "
                                  "They won't reply. Can you help me get it back?"),
            ("Locked out", "The app keeps saying my account is locked after I changed phones."),
            ("Credit limit", "What would I need to qualify for a higher credit limit?"),
        ],
    },
    {
        "slug": "patient-messages",
        "name": "Patient Portal Messages",
        "industry": "Healthcare",
        "tagline": "Put clinical concerns in front of a clinician and admin requests in front of admin.",
        "description": (
            "Reads patient portal messages and decides where each one goes, how quickly it needs a "
            "response, and whether it describes symptoms a clinician should review."
        ),
        "business_value": (
            "Nurses stop spending hours sorting inboxes. Messages describing worrying symptoms are "
            "surfaced within seconds, and scheduling or billing requests never reach clinical staff."
        ),
        "input_label": "Patient message",
        "fields": [
            ("route", "Route to", "choice", "Which team should handle this message?",
             "scheduling: booking, moving or cancelling appointments\n"
             "prescriptions: refills, pharmacy questions, medication supply\n"
             "billing: bills, insurance, payments\n"
             "clinical: symptoms, side effects, test results, medical questions", 0.3),
            ("urgency", "Clinical urgency", "score", "How quickly does a clinician need to see this?",
             "routine, within a few days\nwithin 24 hours\nimmediately, possible emergency", None),
            ("symptoms", "New or worsening symptoms", "noul",
             "Does the patient describe new or worsening symptoms?", "", 0.7),
        ],
        "examples": [
            ("Chest pain", "Since this morning I've had chest tightness and I feel short of breath "
                           "walking up stairs. Should I be worried?"),
            ("Refill", "Can you send a refill for my blood pressure medication to the usual pharmacy?"),
            ("Reschedule", "I need to move my Thursday appointment to next week if possible."),
            ("Insurance bill", "I got a bill for my last visit but I thought insurance covered it."),
        ],
    },
    {
        "slug": "hr-helpdesk",
        "name": "Employee Helpdesk",
        "industry": "Human Resources",
        "tagline": "Answer routine HR questions instantly and escalate sensitive ones safely.",
        "description": (
            "Classifies employee tickets by topic and gauges how the employee feels. Conduct "
            "complaints (harassment, discrimination, bullying, unsafe conditions) are identified "
            "so they go to an HR partner, not a chatbot."
        ),
        "business_value": (
            "Routine questions (most of the volume) go to self-service. Sensitive cases reach a "
            "trained person the same day, which lowers legal and reputational risk."
        ),
        "input_label": "Employee ticket",
        "fields": [
            ("topic", "Topic", "choice", "What is the employee's ticket about?",
             "payroll: pay, payslips, tax, expenses\n"
             "leave: holiday, sick leave, parental leave\n"
             "benefits: health plan, pension, perks\n"
             "it_access: laptop, accounts, system access\n"
             "conduct: complaints about how a colleague or manager behaves: harassment, "
             "discrimination, bullying, unsafe conditions", 0.3),
            ("sentiment", "Employee sentiment", "score", "How is the employee feeling?",
             "positive\nneutral\nfrustrated\ndistressed", None),
        ],
        "examples": [
            ("Payslip", "My payslip this month is missing the overtime I worked in the last week."),
            ("Parental leave", "How many weeks of parental leave am I entitled to? Baby due in March."),
            ("Manager conduct", "My manager keeps making comments about my accent in front of the team "
                                "and I don't feel comfortable going to meetings anymore."),
            ("Laptop", "My laptop won't connect to the VPN since the update."),
            ("Blocked exit", "The fire exit on floor 3 has been blocked by boxes for a week."),
        ],
    },
    {
        "slug": "order-feedback",
        "name": "Order Feedback",
        "industry": "Retail & E-commerce",
        "tagline": "Read every review and post-purchase message, and know what went wrong.",
        "description": (
            "Classifies customer reviews and order messages by what went wrong (the product, the "
            "delivery, or the fit) and measures how the customer feels."
        ),
        "business_value": (
            "Merchandising sees defect trends by product, logistics sees carrier problems, and "
            "unhappy customers are contacted before they post a one-star review. No manual "
            "reading needed."
        ),
        "input_label": "Review or order message",
        "fields": [
            ("issue", "Issue", "choice", "What went wrong with the order?",
             "defect: product broken, faulty or poor quality\n"
             "delivery: parcel late, lost or damaged in transit\n"
             "size: wrong size or doesn't fit\n"
             "nothing: customer is happy, no problem", 0.3),
            ("sentiment", "Customer sentiment", "score", "How does the customer feel about the purchase?",
             "very unhappy\nunhappy\nneutral\nhappy\ndelighted", None),
        ],
        "examples": [
            ("Broken blender", "The blender stopped working after two days. Really disappointed, "
                               "I want to send it back."),
            ("Late parcel", "Ordered a week ago, still not here, tracking hasn't moved since Monday."),
            ("Too small", "Lovely jacket but the medium is way too small. Can I swap it for a large?"),
            ("Five stars", "Absolutely love these headphones, best purchase this year!"),
        ],
    },
    {
        "slug": "claims-intake",
        "name": "Claims First Notice of Loss",
        "industry": "Insurance",
        "tagline": "Triage new claims on arrival: line of business, severity, injuries.",
        "description": (
            "Reads a policyholder's first description of a loss and sets up the claim: which line "
            "it belongs to, how severe it looks, and whether anyone was hurt."
        ),
        "business_value": (
            "Simple claims go straight to fast-track settlement, while injury and major-loss claims "
            "reach senior adjusters on day one. That shortens cycle times and cuts leakage."
        ),
        "input_label": "Policyholder description",
        "fields": [
            ("line", "Line of business", "choice", "Which kind of insurance claim is this?",
             "auto: car, motorbike or vehicle accidents and damage\n"
             "property: home, building, contents, water or fire damage\n"
             "travel: trips, flights, lost luggage abroad\n"
             "health: medical treatment and hospital costs", 0.3),
            ("severity", "Severity", "score", "How severe is the loss?",
             "minor, cosmetic or small cost\nmoderate, repairs needed\nmajor or total loss", None),
            ("injury", "Injury reported", "noul", "Was anyone physically hurt?", "", 0.7),
        ],
        "examples": [
            ("Rear-ended", "Someone rear-ended me at a red light. My neck is sore and the bumper is "
                           "hanging off."),
            ("Burst pipe", "A pipe burst upstairs overnight and water came through the kitchen "
                           "ceiling. The floor and cabinets are soaked."),
            ("Lost luggage", "The airline lost my suitcase on the way to Lisbon and I had to buy "
                             "clothes for the week."),
            ("Scratch", "Small scratch on my car door from a shopping trolley."),
        ],
    },
    {
        "slug": "telecom-retention",
        "name": "Churn & Retention",
        "industry": "Telecom",
        "tagline": "Catch customers who are about to leave while there's still time to save them.",
        "description": (
            "Reads chats and emails from subscribers and estimates churn risk, the main reason "
            "for dissatisfaction, and whether they're explicitly asking to cancel."
        ),
        "business_value": (
            "At-risk customers go to the retention team with the reason already identified, so the "
            "right offer is made first time. Small gains in retention are worth millions a year "
            "at telecom scale."
        ),
        "input_label": "Subscriber message",
        "fields": [
            ("reason", "Main reason", "choice", "What is the subscriber mainly unhappy about?",
             "price: bills too high, price rises, cheaper elsewhere\n"
             "network: coverage, dropped calls, slow data\n"
             "service: poor support, long waits, unresolved complaints\n"
             "moving: relocating or no longer needs the service\n"
             "none: not unhappy, a routine question", 0.3),
            ("churn_risk", "Churn risk", "score", "How likely is this subscriber to leave?",
             "loyal\nat risk\nabout to leave", None),
            ("cancel", "Asks to cancel", "noul",
             "Does the subscriber ask to cancel, leave, or get a PAC / porting code?", "", 0.7),
        ],
        "examples": [
            ("Porting code", "Please send me my PAC code. I've found the same plan for half the price."),
            ("Dropped calls", "Calls keep dropping at home and I've complained twice already. "
                              "If this isn't fixed I'm switching."),
            ("Roaming", "Does my plan include roaming in Spain next month?"),
            ("Moving abroad", "I'm moving to Canada in June, how do I close my account?"),
        ],
    },
    {
        "slug": "comms-surveillance",
        "name": "Communications Surveillance",
        "industry": "Compliance",
        "tagline": "Screen advisor-client messages for conduct risk as they are sent.",
        "description": (
            "Checks outgoing messages from financial advisors for conduct red flags: promised "
            "returns, pressure tactics, and conversations moving to unmonitored channels."
        ),
        "business_value": (
            "Compliance teams review a short, ranked queue instead of random samples. Real "
            "breaches are caught before they become fines, and false positives drop sharply."
        ),
        "input_label": "Advisor message",
        "fields": [
            ("guarantee", "Promises returns", "noul",
             "Does the advisor promise the client a guaranteed profit or say an investment has "
             "no risk?", "", 0.7),
            ("off_channel", "Off-channel request", "noul",
             "Does the advisor mention WhatsApp, a personal phone number, or personal email?",
             "", 0.7),
            ("category", "Message type", "choice", "What kind of message is this?",
             "advice: investment recommendations or portfolio discussion\n"
             "admin: scheduling, paperwork, account servicing\n"
             "personal: social chat unrelated to business", 0.3),
            ("pressure", "Sales pressure", "score", "How much pressure does the message put on the client?",
             "none\nsome urgency\nhigh pressure, act now", None),
        ],
        "examples": [
            ("Guaranteed returns", "This fund is a sure thing: you'll double your money by year end, "
                                   "zero risk. Let's move fast before it closes."),
            ("Move to WhatsApp", "Easier if we chat on WhatsApp from now on, text my personal number."),
            ("Rebalance", "Following our review I'd suggest rebalancing 10% from equities into bonds. "
                          "Happy to discuss the risks on Thursday."),
            ("Paperwork", "Please sign the attached form so we can update your address on file."),
        ],
    },
]


def load(UseCase, Field, Example, reset=False):
    """Creates the demo use cases. With reset, existing ones with the same slug are replaced."""
    created = 0
    for order, data in enumerate(USE_CASES):
        existing = UseCase.objects.filter(slug=data["slug"])
        if existing.exists():
            if not reset:
                continue
            existing.delete()
        uc = UseCase.objects.create(
            order=order,
            **{k: v for k, v in data.items() if k not in ("fields", "examples")},
        )
        for i, (key, label, type_, instructions, options, min_conf) in enumerate(data["fields"]):
            Field.objects.create(
                use_case=uc, key=key, label=label, type=type_, instructions=instructions,
                options=options, min_confidence=min_conf, order=i,
            )
        for i, (title, text) in enumerate(data["examples"]):
            Example.objects.create(use_case=uc, title=title, text=text, order=i)
        created += 1
    return created
