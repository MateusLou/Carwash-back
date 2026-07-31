from sqlalchemy.orm import Session
from sqlalchemy import func
from repositories.base_repository import BaseRepository
from models.agendamento_model import AgendamentoModel
from datetime import date, time
from typing import Optional
from uuid import UUID


class AgendamentoRepository(BaseRepository[AgendamentoModel]):
    """Única camada que escreve query sobre a tabela de agendamentos."""

    def __init__(self, session: Session):
        super().__init__(session, AgendamentoModel)

    def get_by_id(self, agendamento_id: UUID) -> AgendamentoModel | None:
        return self.session.query(self.model).filter(self.model.id == agendamento_id).first()

    def _aplicar_filtros(
        self,
        query,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        status: Optional[str] = None,
        servico: Optional[str] = None,
    ):
        if data_inicio is not None:
            query = query.filter(self.model.data_agendamento >= data_inicio)
        if data_fim is not None:
            query = query.filter(self.model.data_agendamento <= data_fim)
        if status is not None:
            query = query.filter(self.model.status == status)
        if servico is not None:
            query = query.filter(self.model.servico == servico)
        return query

    def list_by_filtros(
        self,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        status: Optional[str] = None,
        servico: Optional[str] = None,
    ) -> list[AgendamentoModel]:
        """Agendamentos do período, do mais próximo para o mais distante."""
        query = self._aplicar_filtros(
            self.session.query(self.model), data_inicio, data_fim, status, servico
        )
        return query.order_by(self.model.data_agendamento, self.model.horario).all()

    def count_by_status(
        self, data_inicio: Optional[date] = None, data_fim: Optional[date] = None
    ) -> dict[str, int]:
        rows = (
            self._aplicar_filtros(
                self.session.query(self.model.status, func.count()), data_inicio, data_fim
            )
            .group_by(self.model.status)
            .all()
        )
        return {status: total for status, total in rows}

    def count_by_servico(
        self, data_inicio: Optional[date] = None, data_fim: Optional[date] = None
    ) -> dict[str, int]:
        rows = (
            self._aplicar_filtros(
                self.session.query(self.model.servico, func.count()), data_inicio, data_fim
            )
            .group_by(self.model.servico)
            .order_by(func.count().desc())
            .all()
        )
        return {servico: total for servico, total in rows}

    def count_by_dia(
        self,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        sem_cancelados: bool = False,
    ) -> list[tuple[date, int]]:
        """Série diária para o gráfico do dashboard.

        `sem_cancelados` segue a regra de `Agendamento.ocupa_vaga()`: na visão
        de agenda, cancelado não é trabalho que vem aí.
        """
        query = self._aplicar_filtros(
            self.session.query(self.model.data_agendamento, func.count()),
            data_inicio,
            data_fim,
        )
        if sem_cancelados:
            query = query.filter(self.model.status != "cancelado")
        return (
            query.group_by(self.model.data_agendamento)
            .order_by(self.model.data_agendamento)
            .all()
        )

    def contar_ocupacao_por_slot(
        self, data_inicio: Optional[date] = None, data_fim: Optional[date] = None
    ) -> list[tuple[date, time, int]]:
        """Quantos carros já estão marcados em cada slot.

        É a view vw_ocupacao_slots (supabase/schema.sql) reescrita aqui — a
        mesma contagem que o bot usa para oferecer só horário livre. Cancelados
        não ocupam vaga.
        """
        return (
            self._aplicar_filtros(
                self.session.query(
                    self.model.data_agendamento, self.model.horario, func.count()
                ),
                data_inicio,
                data_fim,
            )
            .filter(self.model.status != "cancelado")
            .group_by(self.model.data_agendamento, self.model.horario)
            .order_by(self.model.data_agendamento, self.model.horario)
            .all()
        )

    def update_status(self, agendamento: AgendamentoModel, novo_status: str) -> AgendamentoModel:
        agendamento.status = novo_status
        self.session.commit()
        self.session.refresh(agendamento)
        return agendamento
