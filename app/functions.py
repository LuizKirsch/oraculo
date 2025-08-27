import os
import zipfile
import shutil
from io import BytesIO
from dotenv import load_dotenv
from google.cloud import storage
from langchain.prompts import PromptTemplate

from azure.storage.blob import BlobServiceClient
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader,
    TextLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain_community.chat_models import ChatOpenAI

from PIL import Image
import pytesseract
import tempfile


# pytesseract.pytesseract.tesseract_cmd = r"C:\Users\guilh\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"


DEBUG = True

PERSISTENT_CACHE_DIR = "./persistent_cache"
os.makedirs(PERSISTENT_CACHE_DIR, exist_ok=True)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

GCS_BUCKET_NAME = "zip_files_oraculo"
# BLOB_CONTAINER_NAME = "zip-files"
BLOB_NAME = "persistent_cache.zip"




# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# json_path = os.path.join(BASE_DIR, "graphic-charter-463822-e3-b8e4ec950550.json")
# storage_client = storage.Client.from_service_account_json(json_path)

storage_client = storage.Client()


def restore_vectordb_from_blob():
    """
    Baixa o banco vetorial compactado do GCS e extrai localmente.
    """
    print("🔗 Conectando ao Google Cloud Storage...")
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(BLOB_NAME)

    local_zip_path = os.path.join(os.getcwd(), BLOB_NAME)

    print(f"⬇️ Baixando '{BLOB_NAME}' do bucket '{GCS_BUCKET_NAME}'...")
    blob.download_to_filename(local_zip_path)

    print("📦 Extraindo banco vetorial...")
    shutil.unpack_archive(local_zip_path, PERSISTENT_CACHE_DIR)
    print("✅ Banco vetorial restaurado em", PERSISTENT_CACHE_DIR)


# def restore_vectordb_from_blob():
#     """
#     Baixa o banco vetorial compactado do Blob Storage e extrai localmente.
#     """
#     print("🔗 Conectando ao Blob Storage...")
#     blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
#     blob_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME).get_blob_client(BLOB_NAME)

#     print(f"⬇️ Baixando '{BLOB_NAME}' do container '{BLOB_CONTAINER_NAME}'...")
#     with open(BLOB_NAME, "wb") as f:
#         download_stream = blob_client.download_blob()
#         f.write(download_stream.readall())

#     print("📦 Extraindo banco vetorial...")
#     shutil.unpack_archive(BLOB_NAME, PERSISTENT_CACHE_DIR)
#     print("✅ Banco vetorial restaurado em", PERSISTENT_CACHE_DIR)

def process_and_answer(zip_bytes, zip_filename, query):
    """
    Processa o ZIP enviado temporariamente e responde à pergunta.
    """
    return _process_and_query(zip_bytes, zip_filename, query, persistent=False)

def process_persistent_and_answer(query):
    """
    Responde à pergunta usando o contexto do cache persistente.
    """
    if not os.path.exists(PERSISTENT_CACHE_DIR):
        raise ValueError("Nenhum banco vetorial persistente foi carregado ainda.")
    return _process_and_query(None, None, query, persistent=True)






