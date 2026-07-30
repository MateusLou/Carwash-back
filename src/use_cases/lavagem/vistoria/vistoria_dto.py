from pydantic import BaseModel


class SalvarVistoriaDTO(BaseModel):
    danos: list[str]
