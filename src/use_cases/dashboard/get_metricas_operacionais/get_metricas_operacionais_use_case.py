from repositories.lavagem_repository import LavagemRepository, DURACOES, ETAPAS
from use_cases.dashboard.periodo_dto import PeriodoDTO
from fastapi import Response

# Rótulos legíveis para a tela. O nome técnico vai junto, para quem for conferir
# contra a planilha saber exatamente de qual coluna se trata.
ROTULOS = {
    "tempo_espera_antes_lavagem_min": "Espera até começar",
    "tempo_lavagem_total_min": "Lavagem",
    "tempo_pos_lavagem_ate_retirada_min": "Pronto até o cliente buscar",
    "tempo_ate_pagamento_min": "Até o pagamento",
    "t_teto_vidros_min": "Teto e vidros",
    "t_capo_parabrisa_min": "Capô e parabrisa",
    "t_laterais_portas_min": "Laterais e portas",
    "t_traseira_min": "Traseira",
    "t_rodas_pneus_min": "Rodas e pneus",
    "t_interior_min": "Interior",
}


class GetMetricasOperacionaisUseCase:
    """Tempos e produtividade — o "como a casa roda"."""

    def __init__(self, lavagem_repository: LavagemRepository):
        self.lavagem_repository = lavagem_repository

    def execute(self, periodo: PeriodoDTO, response: Response):
        erro = periodo.invalido()
        if erro:
            response.status_code = 422
            return {"status": "error", "message": erro}

        tempos = self.lavagem_repository.tempos(periodo.data_inicio, periodo.data_fim)
        for item in tempos:
            item["rotulo"] = ROTULOS.get(item["metrica"], item["metrica"])

        return {
            "status": "success",
            "data": {
                # separados porque respondem perguntas diferentes: as durações
                # são a experiência do cliente, as etapas são o processo interno
                "duracoes": [t for t in tempos if t["metrica"] in DURACOES],
                "etapas": [t for t in tempos if t["metrica"] in ETAPAS],
                "produtividade": self.lavagem_repository.produtividade_por_funcionario(
                    periodo.data_inicio, periodo.data_fim
                ),
                "serie": self.lavagem_repository.serie_por_periodo(
                    periodo.granularidade, periodo.data_inicio, periodo.data_fim
                ),
            },
        }
