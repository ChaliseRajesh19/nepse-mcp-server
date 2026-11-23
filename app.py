import asyncio
import streamlit as st

from client import (
    connect_to_mcp,
    discover_capabilities,
    prepare_tools_for_llm,
    chat_with_mcp,
)

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="NEPSE AI Assistant",
    page_icon="📈",
    layout="centered",
)

st.title("📈 NEPSE AI Assistant")
st.caption("Your AI assistant for Nepal's stock market.")


# --------------------------------------------------
# MCP CONNECTION AND AI RESPONSE
# --------------------------------------------------


async def ask_nepse_assistant(user_query: str, on_tool_event=None) -> str:

    async with connect_to_mcp() as session:

        capabilities = await discover_capabilities(session)

        llm_tools = prepare_tools_for_llm(capabilities)

        response = await chat_with_mcp(
            session,
            llm_tools,
            user_query,
            on_tool_event=on_tool_event,
        )

        if response is None:
            raise RuntimeError("The assistant could not generate a response.")

        return response


def get_assistant_response(user_query: str, on_tool_event=None) -> str:

    return asyncio.run(
        ask_nepse_assistant(
            user_query,
            on_tool_event=on_tool_event,
        )
    )


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    st.header("📈 NEPSE AI")

    st.write(
        "Ask questions about NEPSE stocks, market activity, "
        "company information, and financial reports."
    )

    if st.button("Clear chat", use_container_width=True):

        st.session_state.messages = []
        st.rerun()


# --------------------------------------------------
# DISPLAY CHAT HISTORY
# --------------------------------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --------------------------------------------------
# CHAT INPUT
# --------------------------------------------------

user_query = st.chat_input("Ask something about NEPSE...")


if user_query:

    # Display user message
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_query,
        }
    )

    with st.chat_message("user"):
        st.markdown(user_query)

    # Generate assistant response
    with st.chat_message("assistant"):

        try:

            with st.status(
                "Processing your request...",
                expanded=True,
            ) as status:

                # Display MCP tool execution events

                def show_tool_event(event):

                    tool_name = event["tool"]
                    tool_status = event["status"]

                    if tool_status == "running":

                        with status.expander(
                            f"🔧 {tool_name} — Running",
                            expanded=True,
                        ):
                            st.write("Input arguments:")
                            st.json(event.get("arguments", {}))

                    elif tool_status == "success":

                        with status.expander(
                            f"✅ {tool_name} — Completed",
                            expanded=False,
                        ):
                            st.write("Returned data:")
                            st.code(
                                event.get(
                                    "result",
                                    "No result available",
                                ),
                                language="text",
                            )

                    elif tool_status == "failed":

                        with status.expander(
                            f"❌ {tool_name} — Failed",
                            expanded=True,
                        ):
                            st.error(event.get("result", "Unknown error"))

                assistant_response = get_assistant_response(
                    user_query,
                    on_tool_event=show_tool_event,
                )

                status.update(
                    label="Request completed",
                    state="complete",
                    expanded=False,
                )

            # Display final AI response
            st.markdown(assistant_response)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": assistant_response,
                }
            )

        except Exception as exc:

            error_message = f"Something went wrong: {exc}"

            st.error(error_message)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_message,
                }
            )
