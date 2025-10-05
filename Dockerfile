# Use uma imagem oficial do Python como base
FROM python:3.9-slim

# Instale dependências do sistema para o Chrome e Selenium
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    ca-certificates \
    libx11-dev \
    libxext6 \
    libxi6 \
    libgdk-pixbuf2.0-0 \
    libdbus-1-3 \
    libfontconfig \
    libxrender1 \
    libnss3 \
    libgconf-2-4 \
    libasound2 \
    libxss1 \
    libappindicator3-1 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libgl1-mesa-glx \
    && apt-get clean

# Instalar o Chrome
RUN wget -q -O - https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb > google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb \
    && apt-get install -y -f

# Instalar o ChromeDriver (compatível com a versão do Chrome)
RUN CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) \
    && wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/ \
    && rm chromedriver_linux64.zip

# Definir variáveis de ambiente
ENV PATH="/usr/local/bin/chromedriver:${PATH}"

# Criar e definir o diretório de trabalho
WORKDIR /app

# Copiar o código do projeto para o contêiner
COPY . /app

# Instalar as dependências do Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Definir a variável de ambiente para rodar Flask no Render
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Expor a porta para acesso externo
EXPOSE 5000

# Comando para rodar o Flask
CMD ["flask", "run"]
