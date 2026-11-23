import asyncio

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pathlib import Path
from datetime import datetime, timedelta, timezone
import jwt
import httpx2

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

PRIVATE_KEY_PATH = BASE_DIR / "jwt_private.pem"

JWT_ISSUER = "mero-invest-auth"
JWT_AUDIENCE = "nepse-mcp-server"
JWT_ALGORITHM = "RS256"


def create_access_token():
    private_key = PRIVATE_KEY_PATH.read_text(encoding="utf-8")

    now = datetime.now(timezone.utc)

    payload = {
        "sub": "mero-invest-api",
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }

    return jwt.encode(
        payload,
        private_key,
        algorithm=JWT_ALGORITHM,
    )


async def main():
    access_token = create_access_token()
    async with (
        httpx2.AsyncClient(
            headers={"Authorization": f"Bearer {access_token}"}
        ) as http_client,
        streamable_http_client(
            "https://nepse-mcp-server.onrender.com/mcp",
            http_client=http_client,
        ) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()

        print("Connected to NEPSE MCP server!")

        tools_result = await session.list_tools()

        print("\nAvailable tools:")
        for tool in tools_result.tools:
            print(f"- {tool.name}")

        print("\nCalling get_market_status...")

        call_result = await session.call_tool(
            "get_market_status",
            {},
        )

        print("\nTool response:")

        if call_result.is_error:
            print("Tool execution failed.")
        else:
            for item in call_result.content:
                if hasattr(item, "text"):
                    print(item.text)


if __name__ == "__main__":
    asyncio.run(main())
