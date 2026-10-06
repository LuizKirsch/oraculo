
# Oráculo IA

> ⚠️ **Prova de conceito (POC).** Este projeto não está pronto para produção: não tem autenticação, testes automatizados nem tratamento robusto de erros.

API inteligente para consultas internas, baseada em banco vetorial e processamento de documentos. Utiliza Python, Docker e integrações modernas para facilitar buscas e respostas automáticas.

## Funcionalidades
- Ingestão e indexação de documentos (pasta `oraculo_docs`)
- Consultas rápidas via API REST
- Banco vetorial persistente (ChromaDB)
- Fácil atualização e manutenção via Docker Compose

## Configuração
- **Persona e regras do bot:** edite `app/prompt.txt` (precisa conter `{context}` e `{question}`). Outro arquivo pode ser usado via `PROMPT_FILE` no `.env`.
- **Documentos:** cada subpasta de `oraculo_docs/` vira uma categoria. Se a pergunta citar o nome de uma pasta, a busca filtra só os documentos dela.
- **Bucket do banco no GCS:** `GCS_BUCKET` no `.env` (opcional: se definido, o container baixa o banco desse bucket ao iniciar; sem ele, usa o `db_oraculo/` local).

## Requisitos
- Docker e Docker Compose
- Python 3.10+
- Insomnia/Postman para testes

## Instalação e Execução
1. Clone o repositório e acesse a pasta do projeto.
2. Adicione seus documentos em `oraculo_docs/`.
3. Gere o banco vetorial (veja comandos abaixo).
4. Inicie a API:
	 ```powershell
	 docker-compose up -d
	 ```

## Comandos Principais
Veja os arquivos `comandos_gerar_banco.txt` e `comandos_atualizar_codigo.txt` para instruções detalhadas.

### Gerar/Recriar Banco Vetorial
```powershell
docker-compose down
Remove-Item -Recurse -Force "db_oraculo\*" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "oraculo_docs\*" -ErrorAction SilentlyContinue
docker-compose build
docker-compose run --rm oraculo-app python -m app.ingestao
docker-compose up -d
```

### Atualizar Código/Docker
```powershell
docker-compose down
docker-compose build
docker-compose up -d
```

## Teste Rápido
Faça uma consulta usando Insomnia/Postman:
- **POST**: `http://localhost:8002/consultar`
- **Header**: `Content-Type: application/json`
- **Body**:
	```json
	{"pergunta": "oi"}
	```

## Estrutura do Projeto
```
├── app/
│   ├── config.py
│   ├── ingestao.py
│   ├── main.py
│   └── oraculo.py
├── db_oraculo/
├── oraculo_docs/
├── comandos_gerar_banco.txt
├── comandos_atualizar_codigo.txt
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
```

## Dicas de Manutenção
- Sempre gere o banco vetorial ao adicionar ou modificar documentos.
- Use os comandos de atualização ao alterar o código Python ou configurações.
- Consulte os logs com `docker-compose logs --tail=20` para debug.

## Licença
Projeto privado para uso interno.
