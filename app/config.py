import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DOCS_DIR: str = os.path.join(BASE_DIR, "oraculo_docs")
    DB_DIR: str = os.path.join(BASE_DIR, "db_oraculo")

    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o"

    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    INGESTION_BATCH_SIZE: int = 100

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)