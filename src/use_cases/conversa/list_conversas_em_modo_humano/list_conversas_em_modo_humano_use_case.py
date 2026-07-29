from repositories.conversa_repository import ConversaRepository
from entities.conversa import Conversa, HORAS_PAUSA
from fastapi import Response


class ListConversasEmModoHumanoUseCase:
    """Quem está esperando um atendente humano agora.

    O bot marca status='humano' quando não sabe responder e fica em silêncio por
    HORAS_PAUSA. Passado esse tempo ele volta a atender sozinho — então a lista
    útil para o painel é só a das transferências ainda dentro da janela.
    """

    conversa_repository: ConversaRepository

    def __init__(self, conversa_repository: ConversaRepository):
        self.conversa_repository = conversa_repository

    def execute(self, response: Response):
        transferidas = self.conversa_repository.list_by_status("humano")

        conversas = [Conversa.model_validate(c) for c in transferidas]
        aguardando = [c for c in conversas if c.esta_em_modo_humano()]

        return {
            "status": "success",
            "horas_pausa": HORAS_PAUSA,
            "total": len(aguardando),
            "data": aguardando,
        }
