from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from repositories.base_repository import BaseRepository
from models.importacao_model import ImportacaoModel


class ImportacaoRepository(BaseRepository[ImportacaoModel]):
    def __init__(self, session: Session):
        super().__init__(session, ImportacaoModel)

    def get_by_id(self, importacao_id: int) -> ImportacaoModel | None:
        return self.session.query(self.model).filter(self.model.id == importacao_id).first()

    def listar(self, limite: int = 20) -> list[ImportacaoModel]:
        return (
            self.session.query(self.model)
            .order_by(self.model.iniciada_em.desc(), self.model.id.desc())
            .limit(limite)
            .all()
        )

    def em_processamento(self) -> ImportacaoModel | None:
        """A importação que está rodando agora, se houver.

        É o guard de concorrência do upload: a carga mexe na base inteira e
        duas ao mesmo tempo embaralhariam contadores e o modo substituir.
        """
        return (
            self.session.query(self.model)
            .filter(self.model.status == "processando")
            .first()
        )

    def expirar_orfas(self, minutos: int = 15) -> int:
        """Marca como erro importações 'processando' velhas demais.

        Um reinício do servidor mata o job em background sem ninguém atualizar
        o registro — e o 'processando' eterno travaria o guard de concorrência
        para sempre. Quinze minutos é folga larga: a carga completa leva ~1–2
        minutos.
        """
        limite = datetime.now(timezone.utc) - timedelta(minutes=minutos)
        expiradas = (
            self.session.query(self.model)
            .filter(self.model.status == "processando", self.model.iniciada_em < limite)
            .update(
                {
                    "status": "erro",
                    "erro": "interrompida por reinício do servidor",
                    "concluida_em": datetime.now(timezone.utc),
                },
                synchronize_session=False,
            )
        )
        if expiradas:
            self.session.commit()
        return expiradas
