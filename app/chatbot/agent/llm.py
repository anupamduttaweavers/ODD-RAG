from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain.messages import HumanMessage
from app.core.config import settings

# Initialize the LLaMA2 model via LangChain Ollama
model = ChatOllama(model=settings.LLM_MODEL_NAME, base_url=settings.LLM_BASE_URL)
# Initialize the embeddings model
embeddings = OllamaEmbeddings(model=settings.EMBEDDING_MODEL,base_url=settings.LLM_BASE_URL)

def generate_response(prompt: str) -> str:
    """Generate a response from the LLaMA2 model using LangChain Ollama."""
    message = HumanMessage(content=prompt)
    response = model.invoke([message])
    return response.content

