from repositories.agendamento_repository import AgendamentoRepository
from use_cases.agendamento.get_metricas_dashboard.get_metricas_dashboard_dto import (
    GetMetricasDashboardDTO,
)
from entities.agendamento import STATUS_VALIDOS
from fastapi import Response


class GetMetricasDashboardUseCase:
    """Os números do topo do dashboard, num request só."""

    agendamento_repository: AgendamentoRepository

    def __init__(self, agendamento_repository: AgendamentoRepository):
        self.agendamento_repository = agendamento_repository

    def execute(self, get_metricas_dto: GetMetricasDashboardDTO, response: Response):
        if (
            get_metricas_dto.data_inicio
            and get_metricas_dto.data_fim
            and get_metricas_dto.data_inicio > get_metricas_dto.data_fim
        ):
            response.status_code = 422
            return {"status": "error", "message": "A data inicial é posterior à data final"}

        data_inicio = get_metricas_dto.data_inicio
        data_fim = get_metricas_dto.data_fim

        por_status = self.agendamento_repository.count_by_status(data_inicio, data_fim)
        por_servico = self.agendamento_repository.count_by_servico(data_inicio, data_fim)
        por_dia = self.agendamento_repository.count_by_dia(data_inicio, data_fim)

        # Status sem nenhum agendamento não vem do group by, mas o dashboard
        # precisa do zero para não deixar buraco no gráfico.
        por_status_completo = {status: por_status.get(status, 0) for status in STATUS_VALIDOS}

        total = sum(por_status_completo.values())
        cancelados = por_status_completo["cancelado"]

        return {
            "status": "success",
            "data": {
                "total": total,
                "total_ativos": total - cancelados,
                "taxa_cancelamento": round(cancelados / total, 4) if total else 0.0,
                "por_status": por_status_completo,
                "por_servico": por_servico,
                "por_dia": [
                    {"data": dia.isoformat(), "total": quantidade} for dia, quantidade in por_dia
                ],
            },
        }
