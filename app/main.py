import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.oraculo import carregar_chain_com_filtro
from app.config import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Não há necessidade de carregar a chain no lifespan, pois ela será carregada
    # dinamicamente com base no filtro.
    yield
    # Limpar qualquer estado global se houver necessidade
    # app_state.clear() # Se app_state não for mais para ser usado globalmente para a chain

app = FastAPI(lifespan=lifespan)
# app_state pode ser usado para armazenar coisas como o vectordb base, se necessário,
# mas não a chain inteira se ela for criada dinamicamente.
app_state = {} 

class Pergunta(BaseModel):
    pergunta: str
    administradora: Optional[str] = None # Campo opcional para especificar a administradora

@app.post("/consultar")
def consultar(pergunta: Pergunta):
    admin_identificada = None

    # 1. Tentativa de extrair a administradora da pergunta (pode ser mais robusto com LLM ou regex)
    if "bradesco" in pergunta.pergunta.lower():
        admin_identificada = "Bradesco"
    elif "caixa" in pergunta.pergunta.lower():
        admin_identificada = "Caixa"
    # Adicione mais regras conforme necessário para outras administradoras

    # 2. Se a administradora foi fornecida explicitamente no payload, ela tem prioridade
    if pergunta.administradora:
        admin_identificada = pergunta.administradora

    try:
        # Carregar a chain com o filtro de administradora, se identificado
        qa_chain = carregar_chain_com_filtro(admin_name=admin_identificada)
    except Exception as e:
        logger.error(f"Erro ao carregar a chain QA: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Serviço indisponível ou erro ao inicializar.")

    logger.info(f"Recebida nova consulta: '{pergunta.pergunta}' (Admin identificada: {admin_identificada if admin_identificada else 'Nenhuma'})")
    
    try:
        resultado = qa_chain({"query": pergunta.pergunta})
    except Exception as e:
        logger.error(f"Erro ao executar a consulta na chain: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar a consulta.")

    # --- LINHA DE DEBUG ---
    if resultado.get("source_documents"):
        # Mostra o conteúdo do primeiro chunk recuperado e seus metadados para debug
        primeiro_chunk = resultado["source_documents"][0].page_content
        primeiro_chunk_metadata = resultado["source_documents"][0].metadata
        logger.info(f"DEBUG: Conteúdo do primeiro chunk recuperado:\n---\n{primeiro_chunk}\n---")
        logger.info(f"DEBUG: Metadados do primeiro chunk recuperado: {primeiro_chunk_metadata}")
    # --- FIM DO DEBUG ---

    fontes_formatadas = []
    if resultado.get("source_documents"):
        for doc in resultado["source_documents"]:
            # Adicionando o nome da administradora na fonte formatada, se disponível nos metadados
            admin_nome_fonte = doc.metadata.get('admin_name', 'N/A')
            fonte_arquivo = os.path.basename(doc.metadata.get('source', 'Desconhecido'))
            fontes_formatadas.append(f"{fonte_arquivo} (Admin: {admin_nome_fonte})")
    
    fontes_unicas = sorted(list(set(fontes_formatadas)))

    return {
        "resposta": resultado["result"],
        "fontes": fontes_unicas
    }