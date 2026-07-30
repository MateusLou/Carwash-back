from repositories.lavagem_repository import LavagemRepository
from use_cases.lavagem.vistoria.vistoria_dto import SalvarVistoriaDTO
from fastapi import HTTPException, Response
from datetime import datetime, timezone


class SalvarVistoriaUseCase:

    def __init__(self, lavagem_repository: LavagemRepository):
        self.lavagem_repository = lavagem_repository

    def execute(self, lavagem_id: int, dto: SalvarVistoriaDTO, response: Response):
        lavagem = self.lavagem_repository.get_by_id(lavagem_id)
        if not lavagem:
            raise HTTPException(status_code=404, detail="Lavagem não encontrada.")

        dados = dict(lavagem.dados_extras or {})
        dados["vistoria"] = {
            "danos": dto.danos,
            "registrada_em": datetime.now(timezone.utc).isoformat(),
        }
        self.lavagem_repository.update_entity(lavagem, {"dados_extras": dados})

        return {"status": "success", "data": dados["vistoria"]}


class GetVistoriaUseCase:

    def __init__(self, lavagem_repository: LavagemRepository):
        self.lavagem_repository = lavagem_repository

    def execute(self, lavagem_id: int, response: Response):
        lavagem = self.lavagem_repository.get_by_id(lavagem_id)
        if not lavagem:
            raise HTTPException(status_code=404, detail="Lavagem não encontrada.")

        vistoria = (lavagem.dados_extras or {}).get("vistoria")
        return {
            "status": "success",
            "data": vistoria or {"danos": [], "registrada_em": None},
        }
