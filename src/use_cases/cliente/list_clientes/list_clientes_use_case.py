from repositories.cliente_repository import ClienteRepository
from entities.cliente import Cliente
from fastapi import Response
from typing import Optional


class ListClientesUseCase:
    """A busca do check-in: o atendente digita parte do nome ou do telefone e o
    cliente aparece, em vez de virar cadastro duplicado."""

    def __init__(self, cliente_repository: ClienteRepository):
        self.cliente_repository = cliente_repository

    def execute(self, busca: Optional[str], response: Response):
        if not busca or len(busca.strip()) < 2:
            # devolver os 3 mil clientes num autocomplete não ajudaria ninguém
            return {"status": "success", "total": 0, "data": []}

        clientes = self.cliente_repository.buscar(busca.strip())
        return {
            "status": "success",
            "total": len(clientes),
            "data": [Cliente.model_validate(c) for c in clientes],
        }