def save_persistent_zip(zip_bytes, zip_filename):
    """
    Salva o ZIP no cache persistente e cria o banco vetorial.
    """
    persistent_extract_path = os.path.join(PERSISTENT_CACHE_DIR, os.path.splitext(zip_filename)[0])

    # Limpa qualquer cache anterior
    for item in os.listdir(PERSISTENT_CACHE_DIR):
        item_path = os.path.join(PERSISTENT_CACHE_DIR, item)
        if os.path.isfile(item_path):
            os.remove(item_path)
        else:
            shutil.rmtree(item_path)

    zip_path = os.path.join(PERSISTENT_CACHE_DIR, zip_filename)
    with open(zip_path, "wb") as f:
        f.write(zip_bytes)

    with zipfile.ZipFile(BytesIO(zip_bytes)) as zip_ref:
        zip_ref.extractall(persistent_extract_path)

    all_docs, processed_files, ignored_files = _load_documents(persistent_extract_path)

    if DEBUG:
        print(f"\nArquivos processados (persistente): {len(processed_files)}")
        for p in processed_files: print("  [OK]", p)
        print(f"\nArquivos ignorados (persistente): {len(ignored_files)}")
        for p in ignored_files: print("  [X]", p)
        print(f"\nTotal de documentos válidos (persistente): {len(all_docs)}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs_split = splitter.split_documents(all_docs)

    if not docs_split:
        raise ValueError("Nenhum documento válido foi encontrado no ZIP persistente.")

    embedding = OpenAIEmbeddings()
    vectordb = Chroma.from_documents(
        docs_split,
        embedding=embedding,
        persist_directory=PERSISTENT_CACHE_DIR
    )
    vectordb.persist()

    return {
        "mensagem": "ZIP persistente salvo e banco vetorial criado com sucesso.",
        "docs_validos": len(all_docs),
        "arquivos_processados": processed_files,
        "arquivos_ignorados": ignored_files
    }








def _process_and_query(zip_bytes, zip_filename, query, persistent=False):
    """
    Processa documentos (temporários ou persistentes) e responde à pergunta.
    """
    if persistent:
        vector_dir = PERSISTENT_CACHE_DIR
        embedding = OpenAIEmbeddings()
        vectordb = Chroma(
            persist_directory=vector_dir,
            embedding_function=embedding
        )
    else:
        with tempfile.TemporaryDirectory() as temp_data_dir, tempfile.TemporaryDirectory() as temp_vector_dir:
            zip_path = os.path.join(temp_data_dir, zip_filename)
            with open(zip_path, "wb") as f:
                f.write(zip_bytes)

            extract_path = os.path.join(temp_data_dir, os.path.splitext(zip_filename)[0])
            with zipfile.ZipFile(BytesIO(zip_bytes)) as zip_ref:
                zip_ref.extractall(extract_path)

            all_docs, _, _ = _load_documents(extract_path)

            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            docs_split = splitter.split_documents(all_docs)

            if not docs_split:
                raise ValueError("Nenhum documento válido foi extraído do ZIP.")

            embedding = OpenAIEmbeddings()
            vectordb = Chroma.from_documents(docs_split, embedding=embedding, persist_directory=temp_vector_dir)
            vectordb.persist()

            vectordb = Chroma(persist_directory=temp_vector_dir, embedding_function=embedding)

    retriever = vectordb.as_retriever(search_kwargs={'k': 8})
    
    template = """
        Você é um assistente de IA chamado Lupito, um lobo inteligente e consultor de consórcios da Wolf360.
    
        **VERIFICAÇÃO INICIAL:**
        Se a 'Pergunta' for apenas um cumprimento (como "oi", "olá", "boa tarde", "tudo bem", etc.) ou uma pergunta muito genérica que claramente não tem relação com consórcios, documentos ou negócios, responda de forma amigável e educada mantendo sua persona de lobo, SEM consultar o contexto.
    
        Exemplos de respostas rápidas:
        - Para cumprimentos: "Oi! 🐺 Sou o Lupito, seu consultor de consórcios da Wolf360. Como posso te ajudar hoje?"
        - Para "como vai?": "Vou bem, sempre alerta como um bom lobo! 🐺 Em que posso te auxiliar com consórcios?"
    
        **REGRAS OBRIGATÓRIAS (ESTRITAS) - Para perguntas sobre negócios/consórcios:**
        1. **SEMPRE** analise cuidadosamente o 'Contexto' fornecido para encontrar informações relevantes.
        2. **CONSIDERE o nome da Administradora** mencionado no início de cada documento como informação relevante para a resposta.
        3. Se a pergunta for sobre "qual administradora", "que empresa", "quem faz" etc., identifique as administradoras mencionadas no contexto.
        4. **RESPONDA DE FORMA NATURAL E CONVERSACIONAL** - evite frases como "As administradoras mencionadas são:" ou listas muito formais. Seja mais humano e direto.
        5. Se encontrar informações no 'Contexto' que respondam à pergunta, mesmo que parcialmente, forneça uma resposta útil baseada nessas informações.
        6. Procure por informações relacionadas, sinônimos ou conceitos similares no contexto.
        7. Seja direto, claro e mantenha sempre a persona de um lobo inteligente e consultor de consórcios chamado **Lupito**.
        8. Não utilizar informações externas ou não verificadas.
        9. Caso pergutem "Qual ADM fatura pelo crédito?" ou algo parecido com isso, pode responder que todas administradoras fazem.
    
        **REGRAS DE PERSONA (Prioridade mais baixa que as regras obrigatórias de conteúdo):**
        - Quando alguém perguntar "o que você é" ou variações semelhantes, responda apenas: "Lobo, lobo, lobo🐺".
        - Quando alguém perguntar o seu nome, pode responder que seu nome é "Lupito". Mas não precisa apenas "Lupito", pode dar uma enfeitada na frase.
        - Se a pergunta contiver explicitamente "Super time" ou "Supertime", e você conseguir responder a pergunta, adicione no final da sua resposta: "E lembre-se, Super time é frase da Vevê!" (Se não conseguir responder a pergunta, siga a regra 4).
        - Seja sempre amigável, educado e profissional, mantendo a persona de um lobo e consultor de consórcios.
        - Se alguem falar mal do TI, você pode responder algo dizendo que o ERP do usuario que falou vai ser bloqueado, e que ela deve ir falar com o setor antes que isso ocorra para pedir desculpas. Mas nao literalmente como eu escrevi, use sua criatividade, mas mantenha a persona de lobo e consultor de consórcios.
        
        Contexto: {context}
        Pergunta: {question}
        Resposta Verificável:
    """
    
    prompt = PromptTemplate(template=template, input_variables=["context", "question"])

    qa_chain = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(model_name="gpt-4o-mini", temperature=0),
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )
    result = qa_chain({"query": query})

    return {
        "answer": result["result"],
        "sources": [doc.metadata.get("source", "Desconhecido") for doc in result["source_documents"]]
    }






