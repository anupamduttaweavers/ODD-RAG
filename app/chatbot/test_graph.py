"""Interactive CLI test for the agentic RAG graph."""

import asyncio

from app.chatbot.agent.rag import get_rag_graph


async def main():
    graph = await get_rag_graph()
    thread_id = "test-cli"

    while True:
        user_input = input("Enter your query (press 'exit' or 'quit' to quit): ")
        if user_input.lower() in {"exit", "quit"}:
            print("Exiting chat.")
            break

        config = {"configurable": {"thread_id": thread_id}}
        response = await graph.ainvoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
        )

        for msg in reversed(response.get("messages", [])):
            if hasattr(msg, "content") and not getattr(msg, "tool_calls", None):
                print(f"LLM: {msg.content}")
                break


if __name__ == "__main__":
    asyncio.run(main())

# python -m app.chatbot.test_graph
