from repositories.cliente_repository import ClienteRepository
from repositories.veiculo_repository import VeiculoRepository
from entities.cliente import Cliente, ClienteComVeiculos
from entities.veiculo import Veiculo
from utils.normalizar_texto import cpf_valido
from fastapi import Response


class GetClientePorCpfUseCase:
    """Quem é o dono deste CPF, e que carros ele já trouxe.

    É o que o check-in chama assim que o atendente termina de digitar o CPF: o
    404 é resposta boa, significa cliente novo, e é ele que faz a tela parar de
    esperar e deixar o atendente preencher a ficha do zero.
    """

    def __init__(
        self,
        cliente_repository: ClienteRepository,
        veiculo_repository: VeiculoRepository,
    ):
        self.cliente_repository = cliente_repository
        self.veiculo_repository = veiculo_repository

    def execute(self, cpf: str, response: Response):
        if not cpf_valido(cpf):
            response.status_code = 422
            return {"status": "error", "message": "CPF inválido"}

        cliente = self.cliente_repository.get_by_cpf(cpf)
        if cliente is None:
            response.status_code = 404
            return {"status": "error", "message": "Cliente não cadastrado"}

        veiculos = self.veiculo_repository.list_by_cliente(cliente.id)
        base = Cliente.model_validate(cliente)
        return {
            "status": "success",
            "data": ClienteComVeiculos(
                **base.model_dump(),
                veiculos=[Veiculo.model_validate(v) for v in veiculos],
            ),
        }
