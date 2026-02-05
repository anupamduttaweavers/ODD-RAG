import faiss
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores.utils import DistanceStrategy
from app.chatbot.agent.llm import embeddings
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_new_vectorstore() -> FAISS:
    """Create a fresh in-memory FAISS vector store."""
    # index = faiss.IndexFlatL2(settings.DINMS) #->This is for the L2 distance matric
    index = faiss.IndexFlatIP(settings.DINMS)  # ->This is for the inner product matric(cosine similarity)
    
    return FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
        normalize_L2=True,# Add this line to normalize vectors for cosine similarity
        distance_strategy=DistanceStrategy.COSINE,
    )


def load_vectorstore() -> FAISS:
    """Load vector store from disk if exists, otherwise create new."""
    if settings.VECTORSTORE_PATH.exists():
        try:
            logger.info("Loading existing vector store ")
            return FAISS.load_local(
                str(settings.VECTORSTORE_PATH),
                embeddings,
                allow_dangerous_deserialization=True  # Required for pickle
            )
        except Exception as e:
            logger.warning(f"Failed to load vector store: {e}. Creating new one.")
            return create_new_vectorstore()
    else:
        logger.info("No existing vector store found. Creating new one.")
        return create_new_vectorstore()


def save_vectorstore(vs: FAISS = None) -> None:
    """Save vector store to disk."""
    if vs is None:
        vs = vector_store
    try:
        settings.VECTORSTORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        vs.save_local(str(settings.VECTORSTORE_PATH))
        logger.info(f"Vector store saved.with {vs.index.ntotal} chunks.")
    except Exception as e:
        logger.error(f"Failed to save vector store: {e}")


# Load or create the vector store on module import
vector_store = load_vectorstore()

# Create a retriever from the vector store
retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 5})




