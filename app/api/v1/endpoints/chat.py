from fastapi import APIRouter,HTTPException,Body
from fastapi.responses import JSONResponse
from app.chatbot.agent.rag import rag_graph

router = APIRouter()


@router.post("/chat")
async def chat_endpoint(query: str=Body(..., min_length=1, description="User query string", embed=True)):
    """Endpoint to handle chat requests."""
    try:
        inital_state = {"query": query}
        # Here you would typically invoke the RAG graph with the user_query
        # For demonstration, we will return a placeholder response
        response = await rag_graph.ainvoke(inital_state)
        final_answer = response["final_answer"]
        return JSONResponse(content={"answer": final_answer})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {str(e)}"
        )