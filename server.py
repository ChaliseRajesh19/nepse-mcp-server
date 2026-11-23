from fastmcp import FastMCP
from nepsepy import NepseClient
import traceback
import argparse
import os
from dotenv import load_dotenv
from pathlib import Path
from fastmcp.server.auth.providers.jwt import JWTVerifier

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

JWT_ISSUER = "mero-invest-auth"
JWT_AUDIENCE = "nepse-mcp-server"
JWT_ALGORITHM = "RS256"

PUBLIC_KEY_PATH = Path(
    os.getenv(
        "MCP_JWT_PUBLIC_KEY_PATH",
        str(BASE_DIR / "jwt_public.pem"),
    )
)

auth = None

if PUBLIC_KEY_PATH.exists():
    public_key = PUBLIC_KEY_PATH.read_text(encoding="utf-8")

    auth = JWTVerifier(
        public_key=public_key,
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        algorithm=JWT_ALGORITHM,
    )

mcp = FastMCP(
    "Nepse Data Server",
    auth=auth,
)


def get_stock_price(symbol: str) -> dict | None:
    """Get the latest price for a given stock symbol."""
    symbol = symbol.strip().upper()
    with NepseClient() as client:
        prices = client.today_price()

        for record in prices["content"]:
            if record["symbol"] == symbol:
                return {
                    "symbol": record["symbol"],
                    "securityName": record["securityName"],
                    "lastUpdatedPrice": record["lastUpdatedPrice"],
                    "closePrice": record["closePrice"],
                    "businessDate": record["businessDate"],
                    "lastUpdatedTime": record["lastUpdatedTime"],
                }
        return None


def search_stock_helper(query: str) -> list:
    """Search for stock symbols based on a query string."""
    query = query.lower()
    with NepseClient() as client:
        prices = client.today_price()
        matching_stocks = []

        for record in prices["content"]:
            if (
                query in record["symbol"].lower()
                or query in record["securityName"].lower()
            ):
                matching_stocks.append(
                    {"symbol": record["symbol"], "securityName": record["securityName"]}
                )

        return matching_stocks


def get_all_today_prices(client):
    first_page = client.today_price(page=1, size=100)

    stocks = first_page.get("content", [])
    total_pages = first_page.get("totalPages", 1)

    for page in range(2, total_pages + 1):
        response = client.today_price(page=page, size=100)

        stocks.extend(response.get("content", []))

    return stocks


@mcp.tool()
def get_latest_price(symbol: str):
    """Get the latest trading price for an exact NEPSE stock symbol."""

    symbol = symbol.strip().upper()

    with NepseClient() as client:
        stocks = get_all_today_prices(client)

    for stock in stocks:
        if stock["symbol"].upper() == symbol:
            return {
                "symbol": stock["symbol"],
                "company": stock["securityName"],
                "last_price": stock["lastUpdatedPrice"],
                "close_price": stock["closePrice"],
                "business_date": stock["businessDate"],
                "last_updated": stock["lastUpdatedTime"],
            }

    return f"No stock found for symbol '{symbol}'."


@mcp.tool()
def search_stock(query: str):
    """Search NEPSE stocks by company name or trading symbol."""

    query = query.strip().lower()

    with NepseClient() as client:
        stocks = get_all_today_prices(client)

    matches = []

    for stock in stocks:
        symbol = stock["symbol"].lower()
        company = stock["securityName"].lower()

        if query in symbol or query in company:
            matches.append(
                {
                    "symbol": stock["symbol"],
                    "company": stock["securityName"],
                    "last_price": stock["lastUpdatedPrice"],
                }
            )

    if not matches:
        return f"No stocks found matching '{query}'."

    return matches


@mcp.tool()
def get_market_status():
    try:
        with NepseClient() as client:
            result = client.market_status()
            if result is None:
                return "Nothing is found"

            if "isOpen" not in result:
                return "Can not found market status"

            return f"Status : {result['isOpen']}\n" f"As of : {result['asOf']}"
    except Exception as exc:
        return f"Unable to find status : {exc}"


@mcp.tool()
def get_market_summary():
    summary = {}
    try:
        with NepseClient() as client:
            result = client.market_summary()
            if result is None:
                return "No market summary data is avaible"

            for record in result:
                title = record["detail"]
                value = record["value"]
                summary[title] = value

            return summary
    except Exception as exc:
        return f"Unable to find the summary : {exc}"


