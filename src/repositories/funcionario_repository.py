from sqlalchemy.orm import Session
from repositories.base_repository import BaseRepository
from models.funcionario_model import FuncionarioModel
from utils.normalizar_texto import normalizar_texto


class FuncionarioRepository(BaseRepository[FuncionarioModel]):
    def __init__(self, session: Session):
        super().__init__(session, FuncionarioModel)

    def get_by_id(self, funcionario_id: int) -> FuncionarioModel | None:
        return self.session.query(self.model).filter(self.model.id == funcionario_id).first()

    def get_by_nome(self, nome: str) -> FuncionarioModel | None:
        return (
            self.session.query(self.model)
            .filter(self.model.nome_normalizado == normalizar_texto(nome))
            .first()
        )

    def list_ativos(self) -> list[FuncionarioModel]:
        return (
            self.session.query(self.model)
            .filter(self.model.ativo.is_(True))
            .order_by(self.model.nome)
            .all()
        )

    def get_or_create(self, nome: str) -> FuncionarioModel:
        funcionario = self.get_by_nome(nome)
        if funcionario is not None:
            return funcionario
        return self.add(FuncionarioModel(nome=nome, nome_normalizado=normalizar_texto(nome)))
