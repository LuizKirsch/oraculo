import os
import shutil
from dotenv import load_dotenv

# from azure.storage.blob import BlobServiceClient
from google.cloud import storage

from functions import save_persistent_zip
from langchain.prompts import PromptTemplate

load_dotenv()

# AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
GCS_BUCKET_NAME = "zip_files_oraculo"
# BLOB_CONTAINER_NAME = "zip-files"

BLOB_NAME = "persistent_cache.zip"
ZIP_LOCAL_PATH = "../documentos/INFORMAÇÕES ADMs-20250612T203706Z-1-001.zip"

storage_client = storage.Client.from_service_account_json("./graphic-charter-463822-e3-b8e4ec950550.json")

# def process_and_upload_vectordb():
#     """
#     Processa o ZIP localmente, gera o banco vetorial,
#     compacta e envia para o Blob Storage.
#     """
#     print("📦 Processando ZIP local...")
#     with open(ZIP_LOCAL_PATH, "rb") as f:
#         zip_bytes = f.read()

#     result = save_persistent_zip(zip_bytes, os.path.basename(ZIP_LOCAL_PATH))
#     print("✅ Banco vetorial criado localmente:")
#     print(result)

#     # Compactar a pasta do banco vetorial
#     print("📦 Compactando banco vetorial para 'persistent_cache.zip'...")
#     shutil.make_archive("persistent_cache", "zip", "persistent_cache")
#     print("✅ Arquivo 'persistent_cache.zip' criado.")

#     # Fazer upload para o Blob Storage
#     print("☁️ Conectando ao Azure Blob Storage...")
#     blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
#     container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)

#     print(f"⬆️ Enviando '{BLOB_NAME}' para o container '{BLOB_CONTAINER_NAME}'...")
#     with open("persistent_cache.zip", "rb") as data:
#         container_client.upload_blob(name=BLOB_NAME, data=data, overwrite=True)
#     print("✅ Banco vetorial enviado para o Blob Storage com sucesso!")

def process_and_upload_vectordb():
    """
    Processa o ZIP localmente (se ainda não existir), gera o banco vetorial,
    compacta e envia para o Google Cloud Storage.
    """
    # Se já existir, pula o processamento
    if not os.path.exists("persistent_cache"):
        print("📦 Processando ZIP local...")
        with open(ZIP_LOCAL_PATH, "rb") as f:
            zip_bytes = f.read()

        result = save_persistent_zip(zip_bytes, os.path.basename(ZIP_LOCAL_PATH))
        print("✅ Banco vetorial criado localmente:")
        print(result)
    else:
        print("⚡ Banco vetorial já existe, pulando processamento.")

    # Compactar a pasta do banco vetorial
    if not os.path.exists("persistent_cache.zip"):
        print("📦 Compactando banco vetorial para 'persistent_cache.zip'...")
        shutil.make_archive("persistent_cache", "zip", "persistent_cache")
        print("✅ Arquivo 'persistent_cache.zip' criado.")
    else:
        print("⚡ Arquivo 'persistent_cache.zip' já existe, pulando compactação.")

    # Upload para Google Cloud Storage
    print("☁️ Conectando ao Google Cloud Storage...")
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(BLOB_NAME)

    print(f"⬆️ Enviando '{BLOB_NAME}' para o bucket '{GCS_BUCKET_NAME}'...")
    blob.upload_from_filename("persistent_cache.zip")
    print("✅ Banco vetorial enviado para o GCS com sucesso!")



if __name__ == "__main__":
    process_and_upload_vectordb()
