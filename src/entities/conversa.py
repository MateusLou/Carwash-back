from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal
from datetime import datetime, timezone, timedelta

StatusConversa = Literal["bot", "humano"]

# Espelha a variável HORAS_PAUSA do nó "Verificar Modo Humano" no n8n: depois de
# transferir para um atendente, o bot fica em silêncio por esse tempo e volta a
# responder sozinho. Se mudar lá, mude aqui.
HORAS_PAUSA = 2


class Conversa(BaseModel):
    """O estado de uma conversa: atendida pelo bot ou transferida para humano."""

    model_config = ConfigDict(from_attributes=True)

    telefone: str
    status: StatusConversa = "bot"
    motivo: Optional[str] = None
    atualizado_em: Optional[datetime] = None

    def esta_em_modo_humano(self, agora: Optional[datetime] = None) -> bool:
        """True enquanto o atendente humano ainda tem a conversa nas mãos.

        Não basta olhar o status: a transferência expira sozinha depois de
        HORAS_PAUSA. Uma linha com status='humano' de ontem já voltou a ser
        atendida pelo bot, mesmo sem ninguém ter mexido no banco.
        """
        if self.status != "humano" or self.atualizado_em is None:
            return False

        agora = agora or datetime.now(timezone.utc)

        # atualizado_em vem como timestamptz (aware); se algum caminho entregar
        # naive, assume UTC para a subtração não estourar.
        atualizado_em = self.atualizado_em
        if atualizado_em.tzinfo is None:
            atualizado_em = atualizado_em.replace(tzinfo=timezone.utc)
        if agora.tzinfo is None:
            agora = agora.replace(tzinfo=timezone.utc)

        return agora - atualizado_em < timedelta(hours=HORAS_PAUSA)
