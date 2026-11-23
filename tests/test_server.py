import pytest
from unittest.mock import patch

from server import (
    get_latest_price,
    search_stock,
    get_market_status,
    get_market_summary,
    get_top_gainers,
    get_top_losers,
    get_nepse_indices,
    get_stock_price_history,
    get_company_info,
    get_stock_market_depth,
    get_stock_trading_history,
    get_company_financial_reports,
    get_company_financial_summary,
    compare_quarterly_financials,
    get_company_news,
    market_status_resource,
    market_indices_resources,
    company_info_resource,
    analyze_company,
)

# --------------------------------------------------
# SHARED FIXTURE
# --------------------------------------------------


@pytest.fixture
def nepse_client():
    with patch("server.NepseClient") as mock_constructor:
        client = mock_constructor.return_value.__enter__.return_value
        yield client


@pytest.fixture
def stock_records():
    return [
        {
            "symbol": "NABIL",
            "securityName": "Nabil Bank Ltd.",
            "lastUpdatedPrice": 1500.0,
            "closePrice": 1495.0,
            "businessDate": "2026-11-13",
            "lastUpdatedTime": "15:00:00",
        },
        {
            "symbol": "ACLBSL",
            "securityName": "Aarambha Chautari Laghubitta",
            "lastUpdatedPrice": 850.0,
            "closePrice": 840.0,
            "businessDate": "2026-11-13",
            "lastUpdatedTime": "15:00:00",
        },
    ]


@pytest.fixture
def company_records():
    return [{"symbol": "NABIL", "id": 123, "securityName": "Nabil Bank Ltd."}]


# --------------------------------------------------
# HELPER FUNCTION TESTS
# --------------------------------------------------


def test_get_all_today_prices_single_page(nepse_client, stock_records):
    from server import get_all_today_prices

    nepse_client.today_price.return_value = {
        "content": stock_records,
        "totalPages": 1,
    }

    result = get_all_today_prices(nepse_client)

    assert result == stock_records
    nepse_client.today_price.assert_called_once_with(page=1, size=100)


def test_get_all_today_prices_multiple_pages(nepse_client, stock_records):
    from server import get_all_today_prices

    nepse_client.today_price.side_effect = [
        {"content": [stock_records[0]], "totalPages": 2},
        {"content": [stock_records[1]], "totalPages": 2},
    ]

    result = get_all_today_prices(nepse_client)

    assert len(result) == 2
    assert result == stock_records
    assert nepse_client.today_price.call_count == 2


# --------------------------------------------------
# STOCK TOOLS
# --------------------------------------------------


def test_get_latest_price_success(nepse_client, stock_records):
    nepse_client.today_price.return_value = {
        "content": stock_records,
        "totalPages": 1,
    }

    result = get_latest_price("nabil")

    assert result == {
        "symbol": "NABIL",
        "company": "Nabil Bank Ltd.",
        "last_price": 1500.0,
        "close_price": 1495.0,
        "business_date": "2026-11-13",
        "last_updated": "15:00:00",
    }


def test_get_latest_price_not_found(nepse_client):
    nepse_client.today_price.return_value = {
        "content": [],
        "totalPages": 1,
    }

    result = get_latest_price("UNKNOWN")

    assert result == "No stock found for symbol 'UNKNOWN'."


def test_search_stock_by_symbol(nepse_client, stock_records):
    nepse_client.today_price.return_value = {
        "content": stock_records,
        "totalPages": 1,
    }

    result = search_stock("nabil")

    assert result == [
        {
            "symbol": "NABIL",
            "company": "Nabil Bank Ltd.",
            "last_price": 1500.0,
        }
    ]


def test_search_stock_by_company_name(nepse_client, stock_records):
    nepse_client.today_price.return_value = {
        "content": stock_records,
        "totalPages": 1,
    }

    result = search_stock("aarambha")

    assert result[0]["symbol"] == "ACLBSL"


def test_search_stock_not_found(nepse_client):
    nepse_client.today_price.return_value = {
        "content": [],
        "totalPages": 1,
    }

    result = search_stock("unknown")

    assert result == "No stocks found matching 'unknown'."


# --------------------------------------------------
# MARKET TOOLS
# --------------------------------------------------


def test_market_status_success(nepse_client):
    nepse_client.market_status.return_value = {
        "isOpen": "CLOSE",
        "asOf": "2026-11-13T15:00:00",
    }

    result = get_market_status()

    assert result == "Status : CLOSE\nAs of : 2026-11-13T15:00:00"


