from sqlalchemy import Column, Text, CheckConstraint, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from database.database import Base


class ConversaModel(Base):
    """Espelho da tabela public.conversas do Supabase.

    Controla o "modo humano": quando o bot não sabe responder, ele grava
    status='humano' aqui e para de responder aquele contato. Tabela já existente
    (supabase/schema.sql) — mantenha as colunas idênticas.
    """

    __tablename__ = "conversas"

    telefone = Column(Text, primary_key=True)
    status = Column(Text, nullable=False, server_default=text("'bot'"))
    motivo = Column(Text, nullable=True)
    atualizado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        CheckConstraint("status in ('bot','humano')", name="conversas_status_check"),
    )

    def __repr__(self):
        return f"<Conversa(telefone={self.telefone}, status={self.status})>"
