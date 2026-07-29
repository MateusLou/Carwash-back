from pydantic import BaseModel, ConfigDict
from entities.lavagem import StatusLavagem


class AvancarStatusLavagemDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    novo_status: StatusLavagem