@mcp.tool()
def get_top_gainers():
    """search for top gainers of the market"""
    try:
        with NepseClient() as client:
            result = client.top_gainers()
            if result is None:
                return "No data is avaiable"
            return "\n".join(
                f"Symbol : {record['symbol']} Company_Name : {record["securityName"]} LTP : {record['ltp']} Percentage_Change : {record['percentageChange']} PointChange : {record['pointChange']}"
                for record in result
            )

    except Exception as exc:
        return f"Unable to find the result : {exc}"


@mcp.tool()
def get_top_losers():
    """search for top losers of the market"""
    try:
        with NepseClient() as client:
            result = client.top_losers()
            if result is None:
                return "No data is avaiable."
            return "\n".join(
                f"Symbol : {record['symbol']} Company_Name : {record["securityName"]} LTP : {record['ltp']} Percentage_Change : {record['percentageChange']} PointChange : {record['pointChange']}"
                for record in result
            )

    except Exception as exc:
        return f"Unable to find the result : {exc}"


@mcp.tool()
def get_nepse_indices():
    """provide the nepse indices"""
    indices_summary = []
    try:
        with NepseClient() as client:
            result = client.nepse_indices()
            if not result:
                return "No data is avaiable."
            for record in result:
                indices_summary.append(f"""
                    Index: {record['index']}
                    Close: {record['close']}
                    Change: {record['change']}
                    Percentage Change: {record['perChange']}%
                    Day High: {record['high']}
                    Day Low: {record['low']}
                    Previous Close: {record['previousClose']}
                    Generated Time: {record['generatedTime']}
                    """)
            return "\n".join(indices_summary)
    except Exception as exc:
        return f"Unable to return the indices:{exc}"


@mcp.tool()
def get_stock_price_history(symbol: str):
    try:
        with NepseClient() as client:
            companies = client.companies()
            symbol = symbol.strip().upper()
            company_id = None
            for company in companies:
                if company["symbol"] == symbol:
                    company_id = company["id"]
                    break
            if company_id is None:
                return "Unable to find the company"

            result = client.security_price_history(security_id=company_id)
            return result

    except Exception as exc:
        return f"Unable to return the price history: {exc}"


@mcp.tool()
def get_company_info(symbol: str):
    """Get company details and daily trading information for a NEPSE-listed company."""
    try:
        with NepseClient() as client:
            companies = client.companies()
            symbol = symbol.strip().upper()
            company_id = None

            for company in companies:
                if company["symbol"].upper() == symbol:
                    company_id = company["id"]
                    break

            if company_id is None:
                return f"Unable to find company: {symbol}"

            result = client.company_info(security_id=company_id)

            if not result:
                return f"No company information available for {symbol}"

            return result

    except Exception as exc:
        return f"Unable to return company information: {exc}"


@mcp.tool()
def get_stock_market_depth(symbol: str):
    """Get the market order book and buy/sell quantities for a NEPSE stock."""
    try:
        with NepseClient() as client:
            companies = client.companies()
            symbol = symbol.strip().upper()
            company_id = None

            for company in companies:
                if company["symbol"].upper() == symbol:
                    company_id = company["id"]
                    break

            if company_id is None:
                return f"Unable to find company: {symbol}"

            result = client.market_depth(security_id=company_id)

            if not result:
                return f"No market depth data available for {symbol}"

            return result

    except Exception as exc:
        traceback.print_exc()
        return f"Unable to return market depth: {exc}"


@mcp.tool()
def get_stock_trading_history(
    symbol: str, start: str, end: str, page: int = 1, size: int = 20
):
    """Get a stock's trading history within a specified date range."""
    try:
        with NepseClient() as client:
            companies = client.companies()
            symbol = symbol.strip().upper()
            company_id = None

            for company in companies:
                if company.get("symbol") and company["symbol"].upper() == symbol:
                    company_id = company["id"]
                    break

            if company_id is None:
                return f"Unable to find company: {symbol}"

            result = client.stock_trading_history(
                security_id=company_id, page=page, size=size, start=start, end=end
            )

            if not result:
                return f"No trading history available for {symbol} in that date range."

            return result

    except Exception as exc:
        return f"Unable to return stock trading history: {exc}"


@mcp.tool()
def get_company_financial_reports(symbol: str):
    """Get financial reports and available report metadata for a NEPSE-listed company."""
    try:
        with NepseClient() as client:
            companies = client.companies()
            symbol = symbol.strip().upper()
            company_id = None

            for company in companies:
                if company.get("symbol") and company["symbol"].upper() == symbol:
                    company_id = company["id"]
                    break

            if company_id is None:
                return f"Unable to find company: {symbol}"

            result = client.financial_reports(security_id=company_id)

            if not result:
                return f"No financial reports available for {symbol}"

            return result

    except Exception as exc:
        return f"Unable to return financial reports: {exc}"


