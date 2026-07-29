from repositories.lavagem_repository import LavagemRepository
from use_cases.dashboard.periodo_dto import PeriodoDTO
from fastapi import Response


class GetMetricasComerciaisUseCase:
    """Vendas — o "quanto entrou".

    A quebra por `cnpj_receita` não é detalhe contábil: o case tem uma frente
    inteira de análise societária sobre a empresa operar com dois CNPJs na mesma
    atividade, e este é o número que mostra quanto passa por cada um.
    """

    def __init__(self, lavagem_repository: LavagemRepository):
        self.lavagem_repository = lavagem_repository

    def execute(self, periodo: PeriodoDTO, response: Response):
        erro = periodo.invalido()
        if erro:
            response.status_code = 422
            return {"status": "error", "message": erro}

        # as quatro quebras numa consulta só — quatro chamadas seriam quatro
        # viagens até o Supabase
        dimensoes = self.lavagem_repository.por_dimensoes(
            ("metodo_pagamento", "tipo_carro", "cnpj_receita", "servico"),
            periodo.data_inicio,
            periodo.data_fim,
        )

        return {
            "status": "success",
            "data": {
                "resumo": self.lavagem_repository.resumo(periodo.data_inicio, periodo.data_fim),
                "serie": self.lavagem_repository.serie_por_periodo(
                    periodo.granularidade, periodo.data_inicio, periodo.data_fim
                ),
                "por_metodo_pagamento": dimensoes["metodo_pagamento"],
                "por_tipo_carro": dimensoes["tipo_carro"],
                "por_cnpj": dimensoes["cnpj_receita"],
                "por_servico": dimensoes["servico"],
            },
        }
