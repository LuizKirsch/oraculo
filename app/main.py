from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from app.functions import (
    # process_and_answer,
    process_persistent_and_answer,
    restore_vectordb_from_blob
)

app = FastAPI(
    title="Oráculo API",
    description="API para processar ZIPs e responder perguntas (usando banco vetorial persistente)",
    version="2.0.0"
)

@app.on_event("startup")
async def startup_event():
    """
    Restaura o banco vetorial do Blob Storage ao iniciar a API.
    """
    try:
        restore_vectordb_from_blob()
    except Exception as e:
        print(f"⚠️ Erro ao restaurar banco vetorial: {e}")

@app.post("/process_and_ask")
async def process_and_ask(query: str = Form(...)):
    """
    Responde a uma pergunta usando o contexto do banco vetorial persistente.
    """
    try:
        result = process_persistent_and_answer(query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
