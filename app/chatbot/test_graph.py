from app.chatbot.agent.rag import rag_graph
import asyncio



async def main():
    """Test the LLM response generation."""
    while True:
        user_input = input("Enter your query(press 'exit' or 'quit' to quit or exit the chat): ")
        if user_input.lower() in {"exit", "quit"}:
            print("Exiting chat.")
            break
        response = await rag_graph.ainvoke({"query": user_input})
        result = response['final_answer']
        print(f"LLM: {result}")


if __name__ == "__main__":
    asyncio.run(main())

# python -m app.chatbot.test_graph