def test_market_status_empty(nepse_client):
    nepse_client.market_status.return_value = None

    assert get_market_status() == "Nothing is found"


def test_market_status_missing_field(nepse_client):
    nepse_client.market_status.return_value = {"asOf": "2026-11-13"}

    assert get_market_status() == "Can not found market status"


def test_market_status_exception(nepse_client):
    nepse_client.market_status.side_effect = Exception("API unavailable")

    assert get_market_status() == "Unable to find status : API unavailable"


def test_market_summary_success(nepse_client):
    nepse_client.market_summary.return_value = [
        {"detail": "Total Turnover", "value": "500000000"},
        {"detail": "Total Transactions", "value": "10000"},
    ]

    result = get_market_summary()

    assert result == {
        "Total Turnover": "500000000",
        "Total Transactions": "10000",
    }


def test_market_summary_empty(nepse_client):
    nepse_client.market_summary.return_value = None

    assert get_market_summary() == "No market summary data is avaible"


def test_market_summary_exception(nepse_client):
    nepse_client.market_summary.side_effect = Exception("API unavailable")

    assert get_market_summary() == "Unable to find the summary : API unavailable"


# --------------------------------------------------
# GAINERS AND LOSERS
# --------------------------------------------------


@pytest.mark.parametrize(
    "function_name, api_method",
    [
        (get_top_gainers, "top_gainers"),
        (get_top_losers, "top_losers"),
    ],
)
def test_gainers_and_losers_success(nepse_client, function_name, api_method):
    record = {
        "symbol": "NABIL",
        "securityName": "Nabil Bank Ltd.",
        "ltp": 1500,
        "percentageChange": 2.5,
        "pointChange": 36,
    }

    getattr(nepse_client, api_method).return_value = [record]

    result = function_name()

    assert "NABIL" in result
    assert "Nabil Bank Ltd." in result
    assert "1500" in result


@pytest.mark.parametrize(
    "function_name, api_method, expected",
    [
        (get_top_gainers, "top_gainers", "No data is avaiable"),
        (get_top_losers, "top_losers", "No data is avaiable."),
    ],
)
def test_gainers_and_losers_empty(nepse_client, function_name, api_method, expected):
    getattr(nepse_client, api_method).return_value = None

    assert function_name() == expected


@pytest.mark.parametrize(
    "function_name, api_method",
    [
        (get_top_gainers, "top_gainers"),
        (get_top_losers, "top_losers"),
    ],
)
def test_gainers_and_losers_exception(nepse_client, function_name, api_method):
    getattr(nepse_client, api_method).side_effect = Exception("API unavailable")

    assert "API unavailable" in function_name()


def test_nepse_indices_success(nepse_client):
    nepse_client.nepse_indices.return_value = [
        {
            "index": "NEPSE",
            "close": 2600,
            "change": 10,
            "perChange": 0.4,
            "high": 2610,
            "low": 2590,
            "previousClose": 2590,
            "generatedTime": "15:00",
        }
    ]

    result = get_nepse_indices()

    assert "NEPSE" in result
    assert "2600" in result


def test_nepse_indices_empty(nepse_client):
    nepse_client.nepse_indices.return_value = []

    assert get_nepse_indices() == "No data is avaiable."


def test_nepse_indices_exception(nepse_client):
    nepse_client.nepse_indices.side_effect = Exception("API unavailable")

    assert "API unavailable" in get_nepse_indices()


# --------------------------------------------------
# COMPANY AND STOCK HISTORY TOOLS
# --------------------------------------------------


def test_stock_price_history_success(nepse_client, company_records):
    expected = [{"businessDate": "2026-11-13", "closePrice": 1500}]

    nepse_client.companies.return_value = company_records
    nepse_client.security_price_history.return_value = expected

    result = get_stock_price_history("nabil")

    assert result == expected
    nepse_client.security_price_history.assert_called_once_with(security_id=123)


def test_stock_price_history_company_not_found(nepse_client):
    nepse_client.companies.return_value = []

    assert get_stock_price_history("UNKNOWN") == "Unable to find the company"


def test_company_info_success(nepse_client, company_records):
    expected = {"security": {"securityName": "Nabil Bank Ltd."}}

    nepse_client.companies.return_value = company_records
    nepse_client.company_info.return_value = expected

    assert get_company_info("nabil") == expected


def test_company_info_not_found(nepse_client):
    nepse_client.companies.return_value = []

    assert get_company_info("UNKNOWN") == "Unable to find company: UNKNOWN"


