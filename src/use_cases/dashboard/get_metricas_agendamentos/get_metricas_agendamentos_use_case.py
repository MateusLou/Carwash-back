from repositories.agendamento_repository import AgendamentoRepository
from use_cases.dashboard.periodo_dto import PeriodoDTO
from entities.agendamento import STATUS_VALIDOS
from fastapi import Response
from datetime import datetime, timedelta, timezone

# O relógio do lava-rápido, o mesmo do contrato (use_cases/lavagem/contrato.py):
# o banco pensa em UTC, mas "hoje" é o dia da parede de São Paulo — às 21h de
# UTC-3 o servidor já virou o dia, a agenda do dono não.
FUSO_SAO_PAULO = timezone(timedelta(hours=-3))

# Hoje + 6: a janela que o gráfico da aba mostra.
DIAS_DA_JANELA = 7


class GetMetricasAgendamentosUseCase:
    """A agenda do WhatsApp dentro do dashboard.

    O bot marca, o dono acompanha aqui: quantos agendamentos existem, para
    quando, em que situação e de qual serviço. O período filtra pela data
    AGENDADA, não pela data em que o cliente marcou — "o que está marcado para
    esta semana?" é a pergunta, e é assim que o bot e a página de Agendamentos
    já enxergam a agenda.

    Exceção: `proximos_dias` ignora o período. É a janela fixa de hoje + 6
    dias — "o que vem aí" não muda porque o dono está olhando o mês passado.
    """

    def __init__(self, agendamento_repository: AgendamentoRepository):
        self.agendamento_repository = agendamento_repository

    def execute(self, periodo: PeriodoDTO, response: Response):
        erro = periodo.invalido()
        if erro:
            response.status_code = 422
            return {"status": "error", "message": erro}

        inicio, fim = periodo.data_inicio, periodo.data_fim

        por_status = self.agendamento_repository.count_by_status(inicio, fim)
        # Status sem nenhum agendamento não vem do group by, mas o dashboard
        # precisa do zero para o card não sumir.
        por_status = {status: por_status.get(status, 0) for status in STATUS_VALIDOS}
        total = sum(por_status.values())

        # Dia sem agendamento também não vem do group by, e aqui o zero é o
        # dado: um buraco na semana é exatamente o que o dono quer enxergar.
        # Cancelado fica de fora — mesma regra de Agendamento.ocupa_vaga().
        hoje = datetime.now(FUSO_SAO_PAULO).date()
        dias = [hoje + timedelta(days=i) for i in range(DIAS_DA_JANELA)]
        por_dia = dict(
            self.agendamento_repository.count_by_dia(
                data_inicio=hoje, data_fim=dias[-1], sem_cancelados=True
            )
        )
        proximos_dias = [
            {"data": dia.isoformat(), "total": por_dia.get(dia, 0)} for dia in dias
        ]

        return {
            "status": "success",
            "data": {
                "total": total,
                "por_status": por_status,
                "taxa_cancelamento": (
                    round(por_status["cancelado"] / total, 4) if total else 0.0
                ),
                "por_servico": [
                    {"categoria": servico, "agendamentos": quantidade}
                    for servico, quantidade in self.agendamento_repository.count_by_servico(
                        inicio, fim
                    ).items()
                ],
                "proximos_dias": proximos_dias,
            },
        }
