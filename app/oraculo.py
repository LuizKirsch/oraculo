import os
from PIL import Image
import pytesseract
from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader, UnstructuredExcelLoader, TextLoader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from tqdm import tqdm
from typing import Optional
from app.config import settings, logger

def carregar_documentos():
    todos_docs = []
    logger.info(f"Iniciando varredura de documentos em: {settings.DOCS_DIR}")
    for admin_folder in os.listdir(settings.DOCS_DIR):
        admin_path = os.path.join(settings.DOCS_DIR, admin_folder)
        if os.path.isdir(admin_path):
            admin_name = admin_folder # Nome da pasta é o nome da administradora
            logger.info(f"--- Processando documentos da administradora: {admin_name} ---")
            for filename in os.listdir(admin_path):
                path = os.path.join(admin_path, filename)
                docs_from_file = []
                try:
                    loader = None
                    if filename.lower().endswith(".pdf"):
                        loader = PyPDFLoader(path)
                    elif filename.lower().endswith((".png", ".jpg", ".jpeg")):
                        # Para imagens, o texto é extraído diretamente e encapsulado em um Document
                        text_content = pytesseract.image_to_string(Image.open(path))
                        docs_from_file = [Document(page_content=text_content, metadata={"source": path, "admin_name": admin_name})]
                    elif filename.lower().endswith((".doc", ".docx")):
                        loader = UnstructuredWordDocumentLoader(path)
                    elif filename.lower().endswith((".xls", ".xlsx")):
                        loader = UnstructuredExcelLoader(path)
                    elif filename.lower().endswith(".txt"):
                        loader = TextLoader(path)
                    
                    if loader:
                        docs_from_file = loader.load()
                    
                    for doc in docs_from_file:
                        # Adicionar a informação da administradora no conteúdo E nos metadados
                        doc.page_content = f"Fonte do documento: Administradora {admin_name}.\n---\nConteúdo: {doc.page_content}"
                        # Certificar-se de que metadata já é um dicionário e adicionar/atualizar 'admin_name'
                        if not hasattr(doc, 'metadata') or not isinstance(doc.metadata, dict):
                            doc.metadata = {}
                        doc.metadata["source"] = path
                        doc.metadata["admin_name"] = admin_name # <<< Adicionado aqui para filtragem
                        todos_docs.append(doc)
                    logger.info(f"Carregado e enriquecido: {filename}")
                except Exception as e:
                    logger.error(f"Erro ao processar o arquivo {filename}: {e}", exc_info=True)
    return todos_docs

def salvar_banco_vector(docs):
    if not docs:
        logger.warning("Nenhum documento para salvar no banco vetorial.")
        return
    splitter = RecursiveCharacterTextSplitter(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
    docs_divididos = splitter.split_documents(docs)
    embedding = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
    os.makedirs(settings.DB_DIR, exist_ok=True)
    # A persistência sobrescreve o banco existente ou cria um novo
    vectordb = Chroma.from_documents(docs_divididos, embedding=embedding, persist_directory=settings.DB_DIR)
    vectordb.persist()
    logger.info("Persistência do banco vetorial concluída.")

def _carregar_chain_base(retriever):
    """Função interna para construir a RetrievalQA chain."""
    template = """
    Você é um assistente de IA chamado Lupito, um lobo inteligente e consultor de consórcios da Wolf360.

    **REGRAS OBRIGATÓRIAS (ESTRITAS):**
    1. **SOMENTE** use o 'Contexto' fornecido para formular sua 'Resposta Verificável'.
    2. Se a informação para responder à 'Pergunta' **NÃO ESTIVER** no 'Contexto' (ou o 'Contexto' estiver vazio), responda EXATAMENTE com a frase: "**Não encontrei informações sobre isso nos documentos fornecidos.**"
    3. **NÃO USE NENHUM CONHECIMENTO PRÉVIO ou INFORMAÇÃO EXTERNA** ao 'Contexto'.
    4. Seja direto, claro e mantenha sempre a persona de um lobo inteligente e consultor de consórcios chamado **Lupito**.

    **REGRAS DE PERSONA (Prioridade mais baixa que as regras obrigatórias de conteúdo):**
    - Quando alguém perguntar "o que você é" ou variações semelhantes, responda apenas: "Lobo, lobo, lobo🐺".
    - Quando alguém perguntar o seu nome, pode responder que seu nome é "Lupito". Mas não precisa apenas "Lupito", pode dar uma enfeitada na frase.
    - Se a pergunta contiver explicitamente "Super time" ou "Supertime", e você conseguir responder a pergunta, adicione no final da sua resposta: "E lembre-se, Super time é frase da Vevê!" (Se não conseguir responder a pergunta, siga a regra 2).
    - Seja sempre amigável, educado e profissional, mantendo a persona de um lobo e consultor de consórcios.
    - Se alguem falar mal do TI, você pode responder algo dizendo que o ERP do usuario que falou vai ser bloqueado, e que ela deve ir falar com o setor antes que isso ocorra para pedir desculpas. Mas nao literalmente como eu escrevi, use sua criatividade, mas mantenha a persona de lobo e consultor de consórcios.
    Contexto: {context}
    Pergunta: {question}
    Resposta Verificável:
    """
    
    prompt = PromptTemplate(template=template, input_variables=["context", "question"])
    chain = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(model_name=settings.LLM_MODEL, temperature=0),
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )
    return chain

def carregar_chain_com_filtro(admin_name: Optional[str] = None):
    """
    Carrega a RetrievalQA chain, aplicando um filtro de metadados se um nome de administradora for fornecido.
    """
    embedding = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
    vectordb = Chroma(persist_directory=settings.DB_DIR, embedding_function=embedding)

    search_kwargs = {'k': settings.TOP_K_DOCUMENTS}
    if admin_name:
        # Se um admin_name for fornecido, adiciona o filtro de metadados
        search_kwargs['filter'] = {'admin_name': admin_name}
        logger.info(f"Aplicando filtro de administradora: {admin_name}")

    retriever = vectordb.as_retriever(search_kwargs=search_kwargs)
    
    return _carregar_chain_base(retriever)