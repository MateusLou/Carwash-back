from pydantic import BaseModel, ConfigDict
from entities.agendamento import StatusAgendamento


class UpdateStatusAgendamentoDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    novo_status: StatusAgendamento
