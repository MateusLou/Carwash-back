from repositories.lavagem_repository import LavagemRepository
from use_cases.lavagem.registrar_pagamento.registrar_pagamento_dto import RegistrarPagamentoDTO
from entities.lavagem import Lavagem, minutos_entre
from fastapi import Response
from datetime import datetime, timezone


class RegistrarPagamentoUseCase:
    """Fecha a conta: preço, forma de pagamento e, se o cliente responder, o NPS.

    Separado do avanço de status porque as duas coisas não acontecem juntas — o
    carro pode ser pago antes de o dono buscar, e há o fiado/mensal, que é 8,5%
    da base.
    """

    def __init__(self, lavagem_repository: LavagemRepository):
        self.lavagem_repository = lavagem_repository

    def execute(self, lavagem_id: int, pagamento_dto: RegistrarPagamentoDTO, response: Response):
        lavagem_model = self.lavagem_repository.get_by_id(lavagem_id)

        if lavagem_model is None:
            response.status_code = 404
            return {"status": "error", "message": "Lavagem não encontrada"}

        if lavagem_model.status == "cancelada":
            response.status_code = 409
            return {"status": "error", "message": "Lavagem cancelada não recebe pagamento"}

        agora = datetime.now(timezone.utc)

        lavagem_model.preco_reais = pagamento_dto.preco_reais
        lavagem_model.metodo_pagamento = pagamento_dto.metodo_pagamento
        lavagem_model.cnpj_receita = pagamento_dto.cnpj_receita
        lavagem_model.atendente_pagamento_id = pagamento_dto.atendente_pagamento_id
        lavagem_model.nps_cliente = pagamento_dto.nps_cliente
        lavagem_model.pago_em = agora

        # Mede do fim da lavagem até o pagamento — mesma leitura que damos à
        # coluna `tempo_ate_pagamento_min` da planilha. Vale confirmar essa
        # definição quando a base definitiva chegar.
        duracao = minutos_entre(lavagem_model.terminou_lavagem_em, agora)
        if duracao is not None:
            lavagem_model.tempo_ate_pagamento_min = duracao

        lavagem_model.atualizado_em = agora
        self.lavagem_repository.salvar(lavagem_model)

        return {
            "status": "success",
            "message": "Pagamento registrado",
            "data": Lavagem.com_nomes(lavagem_model),
        }
