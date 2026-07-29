from repositories.lavagem_repository import LavagemRepository
from entities.lavagem import Lavagem, STATUS_ABERTOS, minutos_entre
from fastapi import Response
from datetime import datetime, timezone


class GetPatioUseCase:
    """O que está no pátio agora.

    Junto de cada carro vai `parado_ha_min`, o tempo desde o último carimbo. É o
    número que o case pede sem nomear: "a casa não dá conta e chega a recusar
    clientes" — quem está esperando há 40 minutos precisa aparecer antes de
    virar reclamação.
    """

    def __init__(self, lavagem_repository: LavagemRepository):
        self.lavagem_repository = lavagem_repository

    def execute(self, response: Response):
        agora = datetime.now(timezone.utc)
        lavagens = self.lavagem_repository.list_patio()

        # o carimbo mais recente de cada etapa é o marco de "parado desde"
        ultimo_carimbo = {
            "aguardando": "chegou_em",
            "em_lavagem": "iniciou_lavagem_em",
            "pronta": "terminou_lavagem_em",
        }

        itens = []
        for modelo in lavagens:
            desde = getattr(modelo, ultimo_carimbo[modelo.status], None)
            itens.append(
                {
                    **Lavagem.com_nomes(modelo).model_dump(),
                    "parado_ha_min": minutos_entre(desde, agora),
                }
            )

        por_status = {status: 0 for status in STATUS_ABERTOS}
        for modelo in lavagens:
            por_status[modelo.status] += 1

        return {
            "status": "success",
            "total": len(itens),
            "por_status": por_status,
            "data": itens,
        }
