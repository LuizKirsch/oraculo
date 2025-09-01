#!/bin/bash
# Script de inicialização para rodar google-banco.py antes de iniciar a API
set -e

python /app/app/google-banco.py
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
