from repositories.lavagem_repository import LavagemRepository
from use_cases.dashboard.periodo_dto import PeriodoDTO
from entities.lavagem import calcular_nps
from fastapi import Response


class GetResumoUseCase:
    """Os cards do topo do painel, num request só.

    Reúne as cinco famílias que o case pede — clientes atendidos, vendas, tempos,
    produtividade e satisfação — em um número cada. O detalhe de cada uma fica
    nos outros três endpoints.
    """

    def __init__(self, lavagem_repository: LavagemRepository):
        self.lavagem_repository = lavagem_repository

    def execute(self, periodo: PeriodoDTO, response: Response):
        erro = periodo.invalido()
        if erro:
            response.status_code = 422
            return {"status": "error", "message": erro}

        resumo = self.lavagem_repository.resumo(periodo.data_inicio, periodo.data_fim)
        nps = self.lavagem_repository.contagem_nps(periodo.data_inicio, periodo.data_fim)
        google = self.lavagem_repository.resumo_nota_google(periodo.data_inicio, periodo.data_fim)

        return {
            "status": "success",
            "data": {
                **resumo,
                "nps": calcular_nps(nps["promotores"], nps["detratores"], nps["respostas"]),
                # o n vai junto porque 43% das lavagens não têm NPS: um NPS
                # calculado sobre 12 respostas não vale o mesmo que sobre 12 mil
                "nps_respostas": nps["respostas"],
                "nota_google_media": google["media"],
                "nota_google_respostas": google["n"],
            },
            # o front usa isso para abrir num período que tem dado, em vez de
            # numa tela vazia quando a base importada termina meses atrás
            "periodo_disponivel": self.lavagem_repository.periodo_disponivel(),
        }
