# Blaze Bot - Render Deployment

## Passos para Deploy

1. Crie um repositório no GitHub e suba todos os arquivos.
2. No Render.com, crie um **Web Service**.
3. Conecte o repositório do GitHub.
4. Adicione as variáveis de ambiente:
   - `TOKEN_TELEGRAM` = Seu token do bot Telegram
   - `CHAT_ID` = ID do chat ou grupo
5. Comando de inicialização:
```bash
./start.sh
