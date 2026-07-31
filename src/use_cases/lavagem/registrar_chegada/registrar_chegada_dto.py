from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from uuid import UUID

from utils.normalizar_texto import cpf_valido, normalizar_cpf


class RegistrarChegadaDTO(BaseModel):
    """Só o CPF é exigido; o resto entra depois.

    O carro precisa entrar no pátio primeiro — exigir cadastro completo na
    chegada empurraria o atendente de volta para o papel, que é justamente o
    problema que a plataforma resolve. Mas sem CPF a lavagem não tem dono: nome
    falta em 14% da base e telefone só existe para quem passou pelo WhatsApp.
    """

    model_config = ConfigDict(extra="forbid")

    cpf: str

    # Presente quando a chegada sai da aba de agendamentos; ausente é walk-in.
    agendamento_id: Optional[UUID] = None

    nome_cliente: Optional[str] = None
    telefone: Optional[str] = None
    placa: Optional[str] = None
    tipo_carro: Optional[str] = None
    modelo_carro: Optional[str] = None
    servico: Optional[str] = None
    funcionario_lavagem_id: Optional[int] = None
    observacoes: Optional[str] = None
    danos_vistoria: Optional[list[str]] = None

    # Veículo que o atendente escolheu na lista do cliente. Sem ele, o carro é
    # procurado pela placa, como antes.
    veiculo_id: Optional[int] = None

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, valor: str) -> str:
        """Guarda os dígitos, e só depois de conferir o verificador.

        Um dígito trocado não daria erro nenhum adiante: daria um cliente novo
        em silêncio, ao lado do certo, e o histórico da pessoa se partiria em
        dois sem ninguém perceber.
        """
        if not cpf_valido(valor):
            raise ValueError("CPF inválido")
        return normalizar_cpf(valor)
