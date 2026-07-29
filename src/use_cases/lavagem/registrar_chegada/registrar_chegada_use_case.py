from repositories.lavagem_repository import LavagemRepository
from repositories.cliente_repository import ClienteRepository
from repositories.veiculo_repository import VeiculoRepository
from use_cases.lavagem.registrar_chegada.registrar_chegada_dto import RegistrarChegadaDTO
from models.lavagem_model import LavagemModel
from entities.lavagem import Lavagem
from fastapi import Response
from datetime import datetime, timezone


class RegistrarChegadaUseCase:
    """O check-in: o carro chegou.

    É aqui que telefone e placa entram no banco pela primeira vez — a base
    histórica não tem nenhum dos dois. O horário de chegada é carimbado agora, e
    é dele que sai o tempo de espera quando a lavagem começar.
    """

    def __init__(
        self,
        lavagem_repository: LavagemRepository,
        cliente_repository: ClienteRepository,
        veiculo_repository: VeiculoRepository,
    ):
        self.lavagem_repository = lavagem_repository
        self.cliente_repository = cliente_repository
        self.veiculo_repository = veiculo_repository

    def execute(self, chegada_dto: RegistrarChegadaDTO, response: Response):
        agora = datetime.now(timezone.utc)

        cliente = self.cliente_repository.get_or_create(
            nome=chegada_dto.nome_cliente, telefone=chegada_dto.telefone
        )
        veiculo = self.veiculo_repository.get_or_create(
            placa=chegada_dto.placa,
            cliente_id=cliente.id if cliente else None,
            tipo=chegada_dto.tipo_carro,
            modelo=chegada_dto.modelo_carro,
        )

        lavagem = LavagemModel(
            origem="plataforma",
            status="aguardando",
            data=agora.date(),
            chegou_em=agora,
            cliente_id=cliente.id if cliente else None,
            veiculo_id=veiculo.id if veiculo else None,
            # tipo_carro fica na própria lavagem além de no veículo: é o que
            # mantém a métrica por porte funcionando para quem chega sem placa
            tipo_carro=chegada_dto.tipo_carro or (veiculo.tipo if veiculo else None),
            funcionario_lavagem_id=chegada_dto.funcionario_lavagem_id,
            observacoes=chegada_dto.observacoes,
        )
        if chegada_dto.servico:
            lavagem.servico = chegada_dto.servico

        self.lavagem_repository.add(lavagem)

        response.status_code = 201
        return {
            "status": "success",
            "message": "Chegada registrada",
            "data": Lavagem.com_nomes(lavagem),
        }
