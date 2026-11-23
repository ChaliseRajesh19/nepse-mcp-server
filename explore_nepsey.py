from nepsepy import NepseClient
import json

with NepseClient() as client:
    companies = client.companies()

    symbol = "NABIL"
    company = next(
        (c for c in companies if c.get("symbol", "").upper() == symbol), None
    )

    if company:
        reports = client.financial_reports(security_id=company["id"])

        print(json.dumps(reports[:5], indent=4, default=str))
    else:
        print(f"Company not found: {symbol}")
