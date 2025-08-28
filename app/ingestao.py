from app.oraculo import carregar_documentos, salvar_banco_vector
from app.config import logger
from azure.storage.blob import BlobServiceClient
import zipfile
import io
import os 

# Variáveis de ambiente (recomendado para segurança, mas você pode substituir pelas suas strings direto)
AZURE_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=storageapioraculozips;AccountKey=***REMOVED***;EndpointSuffix=core.windows.net"
AZURE_CONTAINER_NAME = "zip-files"
BLOB_NAME = "INFORMAÇÕES ADMs-20250612T203706Z-1-001.zip"

def listar_blobs():
    # Cliente do serviço
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)

    # Pega o blob específico
    blob_client = container_client.get_blob_client(BLOB_NAME)

    pasta_destino = "oraculo_docs"
    os.makedirs(pasta_destino, exist_ok=True)
    
    print(f"⬇️ Lendo {BLOB_NAME} do Azure...")

    # Baixa o conteúdo do blob em memória com barra de progresso
    from tqdm import tqdm
    tamanho = blob_client.get_blob_properties().size
    stream = io.BytesIO()
    downloader = blob_client.download_blob()
    with tqdm(total=tamanho, unit='B', unit_scale=True, desc=BLOB_NAME) as barra:
        for chunk in downloader.chunks():
            stream.write(chunk)
            barra.update(len(chunk))
    stream.seek(0)

    with zipfile.ZipFile(stream) as z:
        print(f"📦 Extraindo arquivos do {BLOB_NAME} para {pasta_destino}...\n")
        raiz = z.namelist()[0].split("/")[0]  # pega o nome da pasta raiz
        for name in z.namelist():
            if name.endswith("/"):
                continue
            # Remove o diretório raiz do caminho
            caminho_relativo = os.path.relpath(name, raiz)
            # Remove espaços extras dos diretórios e arquivos
            partes = [parte.strip() for parte in caminho_relativo.split(os.sep)]
            caminho_limpo = os.path.join(*partes)
            caminho_destino = os.path.join(pasta_destino, caminho_limpo)
            os.makedirs(os.path.dirname(caminho_destino), exist_ok=True)
            with z.open(name) as fonte, open(caminho_destino, "wb") as destino:
                destino.write(fonte.read())
            print("-", caminho_limpo)
    print(f"✅ Todos os arquivos foram extraídos para {pasta_destino}")

if __name__ == "__main__":
    logger.info("📥 Iniciando download e extração do ZIP do Azure Blob Storage...")
    listar_blobs()

    logger.info("🔄 Iniciando processo de ingestão de documentos...")
    documentos = carregar_documentos()
    
    if documentos:
        logger.info(f"📄 Total de documentos carregados: {len(documentos)}")
        logger.info("💾 Salvando no banco vetorial...")
        salvar_banco_vector(documentos)
        logger.info("✅ Processo de ingestão concluído com sucesso!")
    else:
        logger.warning("Nenhum documento encontrado para processar.")