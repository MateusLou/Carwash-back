from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import glob
import dotenv
from importlib import import_module

dotenv.load_dotenv()

working_directory = os.path.dirname(os.path.abspath(__file__))

# src/ precisa estar no sys.path ANTES de importar os use cases: eles (e os
# models) fazem "from database.database import ...". Rodando
# "uvicorn src.app:app" a partir da raiz, quem entra no path é a raiz, não o
# src/ — e cada rota falharia calada no except lá embaixo, sumindo do /docs.
if working_directory not in sys.path:
    sys.path.insert(0, working_directory)

from config.config import config

app = FastAPI(title="API Lava-Rápido Nogueira — dashboard de agendamentos")

@app.get("/")
def test():
    return {"status": "OK"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config["client_url"]],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

use_cases_directory = os.path.join(working_directory, "use_cases")
routes = glob.glob(os.path.join(use_cases_directory, "**/index.py"), recursive=True)

for route in routes:
    relative_path = os.path.relpath(route, working_directory)
    module_name = os.path.splitext(relative_path)[0].replace(os.path.sep, '.')

    try:
        module = import_module(module_name)
        if hasattr(module, 'router'):
            app.include_router(module.router)
    except ModuleNotFoundError as e:
        print(f"Erro ao importar módulo {module_name}: {e}")
