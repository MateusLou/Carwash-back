import os
import dotenv
dotenv.load_dotenv()

# Lacuna em branco no contrato vira um marcador visível em vez de espaço vazio ou
# linha pontilhada: `[CNPJ a informar]` alguém lê e cobra o dado; um espaço em
# branco parece bug de layout, e uma linha pontilhada num PDF já entregue ao
# cliente convida a preencher depois.
def _ou_pendente(variavel: str, rotulo: str) -> str:
    return os.getenv(variavel) or f"[{rotulo} a informar]"


# client_url = onde o carwash-front roda. Serve para o CORS (app.py) e para
# montar o link do e-mail de recuperação de senha. Em dev é o Vite; em produção
# vem do .env, para não deixar domínio chumbado no código.
#
# contratada = a qualificação da empresa no cabeçalho do termo de adesão
# (src/use_cases/lavagem/contrato.py). Fica aqui, e não chumbada no texto, porque
# CNPJ e RG mudam de ambiente para ambiente: o .env de dev não pode ter os
# documentos reais do Claudemir.
config = {
    "client_url": "http://localhost:5173"
    if os.getenv("ENVIRONMENT") == "dev"
    else os.getenv("CLIENT_URL", "http://localhost:5173"),

    "contratada": {
        "razao_social": os.getenv("EMPRESA_RAZAO_SOCIAL") or "LAVA-RÁPIDO NOGUEIRA",
        "cnpj": _ou_pendente("EMPRESA_CNPJ", "CNPJ"),
        # Só o que vem depois de "Rua" — o bairro e a cidade já estão no texto
        # do contrato ("..., Moema, São Paulo/SP").
        "sede_rua": _ou_pendente("EMPRESA_SEDE_RUA", "endereço da sede"),
        "representante": _ou_pendente("REPRESENTANTE_LEGAL", "representante legal"),
        "representante_rg": _ou_pendente("REPRESENTANTE_RG", "RG"),
        "representante_cpf": _ou_pendente("REPRESENTANTE_CPF", "CPF"),
        "representante_domicilio": _ou_pendente("REPRESENTANTE_DOMICILIO", "domicílio"),
    },
}
