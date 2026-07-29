from repositories.lavagem_repository import LavagemRepository
from use_cases.lavagem.avancar_status_lavagem.avancar_status_lavagem_dto import (
    AvancarStatusLavagemDTO,
)
from entities.lavagem import (
    Lavagem, CARIMBO_POR_STATUS, TRECHO_POR_STATUS, TRANSICOES_PERMITIDAS, minutos_entre,
)
from fastapi import Response
from datetime import datetime, timezone


class AvancarStatusLavagemUseCase:
    """Move o carro de uma etapa para a próxima.

    Cada transição faz duas coisas: carimba o horário do momento e **fecha a
    duração do trecho que terminou**. É esse cálculo que faz a lavagem
    registrada hoje ter os mesmos campos de tempo que as 37 mil importadas — e
    por isso as duas aparecem juntas no mesmo gráfico.
    """

    def __init__(self, lavagem_repository: LavagemRepository):
        self.lavagem_repository = lavagem_repository

    def execute(self, lavagem_id: int, avancar_dto: AvancarStatusLavagemDTO, response: Response):
        lavagem_model = self.lavagem_repository.get_by_id(lavagem_id)

        if lavagem_model is None:
            response.status_code = 404
            return {"status": "error", "message": "Lavagem não encontrada"}

        lavagem = Lavagem.model_validate(lavagem_model)
        novo_status = avancar_dto.novo_status

        if not lavagem.pode_mudar_para(novo_status):
            permitidos = TRANSICOES_PERMITIDAS.get(lavagem.status, ())
            response.status_code = 409
            return {
                "status": "error",
                "message": (
                    f"Não dá para ir de '{lavagem.status}' para '{novo_status}'. "
                    + (
                        f"A partir de '{lavagem.status}', só: {', '.join(permitidos)}."
                        if permitidos
                        else f"'{lavagem.status}' é um estado final."
                    )
                ),
            }

        agora = datetime.now(timezone.utc)

        campo_carimbo = CARIMBO_POR_STATUS.get(novo_status)
        if campo_carimbo:
            setattr(lavagem_model, campo_carimbo, agora)

        trecho = TRECHO_POR_STATUS.get(novo_status)
        if trecho:
            campo_inicio, campo_fim, campo_duracao = trecho
            duracao = minutos_entre(
                getattr(lavagem_model, campo_inicio), getattr(lavagem_model, campo_fim)
            )
            # None quando a linha veio da importação e não tem carimbo de início:
            # nesse caso a duração que já está lá é a da planilha, e sobrescrever
            # com nada apagaria o dado.
            if duracao is not None:
                setattr(lavagem_model, campo_duracao, duracao)

        lavagem_model.status = novo_status
        lavagem_model.atualizado_em = agora
        self.lavagem_repository.salvar(lavagem_model)

        return {
            "status": "success",
            "message": f"Lavagem em '{novo_status}'",
            "data": Lavagem.com_nomes(lavagem_model),
        }
