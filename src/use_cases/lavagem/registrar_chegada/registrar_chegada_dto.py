from pydantic import BaseModel, ConfigDict
from typing import Optional


class RegistrarChegadaDTO(BaseModel):
    """Tudo opcional de propósito: o carro entra no pátio primeiro, os dados vêm
    depois. Exigir cadastro completo na chegada empurraria o atendente de volta
    para o papel — que é justamente o problema que a plataforma resolve."""

    model_config = ConfigDict(extra="forbid")

    nome_cliente: Optional[str] = None
    telefone: Optional[str] = None
    placa: Optional[str] = None
    tipo_carro: Optional[str] = None
    modelo_carro: Optional[str] = None
    servico: Optional[str] = None
    funcionario_lavagem_id: Optional[int] = None
    observacoes: Optional[str] = None