def test_company_info_no_data(nepse_client, company_records):
    nepse_client.companies.return_value = company_records
    nepse_client.company_info.return_value = None

    assert get_company_info("NABIL") == ("No company information available for NABIL")


def test_market_depth_success(nepse_client, company_records):
    expected = {"buyQuantity": 100, "sellQuantity": 50}

    nepse_client.companies.return_value = company_records
    nepse_client.market_depth.return_value = expected

    assert get_stock_market_depth("NABIL") == expected


def test_market_depth_company_not_found(nepse_client):
    nepse_client.companies.return_value = []

    assert get_stock_market_depth("UNKNOWN") == ("Unable to find company: UNKNOWN")


def test_market_depth_no_data(nepse_client, company_records):
    nepse_client.companies.return_value = company_records
    nepse_client.market_depth.return_value = None

    assert get_stock_market_depth("NABIL") == (
        "No market depth data available for NABIL"
    )


def test_trading_history_success(nepse_client, company_records):
    expected = [{"contractId": 1, "quantity": 100}]

    nepse_client.companies.return_value = company_records
    nepse_client.stock_trading_history.return_value = expected

    result = get_stock_trading_history("NABIL", "2026-01-01", "2026-11-13")

    assert result == expected
    nepse_client.stock_trading_history.assert_called_once_with(
        security_id=123,
        page=1,
        size=20,
        start="2026-01-01",
        end="2026-11-13",
    )


def test_trading_history_company_not_found(nepse_client):
    nepse_client.companies.return_value = []

    result = get_stock_trading_history("UNKNOWN", "2026-01-01", "2026-11-13")

    assert result == "Unable to find company: UNKNOWN"


def test_trading_history_empty(nepse_client, company_records):
    nepse_client.companies.return_value = company_records
    nepse_client.stock_trading_history.return_value = None

    result = get_stock_trading_history("NABIL", "2026-01-01", "2026-11-13")

    assert result == ("No trading history available for NABIL in that date range.")


# --------------------------------------------------
# FINANCIAL TOOLS
# --------------------------------------------------


def test_financial_reports_success(nepse_client, company_records):
    expected = [{"fiscalReport": {"epsValue": 20}}]

    nepse_client.companies.return_value = company_records
    nepse_client.financial_reports.return_value = expected

    assert get_company_financial_reports("NABIL") == expected


def test_financial_reports_company_not_found(nepse_client):
    nepse_client.companies.return_value = []

    assert get_company_financial_reports("UNKNOWN") == (
        "Unable to find company: UNKNOWN"
    )


def test_financial_reports_empty(nepse_client, company_records):
    nepse_client.companies.return_value = company_records
    nepse_client.financial_reports.return_value = []

    assert get_company_financial_reports("NABIL") == (
        "No financial reports available for NABIL"
    )


def test_financial_summary_success(nepse_client, company_records):
    nepse_client.companies.return_value = company_records
    nepse_client.financial_reports.return_value = [
        {
            "fiscalReport": {
                "financialYear": {"fyName": "2082/83"},
                "quarterMaster": {"quarterName": "First Quarter"},
                "reportTypeMaster": {"reportName": "Quarterly Report"},
                "epsValue": 20,
                "peValue": 30,
                "profitAmount": 100000,
                "netWorthPerShare": 150,
                "paidUpCapital": 1000000,
            },
            "applicationDocumentDetailsList": [{"submittedDate": "2026-11-13"}],
        }
    ]

    result = get_company_financial_summary("NABIL")

    assert result["symbol"] == "NABIL"
    assert result["eps"] == 20
    assert result["pe_ratio"] == 30
    assert result["submitted_date"] == "2026-11-13"


def test_financial_summary_company_not_found(nepse_client):
    nepse_client.companies.return_value = []

    assert get_company_financial_summary("UNKNOWN") == {
        "error": "Company not found: UNKNOWN"
    }


def test_financial_summary_no_reports(nepse_client, company_records):
    nepse_client.companies.return_value = company_records
    nepse_client.financial_reports.return_value = []

    assert get_company_financial_summary("NABIL") == {
        "error": "No financial reports found for NABIL"
    }


