#!/bin/bash
# start.sh - Script para iniciar o Blaze Bot no Render

set -e  # para encerrar em caso de erro
export PYTHONUNBUFFERED=1  # mantém logs em tempo real

echo "🚀 Iniciando Blaze Bot no Render..."

# Instala Chromium e ChromeDriver (Render usa Debian/Ubuntu slim)
apt-get update -qq
apt-get install -y chromium chromium-driver > /dev/null 2>&1

# Define variáveis de ambiente para o Selenium localizar o Chrome e o Driver
export CHROME_PATH=$(which chromium)
export CHROMEDRIVER_PATH=$(which chromedriver)

echo "✅ Chromium instalado em: $CHROME_PATH"
echo "✅ ChromeDriver instalado em: $CHROMEDRIVER_PATH"

# Executa o bot
python3 main.py
