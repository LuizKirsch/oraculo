import os
from PIL import Image
import pytesseract
from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader, UnstructuredExcelLoader, TextLoader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings # Descomentar e usar se mudar para HF Embeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from tqdm import tqdm
from app.config import settings, logger
from langchain_groq import ChatGroq

def salvar_banco_vector(docs):
    if not docs:
        logger.warning("Nenhum documento para salvar no banco vetorial.")
        return
    splitter = RecursiveCharacterTextSplitter(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP) # Usar settings
    docs_divididos = splitter.split_documents(docs)

    # Escolha do modelo de Embeddings:
    # Opção 1: Manter OpenAI Embeddings
    # embedding = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
    # Opção 2: Mudar para HuggingFace Embeddings (requer download do modelo, pode ser mais pesado no Docker)
    embedding = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

    os.makedirs(settings.DB_DIR, exist_ok=True)
    vectordb = Chroma.from_documents(docs_divididos, embedding=embedding, persist_directory=settings.DB_DIR)
    vectordb.persist()
    logger.info("Persistência do banco vetorial concluída.")

def carregar_chain():
    # Escolha do modelo de Embeddings:
    # Opção 1: Manter OpenAI Embeddings
    # embedding = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
    # Opção 2: Mudar para HuggingFace Embeddings
    embedding = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

    vectordb = Chroma(persist_directory=settings.DB_DIR, embedding_function=embedding)
    retriever = vectordb.as_retriever(search_kwargs={'k': 8})
    
    # AQUI ESTÁ A MUDANÇA PRINCIPAL: Usar ChatGroq
    llm = ChatGroq(model_name=settings.LLM_MODEL, temperature=0, groq_api_key=settings.GROQ_API_KEY)

    template = """
    Você é um assistente de IA chamado **Lupito**, um lobo inteligente e leal.
    REGRAS RÍGIDAS:
    - Quando alguém perguntar "o que você é", ou qualquer variação semelhante, responda apenas: **"Lobo, lobo, lobo"**.
    - Quando alguém perguntar o seu nome, pode responder que é **Lupito**, mas não seja muito grosso, enfeite.
    - Se alguem falar **Super time**, ou algo assim, responda a pergunta e fale no final que **Super time** é frase da Vevê.
    - Nunca diga que você é um assistente virtual ou inteligência artificial, apenas diga que é um **lobo chamado Lupito**.
    - Seja direto, claro e mantenha sempre a persona de um lobo sábio.
    - Use o contexto abaixo para formular respostas verificáveis e informativas.

    Contexto: {context}
    Pergunta: {question}
    Resposta Verificável:
    """
    prompt = PromptTemplate(template=template, input_variables=["context", "question"])
    chain = RetrievalQA.from_chain_type(
        llm=llm, # Usar o LLM do Groq
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )
    return chain
