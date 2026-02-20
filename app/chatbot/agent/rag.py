import logging
from typing import TypedDict
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain.messages import SystemMessage, HumanMessage
from langchain_core.documents import Document
from typing_extensions import Annotated
from app.chatbot.config.prompts import get_prompt
from app.chatbot.agent.llm import model
from app.vectorstore.operations import retrieve_similar
from app.admin.runtime_config import rc

logger = logging.getLogger(__name__)

class RAGState(TypedDict):
    query: str
    retrieved_docs: list[Document]
    query_generated: str
    final_answer: str


graph_builder = StateGraph(RAGState)


async def choose_paths(state: RAGState) -> bool:
    """Decide on the paths to take based on the user's query."""
    system_prompt = SystemMessage(content=get_prompt("flow_decision"))
    user_message = HumanMessage(content=state["query"])
    response = await model.ainvoke([system_prompt, user_message])
    if "yes" in response.content.lower():
        intention = "greeting"
    else:
        intention = "query"
    logger.info(f"Flow decision: {intention}")
    return True if intention == "greeting" else False


async def greeting(state: RAGState) -> RAGState:
    """Handle greeting intentions."""
    system_prompt = SystemMessage(content=get_prompt("greeting"))
    user_message = HumanMessage(content=state["query"])
    response = await model.ainvoke([system_prompt, user_message])
    state["final_answer"] = response.content
    logger.info(f"Greeting Response: {response.content}")
    return state

async def retrieve_intentions(state: RAGState) -> RAGState:
    """Retrieve user intentions based on the user's query."""
    system_message = SystemMessage(content=get_prompt("query_generator"))
    user_message = HumanMessage(content=state["query"])

    response = await model.ainvoke([system_message, user_message])
    logger.info(f"Generated Query: {response.content}")
    state["query_generated"] = response.content
    return state


async def retrieve_documents(state: RAGState) -> RAGState:
    """Retrieve relevant documents based on the user's query."""
    query = state.get("query_generated") or state["query"]

    k = rc.get_int("rag_retrieval_k", 20)
    docs = await retrieve_similar(query, k=k)
    logger.info(f"Retrieved {len(docs)} documents (k={k}).")
    state["retrieved_docs"] = docs
    return state


async def generate_answer(state: RAGState) -> RAGState:
    """Generate an answer based on the user's query and retrieved documents."""
    system_message = SystemMessage(content=get_prompt("answer_format"))
    context = "\n".join(
        [
            (
                f"[Doc {i}]\n"
                f"Content:\n{doc.page_content}\n"
                f"Source:\n"
                f"  file_name: {doc.metadata.get('file_name', 'n/a')}\n"
                f"  page_number: {doc.metadata.get('page_number', 'n/a')}"
            )
            for i, doc in enumerate(state["retrieved_docs"], 1)
        ]
    )
    documents_message = SystemMessage(
        content=f"Use the following documents content and source as reference to generate an final answer:\n{context}"
    )
    user_message = HumanMessage(content=state["query"])
    response = await model.ainvoke([system_message, documents_message, user_message])
    logger.info(f"Generated Answer: {response.content}")
    state["final_answer"] = response.content
    return state


# Adding the nodes to the graph
graph_builder.add_node("retrieve_intentions", retrieve_intentions)
graph_builder.add_node("retrieve_documents", retrieve_documents)
graph_builder.add_node("generate_answer", generate_answer)
graph_builder.add_node("greeting", greeting)
# graph_builder.add_node("choose_paths", choose_paths)

# Adding edges to define the flow
graph_builder.add_conditional_edges(START, choose_paths, {True: "greeting", False: "retrieve_intentions"})
# graph_builder.add_edge(START, "retrieve_intentions")
graph_builder.add_edge("retrieve_intentions", "retrieve_documents")
graph_builder.add_edge("retrieve_documents", "generate_answer")
graph_builder.add_edge("generate_answer", END)
graph_builder.add_edge("greeting", END)

rag_graph = graph_builder.compile()
