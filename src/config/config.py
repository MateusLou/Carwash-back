import os
import dotenv
dotenv.load_dotenv()

# client_url = onde o carwash-front roda. Serve para o CORS (app.py) e para
# montar o link do e-mail de recuperação de senha. Em dev é o Vite; em produção
# vem do .env, para não deixar domínio chumbado no código.
config = {
    "client_url": "http://localhost:5173"
    if os.getenv("ENVIRONMENT") == "dev"
    else os.getenv("CLIENT_URL", "http://localhost:5173")
}
