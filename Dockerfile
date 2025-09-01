# --- Estágio 1: Builder ---
# Usamos uma imagem completa para instalar dependências que podem precisar de compilação
FROM python:3.11 as builder

WORKDIR /app

# Instala o Tesseract OCR, uma dependência de sistema para o Pytesseract
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*

# Cria um ambiente virtual isolado
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copia e instala as dependências Python no venv
# Fazer isso em uma camada separada aproveita o cache do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Estágio 2: Final ---
# Usamos uma imagem "slim" para um resultado final muito menor
FROM python:3.11-slim

WORKDIR /app

# Copia o ambiente virtual com as dependências já instaladas do estágio builder
COPY --from=builder /opt/venv /opt/venv

# Copia o Tesseract OCR já instalado do estágio builder
COPY --from=builder /usr/bin/tesseract /usr/bin/tesseract
COPY --from=builder /usr/share/tesseract-ocr/ /usr/share/tesseract-ocr/

# Define o PATH para que o sistema encontre os executáveis no venv
ENV PATH="/opt/venv/bin:$PATH"


# Copia o código da aplicação
# O diretório 'app' local será copiado para '/app/app' dentro do contêiner
COPY ./app /app/app

# Copia o script de inicialização e garante permissão antes de trocar usuário
COPY ./app/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Adiciona um usuário não-root por questões de segurança
RUN useradd --create-home appuser
USER appuser

# Expõe a porta que a API vai rodar
EXPOSE 8000

# Comando padrão para iniciar a aplicação, usando o entrypoint customizado
ENTRYPOINT ["/app/entrypoint.sh"]