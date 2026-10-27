"""Jour 5 : API FastAPI autour du RAG et de l'agent."""
from contextlib import asynccontextmanager

import groq
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from src import rag
from src.agent import run_agent
from src.embed import MODEL_NAME, get_collection, load_model


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class Source(BaseModel):
    source: str
    page: int
    score: float


class AskResponse(BaseModel):
    answer: str
    answered: bool
    sources: list[Source]
    best_score: float


class Step(BaseModel):
    tool: str
    arguments: dict
    result: str


class AgentResponse(BaseModel):
    answer: str
    answered: bool
    sources: list[Source]
    steps: list[Step]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Le modèle d'embedding et l'index sont chargés une seule fois au démarrage.
    app.state.model = load_model()
    app.state.collection = get_collection()
    yield


app = FastAPI(title="Assistant RAG ENIAD", version="0.1.0", lifespan=lifespan)


def llm_http_error(exc: groq.APIError) -> HTTPException:
    """Traduit une erreur du fournisseur LLM sans exposer de détails internes."""
    if isinstance(exc, groq.RateLimitError):
        return HTTPException(status_code=429, detail="Limite de requêtes du LLM atteinte, réessaie dans un instant.")
    return HTTPException(status_code=502, detail="Le service de génération est indisponible.")


@app.get("/health")
def health(request: Request) -> dict:
    return {
        "status": "ok",
        "chunks": request.app.state.collection.count(),
        "embedding_model": MODEL_NAME,
        "llm": rag.LLM_MODEL,
        "threshold": rag.SCORE_THRESHOLD,
    }


# Ces fonctions sont synchrones (def, pas async def) : FastAPI les exécute dans un
# pool de threads, ce qui évite de bloquer le serveur pendant l'appel réseau au LLM.
@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, request: Request):
    state = request.app.state
    try:
        return rag.answer_question(body.question, model=state.model, collection=state.collection)
    except groq.APIError as exc:
        raise llm_http_error(exc) from exc


@app.post("/agent", response_model=AgentResponse)
def agent(body: AskRequest, request: Request):
    state = request.app.state
    try:
        return run_agent(body.question, model=state.model, collection=state.collection)
    except groq.APIError as exc:
        raise llm_http_error(exc) from exc