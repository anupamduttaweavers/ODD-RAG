from app.chatbot.agent.llm import generate_response,embeddings




def main():
    """Test the LLM response generation."""
    while True:
        user_input = input("Enter your query(press 'exit' or 'quit' to quit or exit the chat): ")
        if user_input.lower() in {"exit", "quit"}:
            print("Exiting chat.")
            break
        response = generate_response(user_input)
        print(f"LLM: {response}")


def test_embeddings():
    """Test the embeddings generation."""
    sample_text = "This is a sample text for embedding."
    embedding_vector = embeddings.embed_query(sample_text)
    print(f"Embedding vector for sample text: {embedding_vector[:10]},total dims: {len(embedding_vector)}")




if __name__ == "__main__":
    main() #-->This is to test the llm response generation
    # test_embeddings() #-->This is to test the embeddings generation

# Run this command to test the LLM response generation:(check the function which you want to test in the __main__ block)
# python -m app.chatbot.test_llm