@mcp.tool()
def get_company_financial_summary(symbol: str) -> dict:
    """Return key financial metrics from the latest available company report."""
    try:
        with NepseClient() as client:
            companies = client.companies()
            symbol = symbol.strip().upper()

            company_id = None
            for company in companies:
                if company.get("symbol", "").upper() == symbol:
                    company_id = company["id"]
                    break

            if company_id is None:
                return {"error": f"Company not found: {symbol}"}

            reports = client.financial_reports(security_id=company_id)

            if not reports:
                return {"error": f"No financial reports found for {symbol}"}

            latest_report = reports[0]
            financial = latest_report.get("fiscalReport") or {}
            fiscal_year = financial.get("financialYear") or {}
            quarter = financial.get("quarterMaster") or {}
            report_type = financial.get("reportTypeMaster") or {}
            documents = latest_report.get("applicationDocumentDetailsList") or []
            submitted_date = documents[0].get("submittedDate") if documents else None

            return {
                "symbol": symbol,
                "financial_year": fiscal_year.get("fyName"),
                "quarter": quarter.get("quarterName"),
                "report_type": report_type.get("reportName"),
                "eps": financial.get("epsValue"),
                "pe_ratio": financial.get("peValue"),
                "profit_amount": financial.get("profitAmount"),
                "net_worth_per_share": financial.get("netWorthPerShare"),
                "paid_up_capital": financial.get("paidUpCapital"),
                "submitted_date": submitted_date,
            }

    except Exception as exc:
        return {"error": f"Unable to fetch financial summary: {exc}"}


@mcp.tool()
def compare_quarterly_financials(symbol: str) -> dict:
    """Compare quarterly EPS and profit across available financial reports."""
    try:
        with NepseClient() as client:
            companies = client.companies()
            symbol = symbol.strip().upper()

            company = next(
                (
                    item
                    for item in companies
                    if item.get("symbol", "").upper() == symbol
                ),
                None,
            )

            if company is None:
                return {"error": f"Company not found: {symbol}"}

            reports = client.financial_reports(security_id=company["id"])

            quarter_order = {
                "First Quarter": 1,
                "Second Quarter": 2,
                "Third Quarter": 3,
                "Fourth Quarter": 4,
            }

            quarterly_reports = []

            for report in reports:
                financial = report.get("fiscalReport") or {}
                report_type = (financial.get("reportTypeMaster") or {}).get(
                    "reportName"
                )
                quarter = (financial.get("quarterMaster") or {}).get("quarterName")
                year = (financial.get("financialYear") or {}).get("fyName")

                if report_type != "Quarterly Report":
                    continue

                if quarter not in quarter_order or not year:
                    continue

                quarterly_reports.append(
                    {
                        "financial_year": year,
                        "quarter": quarter,
                        "quarter_number": quarter_order[quarter],
                        "eps": financial.get("epsValue"),
                        "profit": financial.get("profitAmount"),
                    }
                )

            quarterly_reports.sort(
                key=lambda item: (
                    item["financial_year"],
                    item["quarter_number"],
                )
            )

            return {
                "symbol": symbol,
                "quarterly_reports": quarterly_reports,
            }

    except Exception as exc:
        return {"error": f"Unable to compare quarterly financials: {exc}"}


@mcp.tool()
def get_company_news(symbol: str) -> dict:
    """Get company announcements and available document metadata for a NEPSE-listed security."""

    symbol = symbol.strip().upper()

    with NepseClient() as client:
        companies = client.companies()

        company = next(
            (item for item in companies if item.get("symbol", "").upper() == symbol),
            None,
        )

        if company is None:
            return {
                "symbol": symbol,
                "error": "Company not found",
            }

        records = client.security_company_news(security_id=company["id"])

    news_items = []

    for record in records or []:
        news = record.get("companyNews") or {}

        documents = [
            {
                "submitted_date": document.get("submittedDate"),
                "file_path": document.get("filePath"),
            }
            for document in (record.get("applicationDocumentDetailsList") or [])
        ]

        news_items.append(
            {
                "headline": news.get("newsHeadline"),
                "source": news.get("newsSource"),
                "type": news.get("newsType"),
                "added_date": news.get("addedDate"),
                "expiry_date": news.get("expiryDate"),
                "body": news.get("newsBody"),
                "documents": documents,
            }
        )

    return {
        "symbol": symbol,
        "company_name": company.get("securityName"),
        "total_records": len(news_items),
        "news": news_items,
    }


