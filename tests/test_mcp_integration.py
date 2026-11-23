import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"


def test_mcp_server_integration():
    async def run_test():
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(SERVER_PATH)],
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 1. Initialize MCP connection
                initialization = await session.initialize()
                assert initialization is not None

                # 2. Discover tools
                tools_result = await session.list_tools()
                tool_names = {tool.name for tool in tools_result.tools}

                expected_tools = {
                    "get_latest_price",
                    "search_stock",
                    "get_market_status",
                    "get_market_summary",
                    "get_top_gainers",
                    "get_top_losers",
                    "get_nepse_indices",
                    "get_stock_price_history",
                    "get_company_info",
                    "get_stock_market_depth",
                    "get_stock_trading_history",
                    "get_company_financial_reports",
                    "get_company_financial_summary",
                    "compare_quarterly_financials",
                    "get_company_news",
                }

                assert expected_tools.issubset(
                    tool_names
                ), f"Missing tools: {expected_tools - tool_names}"

                # 3. Discover resources
                resources_result = await session.list_resources()
                resource_uris = {
                    str(resource.uri) for resource in resources_result.resources
                }

                assert "nepse://market/status" in resource_uris
                assert "nepse://market/indices" in resource_uris

                # 4. Discover resource templates
                templates_result = await session.list_resource_templates()

                template_uris = {
                    template.uriTemplate
                    for template in templates_result.resourceTemplates
                }

                assert "nepse://company/{symbol}" in template_uris

                # 5. Discover prompts
                prompts_result = await session.list_prompts()
                prompt_names = {prompt.name for prompt in prompts_result.prompts}

                assert "analyze_company" in prompt_names

                # 6. Retrieve company-analysis prompt
                prompt_result = await session.get_prompt(
                    "analyze_company",
                    {"symbol": "ACLBSL"},
                )

                assert prompt_result.messages
                assert any(
                    message.content is not None for message in prompt_result.messages
                )

                print("MCP integration test passed.")
                print(f"Discovered tools: {len(tool_names)}")
                print(f"Discovered resources: {len(resource_uris)}")
                print(f"Discovered templates: {len(template_uris)}")
                print(f"Discovered prompts: {len(prompt_names)}")

    asyncio.run(run_test())
