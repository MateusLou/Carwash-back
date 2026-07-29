from sqlalchemy.orm import Session
from repositories.base_repository import BaseRepository
from models.conversa_model import ConversaModel


class ConversaRepository(BaseRepository[ConversaModel]):
    """Única camada que escreve query sobre a tabela de conversas."""

    def __init__(self, session: Session):
        super().__init__(session, ConversaModel)

    def get_by_telefone(self, telefone: str) -> ConversaModel | None:
        return self.session.query(self.model).filter(self.model.telefone == telefone).first()

    def list_by_status(self, status: str) -> list[ConversaModel]:
        """Conversas com aquele status, da transferência mais recente para a mais antiga.

        Devolve tudo que está marcado como 'humano', inclusive transferências
        antigas — quem decide se a pausa ainda vale é a entity Conversa, que
        conhece a regra das horas. Aqui é só query.
        """
        return (
            self.session.query(self.model)
            .filter(self.model.status == status)
            .order_by(self.model.atualizado_em.desc())
            .all()
        )