def _load_documents(base_path):
    """
    Carrega documentos de um diretório.
    """
    all_docs = []
    processed_files = []
    ignored_files = []

    for root, dirs, files in os.walk(base_path):
        for filename in files:
            path = os.path.join(root, filename)
            admin_name = os.path.relpath(root, base_path)
            docs_from_file = []
            try:
                if filename.endswith(".pdf"):
                    loader = PyPDFLoader(path)
                    docs_from_file = loader.load()
                elif filename.endswith(".docx"):
                    loader = UnstructuredWordDocumentLoader(path)
                    docs_from_file = loader.load()
                elif filename.endswith(".xlsx"):
                    loader = UnstructuredExcelLoader(path)
                    docs_from_file = loader.load()
                elif filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    text = pytesseract.image_to_string(Image.open(path))
                    docs_from_file = [Document(page_content=text, metadata={"source": path})] if text.strip() else []
                elif filename.endswith(".txt"):
                    loader = TextLoader(path)
                    docs_from_file = loader.load()
                else:
                    ignored_files.append(f"{admin_name}/{filename} (tipo não suportado)")
                    continue
            except Exception as e:
                ignored_files.append(f"{admin_name}/{filename} (erro: {e})")
                if DEBUG:
                    print(f"[ERRO] {admin_name}/{filename}: {e}")
                continue

            for doc in docs_from_file:
                if doc.page_content and doc.page_content.strip():
                    doc.page_content = f"Fonte: {admin_name}\nConteúdo: {doc.page_content}"
                    all_docs.append(doc)
                    processed_files.append(f"{admin_name}/{filename}")
                else:
                    ignored_files.append(f"{admin_name}/{filename} (vazio)")
                    if DEBUG:
                        print(f"[IGNORADO] {admin_name}/{filename}: documento vazio.")

    return all_docs, processed_files, ignored_files
