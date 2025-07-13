from app.oraculo import carregar_documentos, salvar_banco_vector
from app.config import logger

if __name__ == "__main__":
    logger.info("🔄 Iniciando processo de ingestão de documentos...")
    documentos = carregar_documentos()
    
    if documentos:
        logger.info(f"📄 Total de documentos carregados: {len(documentos)}")
        logger.info("💾 Salvando no banco vetorial...")
        salvar_banco_vector(documentos)
        logger.info("✅ Processo de ingestão concluído com sucesso!")
    else:
        logger.warning("Nenhum documento encontrado para processar.")