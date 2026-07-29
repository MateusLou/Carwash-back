from repositories.lavagem_repository import LavagemRepository
from use_cases.dashboard.periodo_dto import PeriodoDTO
from entities.lavagem import calcular_nps
from fastapi import Response


class GetMetricasSatisfacaoUseCase:
    """NPS e nota do Google.

    Duas cautelas embutidas na resposta, porque sem elas o número engana:

    1. **`respostas` sempre acompanha o indicador.** O NPS falta em 43% das
       lavagens e a nota do Google em 55%. Um NPS sobre 30 respostas não pesa o
       mesmo que sobre 3 mil, e o gráfico sozinho não mostra a diferença.
    2. **Nulo nunca vira zero.** Sem resposta, o indicador vem `null` — tratar
       ausência como nota mínima inventaria uma insatisfação que ninguém relatou.
    """

    def __init__(self, lavagem_repository: LavagemRepository):
        self.lavagem_repository = lavagem_repository

    def execute(self, periodo: PeriodoDTO, response: Response):
        erro = periodo.invalido()
        if erro:
            response.status_code = 422
            return {"status": "error", "message": erro}

        nps = self.lavagem_repository.contagem_nps(periodo.data_inicio, periodo.data_fim)
        google = self.lavagem_repository.resumo_nota_google(periodo.data_inicio, periodo.data_fim)

        return {
            "status": "success",
            "data": {
                "nps": calcular_nps(nps["promotores"], nps["detratores"], nps["respostas"]),
                "respostas": nps["respostas"],
                "distribuicao": {
                    "promotores": nps["promotores"],
                    "neutros": nps["neutros"],
                    "detratores": nps["detratores"],
                },
                "nota_media": nps["nota_media"],
                "nota_google": google,
                "serie": self.lavagem_repository.serie_nps(
                    periodo.granularidade, periodo.data_inicio, periodo.data_fim
                ),
            },
        }
