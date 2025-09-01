from google.cloud import storage
from dotenv import load_dotenv
import os

load_dotenv()

service_account_info = {
    "type": os.getenv("GOOGLE_TYPE"),
    "project_id": os.getenv("GOOGLE_PROJECT_ID"),
    "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("GOOGLE_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
    "auth_uri": os.getenv("GOOGLE_AUTH_URI"),
    "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL"),
    "universe_domain": os.getenv("GOOGLE_UNIVERSE_DOMAIN"),
}

if not all(service_account_info.values()):
    raise ValueError("Uma ou mais variáveis de credenciais do Google Cloud não foram encontradas no .env")

storage_client = storage.Client.from_service_account_info(service_account_info)
bucket = storage_client.bucket("lupito-oraculo")

is_cloud_run = os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_ENV")
base_dir = "/tmp" if is_cloud_run else "/app"

for blob in bucket.list_blobs(prefix="db_oraculo/"):
    print(f"Baixando: {blob.name}")
    local_path = os.path.join(base_dir, blob.name)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    blob.download_to_filename(local_path)
    print(f"Salvo em: {local_path}")