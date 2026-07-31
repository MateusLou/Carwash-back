from fastapi import Response

from models.importacao_model import ImportacaoModel
from repositories.importacao_repository import ImportacaoRepository

# O arquivo oficial tem 4,3 MB com 12 anos de operação — 20 MB é folga de
# décadas, e um teto evita que um upload errado (um vídeo, um zip gigante)
# ocupe memória à toa.
TAMANHO_MAXIMO_BYTES = 20 * 1024 * 1024

# Todo .xlsx é um zip, e todo zip começa com estes 4 bytes. O parse completo
# fica para o background — abrir o workbook aqui atrasaria a resposta.
ASSINATURA_ZIP = b"PK\x03\x04"


class UploadPlanilhaUseCase:
    """Recebe o .xlsx do dono e agenda a carga.

    A regra de negócio aqui é curta: validar o arquivo o suficiente para
    recusar rápido o que nunca daria certo, garantir que não há outra carga
    rodando, e registrar o job que o polling do front vai acompanhar. A carga
    em si é do motor, em background — 27 mil linhas contra o Supabase levam
    mais de um minuto, e um request preso esse tempo todo cairia em qualquer
    gateway.
    """

    def __init__(self, importacao_repository: ImportacaoRepository):
        self.importacao_repository = importacao_repository

    def execute(self, nome_arquivo: str | None, conteudo: bytes, response: Response) -> dict:
        nome = nome_arquivo or "planilha.xlsx"

        if not nome.lower().endswith(".xlsx"):
            response.status_code = 400
            return {"status": "error", "message": "Envie um arquivo .xlsx"}

        if len(conteudo) > TAMANHO_MAXIMO_BYTES:
            response.status_code = 413
            return {"status": "error", "message": "Arquivo maior que 20 MB"}

        if not conteudo.startswith(ASSINATURA_ZIP):
            response.status_code = 400
            return {"status": "error", "message": "O arquivo não é um .xlsx válido"}

        # Destrava jobs órfãos de um reinício antes de conferir o guard —
        # senão um 'processando' fantasma bloquearia uploads para sempre.
        self.importacao_repository.expirar_orfas()
        if self.importacao_repository.em_processamento() is not None:
            response.status_code = 409
            return {
                "status": "error",
                "message": "Já existe uma importação em andamento — aguarde ela terminar",
            }

        importacao = self.importacao_repository.add(
            ImportacaoModel(arquivo=nome, aba=None, status="processando")
        )

        response.status_code = 202
        return {
            "status": "success",
            "message": "Importação iniciada",
            "data": {"importacao_id": importacao.id},
        }