@mcp.resource("nepse://market/status")
def market_status_resource():
    try:
        with NepseClient() as client:
            result = client.market_status()
            if result is None:
                return "Nothing is found"

            if "isOpen" not in result:
                return "Can not found market status"

            return f"Status : {result['isOpen']}\n" f"As of : {result['asOf']}"
    except Exception as exc:
        return f"Unable to find status : {exc}"


@mcp.resource("nepse://market/indices")
def market_indices_resources():
    indices_summary = []
    try:
        with NepseClient() as client:
            result = client.nepse_indices()
            if not result:
                return "No data is avaiable."
            for record in result:
                indices_summary.append(f"""
                    Index: {record['index']}
                    Close: {record['close']}
                    Change: {record['change']}
                    Percentage Change: {record['perChange']}%
                    Day High: {record['high']}
                    Day Low: {record['low']}
                    Previous Close: {record['previousClose']}
                    Generated Time: {record['generatedTime']}
                    """)
            return "\n".join(indices_summary)
    except Exception as exc:
        return f"Unable to return the indices:{exc}"


@mcp.resource("nepse://company/{symbol}")
def company_info_resource(symbol: str):
    try:
        with NepseClient() as client:
            companies = client.companies()
            symbol = symbol.strip().upper()
            company_id = None

            for company in companies:
                if company.get("symbol") and company["symbol"].upper() == symbol:
                    company_id = company["id"]
                    break

            if company_id is None:
                return f"Unable to find company: {symbol}"

            result = client.company_info(security_id=company_id)

            if not result:
                return f"No company information available for {symbol}"

            security = result.get("security") or {}
            daily_trade = result.get("securityDailyTradeDto") or {}

            company_details = security.get("companyId") or {}
            sector_details = company_details.get("sectorMaster") or {}

            security_name = security.get("securityName") or "Unknown"
            company_symbol = security.get("symbol") or symbol
            listing_date = security.get("listingDate") or "N/A"

            sector_description = sector_details.get("sectorDescription") or "Unknown"

            close_price = daily_trade.get("closePrice")
            previous_close = daily_trade.get("previousClose")
            day_high = daily_trade.get("highPrice")
            day_low = daily_trade.get("lowPrice")

            close_price = close_price if close_price is not None else "N/A"
            previous_close = previous_close if previous_close is not None else "N/A"
            day_high = day_high if day_high is not None else "N/A"
            day_low = day_low if day_low is not None else "N/A"

            return f"""
Company: {security_name}
Symbol: {company_symbol}
Sector: {sector_description}
Listing Date: {listing_date}

Closing Price: {close_price}
Previous Close: {previous_close}
Day High: {day_high}
Day Low: {day_low}
"""

    except Exception as exc:
        return f"Unable to return company information: {exc}"


@mcp.prompt()
def analyze_company(symbol: str) -> str:
    """Guide analysis of a NEPSE-listed company using available MCP data sources."""
    return f"""
    Analyze the NEPSE-listed company with symbol {symbol}.

    Available data sources:

    1. Tool: get_company_financial_reports(symbol: str)
       Description: Retrieves the company's available financial reports
       and report metadata.

    2. Tool: get_company_financial_summary(symbol: str)
       Description: Retrieves selected financial metrics, including EPS,
       P/E ratio, profit, net worth per share, and paid-up capital.

    3. Resource: nepse://company/{symbol}
       Description: Provides company identity, sector, listing date,
       and selected trading details such as closing price, daily high,
       daily low, and previous close.

    Instructions:
    - Use the available tools and resource to gather relevant information.
    - Explain the company's financial position using the retrieved data.
    - Separate reported facts from interpretation.
    - Identify missing or outdated information.
    - Do not invent financial figures or make unsupported buy/sell claims.
    """


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NEPSE MCP Server")

    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default=os.getenv("MCP_TRANSPORT", "stdio"),
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", "127.0.0.1"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", os.getenv("PORT", "8000"))),
    )

    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run()
    else:
        if auth is None:
            raise RuntimeError("jwt_public.pem is required for HTTP transport.")

        mcp.run(
            transport="http",
            host=args.host,
            port=args.port,
        )