def test_compare_quarterly_financials_success(nepse_client, company_records):
    nepse_client.companies.return_value = company_records
    nepse_client.financial_reports.return_value = [
        {
            "fiscalReport": {
                "reportTypeMaster": {"reportName": "Quarterly Report"},
                "quarterMaster": {"quarterName": "Second Quarter"},
                "financialYear": {"fyName": "2082/83"},
                "epsValue": 25,
                "profitAmount": 200000,
            }
        },
        {
            "fiscalReport": {
                "reportTypeMaster": {"reportName": "Quarterly Report"},
                "quarterMaster": {"quarterName": "First Quarter"},
                "financialYear": {"fyName": "2082/83"},
                "epsValue": 15,
                "profitAmount": 100000,
            }
        },
    ]

    result = compare_quarterly_financials("NABIL")

    assert result["symbol"] == "NABIL"
    assert len(result["quarterly_reports"]) == 2
    assert result["quarterly_reports"][0]["quarter"] == "First Quarter"
    assert result["quarterly_reports"][1]["quarter"] == "Second Quarter"


def test_compare_quarterly_company_not_found(nepse_client):
    nepse_client.companies.return_value = []

    assert compare_quarterly_financials("UNKNOWN") == {
        "error": "Company not found: UNKNOWN"
    }


# --------------------------------------------------
# COMPANY NEWS
# --------------------------------------------------


def test_company_news_success(nepse_client, company_records):
    nepse_client.companies.return_value = company_records
    nepse_client.security_company_news.return_value = [
        {
            "companyNews": {
                "newsHeadline": "Company announcement",
                "newsSource": "NEPSE",
                "newsType": "Announcement",
                "addedDate": "2026-11-13",
                "expiryDate": None,
                "newsBody": "Announcement details",
            },
            "applicationDocumentDetailsList": [
                {
                    "submittedDate": "2026-11-13",
                    "filePath": "document.pdf",
                }
            ],
        }
    ]

    result = get_company_news("NABIL")

    assert result["symbol"] == "NABIL"
    assert result["total_records"] == 1
    assert result["news"][0]["headline"] == "Company announcement"
    assert result["news"][0]["documents"][0]["file_path"] == "document.pdf"


def test_company_news_company_not_found(nepse_client):
    nepse_client.companies.return_value = []

    assert get_company_news("UNKNOWN") == {
        "symbol": "UNKNOWN",
        "error": "Company not found",
    }


def test_company_news_empty(nepse_client, company_records):
    nepse_client.companies.return_value = company_records
    nepse_client.security_company_news.return_value = None

    result = get_company_news("NABIL")

    assert result["total_records"] == 0
    assert result["news"] == []


# --------------------------------------------------
# MCP RESOURCES
# --------------------------------------------------


def test_market_status_resource(nepse_client):
    nepse_client.market_status.return_value = {
        "isOpen": "CLOSE",
        "asOf": "2026-11-13T15:00:00",
    }

    assert market_status_resource() == ("Status : CLOSE\nAs of : 2026-11-13T15:00:00")


def test_market_status_resource_empty(nepse_client):
    nepse_client.market_status.return_value = None

    assert market_status_resource() == "Nothing is found"


def test_market_indices_resource(nepse_client):
    nepse_client.nepse_indices.return_value = [
        {
            "index": "NEPSE",
            "close": 2600,
            "change": 10,
            "perChange": 0.4,
            "high": 2610,
            "low": 2590,
            "previousClose": 2590,
            "generatedTime": "15:00",
        }
    ]

    result = market_indices_resources()

    assert "NEPSE" in result
    assert "2600" in result


def test_market_indices_resource_empty(nepse_client):
    nepse_client.nepse_indices.return_value = []

    assert market_indices_resources() == "No data is avaiable."


def test_company_info_resource_success(nepse_client, company_records):
    nepse_client.companies.return_value = company_records
    nepse_client.company_info.return_value = {
        "security": {
            "securityName": "Nabil Bank Ltd.",
            "symbol": "NABIL",
            "listingDate": "1986-01-01",
            "companyId": {"sectorMaster": {"sectorDescription": "Commercial Bank"}},
        },
        "securityDailyTradeDto": {
            "closePrice": 1500,
            "previousClose": 1495,
            "highPrice": 1510,
            "lowPrice": 1490,
        },
    }

    result = company_info_resource("nabil")

    assert "Nabil Bank Ltd." in result
    assert "NABIL" in result
    assert "Commercial Bank" in result


def test_company_info_resource_company_not_found(nepse_client):
    nepse_client.companies.return_value = []

    assert company_info_resource("UNKNOWN") == ("Unable to find company: UNKNOWN")


# --------------------------------------------------
# MCP PROMPT
# --------------------------------------------------


def test_analyze_company_prompt():
    result = analyze_company("NABIL")

    assert "NABIL" in result
    assert "get_company_financial_reports" in result
    assert "get_company_financial_summary" in result
    assert "nepse://company/NABIL" in result
    assert "Do not invent financial figures" in result
