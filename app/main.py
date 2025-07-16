import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.oraculo import carregar_chain
from app.config import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    app_state["qa_chain"] = carregar_chain()
    yield
    app_state.clear()

app = FastAPI(lifespan=lifespan)
app_state = {}

class Pergunta(BaseModel):
    pergunta: str

@app.post("/consultar")
def consultar(pergunta: Pergunta):
    chain = app_state.get("qa_chain")
    if not chain:
        raise HTTPException(status_code=503, detail="Serviço indisponível...")

    logger.info(f"Recebida nova consulta: '{pergunta.pergunta}'")
    resultado = chain.invoke({"query": pergunta.pergunta})

    # --- LINHA DE DEBUG ---
    if resultado.get("source_documents"):
        primeiro_chunk = resultado["source_documents"][0].page_content
        logger.info(f"DEBUG: Conteúdo do primeiro chunk recuperado:\n---\n{primeiro_chunk}\n---")
    # --- FIM DO DEBUG ---

    fontes_formatadas = []
    if resultado.get("source_documents"):
        for doc in resultado["source_documents"]:
            fonte = os.path.basename(doc.metadata.get('source', 'Desconhecido'))
            fontes_formatadas.append(fonte)
    
    fontes_unicas = sorted(list(set(fontes_formatadas)))

    return {
        "resposta": resultado["result"],
        "fontes": fontes_unicas
    }