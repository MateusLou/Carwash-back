from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal, get_args
from datetime import date, time, datetime
from uuid import UUID

StatusAgendamento = Literal["pendente", "confirmado", "concluido", "cancelado"]

STATUS_VALIDOS: tuple[str, ...] = get_args(StatusAgendamento)

# Regra de negócio: o agendamento anda para frente. Concluído e cancelado são
# pontos finais — para voltar atrás, cria-se um agendamento novo.
TRANSICOES_PERMITIDAS: dict[str, tuple[str, ...]] = {
    "pendente": ("confirmado", "cancelado"),
    "confirmado": ("concluido", "cancelado"),
    "concluido": (),
    "cancelado": (),
}


class Agendamento(BaseModel):
    """Um agendamento do lava-rápido, do ponto de vista do negócio.

    É o mesmo conceito que o bot do WhatsApp cria no Supabase — aqui ele aparece
    sem nada de banco ou HTTP, só a ideia e as regras que valem sobre ela.
    """

    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    # dados do cliente
    nome_cliente: Optional[str] = None
    telefone: str

    # dados do veículo
    placa: Optional[str] = None
    modelo_carro: Optional[str] = None

    # dados do serviço
    servico: str = "Lavagem completa"
    data_agendamento: date
    horario: time

    # controle
    status: StatusAgendamento = "pendente"
    observacoes: Optional[str] = None

    def pode_mudar_para(self, novo_status: str) -> bool:
        """Diz se a mudança de status faz sentido a partir do estado atual."""
        return novo_status in TRANSICOES_PERMITIDAS.get(self.status, ())

    def ocupa_vaga(self) -> bool:
        """Cancelado não conta na ocupação do slot — mesma regra da view
        vw_ocupacao_slots que o bot consulta para oferecer horário livre."""
        return self.status != "cancelado"
