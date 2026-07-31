from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
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

    def upsert_em_lote_por_nome(self, nomes: set[str]) -> dict[str, int]:
        """Garante que cada nome exista e devolve nome_normalizado → id.

        Três queries em vez de um get_or_create por linha — a importação junta
        os lavadores e atendentes de todas as abas e resolve tudo de uma vez
        (funcionário novo numa aba nova entra aqui sozinho).

        NÃO comita: a importação em modo substituir precisa de uma transação
        única para a falha devolver o banco inteiro ao estado anterior.
        """
        normalizados = {
            normalizar_texto(str(n)): str(n).strip() for n in nomes if n and str(n).strip()
        }
        if not normalizados:
            return {}

        consulta = select(self.model.nome_normalizado, self.model.id).where(
            self.model.nome_normalizado.in_(list(normalizados))
        )
        existentes = dict(self.session.execute(consulta).all())

        faltando = [
            {"nome": original, "nome_normalizado": chave}
            for chave, original in normalizados.items()
            if chave not in existentes
        ]
        if faltando:
            self.session.execute(pg_insert(self.model).values(faltando).on_conflict_do_nothing())
            existentes = dict(self.session.execute(consulta).all())
        return existentes
