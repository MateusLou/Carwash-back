from repositories.lavagem_repository import LavagemRepository
from repositories.cliente_repository import ClienteRepository
from repositories.veiculo_repository import VeiculoRepository
from repositories.agendamento_repository import AgendamentoRepository
from use_cases.lavagem.registrar_chegada.registrar_chegada_dto import RegistrarChegadaDTO
from use_cases.lavagem.contrato import emitir_contrato
from models.lavagem_model import LavagemModel
from models.agendamento_model import AgendamentoModel
from entities.lavagem import Lavagem
from entities.agendamento import Agendamento
from utils.normalizar_texto import normalizar_telefone
from fastapi import Response
from datetime import datetime, timezone


class RegistrarChegadaUseCase:
    """O check-in: o carro chegou.

    O CPF identifica o cliente; é obrigatório porque é a única chave confiável
    (nome falta em 14% da base, telefone só existe para quem passou pelo
    WhatsApp). Telefone e placa entram no banco pela primeira vez aqui — a base
    histórica não tem nenhum dos dois. O horário de chegada é carimbado agora, e
    é dele que sai o tempo de espera quando a lavagem começar.

    Dois caminhos chegam aqui: o walk-in, que preenche a ficha do zero, e a
    chegada de quem tinha agendamento — que traz `agendamento_id` e amarra a
    lavagem ao que o bot do WhatsApp marcou.
    """

    def __init__(
        self,
        lavagem_repository: LavagemRepository,
        cliente_repository: ClienteRepository,
        veiculo_repository: VeiculoRepository,
        agendamento_repository: AgendamentoRepository,
    ):
        self.lavagem_repository = lavagem_repository
        self.cliente_repository = cliente_repository
        self.veiculo_repository = veiculo_repository
        self.agendamento_repository = agendamento_repository

    def execute(self, chegada_dto: RegistrarChegadaDTO, response: Response):
        agora = datetime.now(timezone.utc)

        agendamento_model = None
        if chegada_dto.agendamento_id is not None:
            agendamento_model = self.agendamento_repository.get_by_id(
                chegada_dto.agendamento_id
            )

            if agendamento_model is None:
                response.status_code = 404
                return {"status": "error", "message": "Agendamento não encontrado"}

            if agendamento_model.status == "cancelado":
                response.status_code = 409
                return {
                    "status": "error",
                    "message": "Agendamento cancelado não recebe chegada",
                }

            ja_chegou = self.lavagem_repository.get_by_agendamento_id(
                chegada_dto.agendamento_id
            )
            if ja_chegou is not None:
                response.status_code = 409
                return {
                    "status": "error",
                    "message": "A chegada deste agendamento já foi registrada",
                }

        # O que o funcionário digitou ganha; campo em branco herda do
        # agendamento. É o telefone que amarra o cadastro ao mundo do WhatsApp,
        # e perdê-lo aqui criaria um cliente duplicado.
        dados = self._com_dados_do_agendamento(chegada_dto, agendamento_model)

        cliente = self.cliente_repository.get_or_create(
            cpf=chegada_dto.cpf,
            nome=dados["nome_cliente"],
            telefone=dados["telefone"],
        )

        if chegada_dto.veiculo_id is not None:
            veiculo = self.veiculo_repository.get_by_id(chegada_dto.veiculo_id)
            if veiculo is None:
                response.status_code = 404
                return {"status": "error", "message": "Veículo não encontrado"}
            # Um veículo de outro dono nunca é reaproveitado: seria trocar o
            # carro de dono por um id errado vindo da tela.
            if veiculo.cliente_id is not None and veiculo.cliente_id != (
                cliente.id if cliente else None
            ):
                response.status_code = 409
                return {"status": "error", "message": "Veículo é de outro cliente"}
            self.veiculo_repository.atualizar(
                veiculo,
                placa=dados["placa"],
                tipo=chegada_dto.tipo_carro,
                modelo=dados["modelo_carro"],
                cliente_id=cliente.id if cliente else None,
            )
        else:
            veiculo = self.veiculo_repository.get_or_create(
                placa=dados["placa"],
                cliente_id=cliente.id if cliente else None,
                tipo=chegada_dto.tipo_carro,
                modelo=dados["modelo_carro"],
            )

        dados_extras = {}
        if chegada_dto.danos_vistoria:
            dados_extras["vistoria"] = {
                "danos": chegada_dto.danos_vistoria,
                "registrada_em": agora.isoformat(),
            }

        lavagem = LavagemModel(
            origem="plataforma",
            status="aguardando",
            data=agora.date(),
            chegou_em=agora,
            agendamento_id=chegada_dto.agendamento_id,
            cliente_id=cliente.id if cliente else None,
            veiculo_id=veiculo.id if veiculo else None,
            tipo_carro=chegada_dto.tipo_carro or (veiculo.tipo if veiculo else None),
            funcionario_lavagem_id=chegada_dto.funcionario_lavagem_id,
            observacoes=chegada_dto.observacoes,
            dados_extras=dados_extras,
        )
        if dados["servico"]:
            lavagem.servico = dados["servico"]

        self.lavagem_repository.add(lavagem)

        if agendamento_model is not None:
            self._confirmar_agendamento(agendamento_model)

        # Só depois de tudo gravado: o contrato é consequência do check-in, e
        # nenhuma falha dele pode desfazer o carro que já entrou no pátio.
        contrato = self._emitir_contrato(lavagem, agora)

        response.status_code = 201
        return {
            "status": "success",
            "message": "Chegada registrada",
            "data": Lavagem.com_nomes(lavagem),
            "contrato": contrato,
        }

    def _com_dados_do_agendamento(
        self, chegada_dto: RegistrarChegadaDTO, agendamento: AgendamentoModel | None
    ) -> dict:
        """Os dados do cliente e do veículo, com o agendamento como reserva."""
        campos = ("nome_cliente", "telefone", "placa", "modelo_carro", "servico")
        return {
            campo: getattr(chegada_dto, campo)
            or (getattr(agendamento, campo, None) if agendamento else None)
            for campo in campos
        }

    def _emitir_contrato(self, lavagem_model, agora: datetime) -> dict:
        """O termo de adesão preenchido, arquivado e no WhatsApp do cliente.

        Melhor-esforço, como o `_notificar_carro_pronto` do avançar de status:
        a chegada já foi gravada, e PDF, Storage ou WhatsApp fora do ar não
        podem desfazer isso. O que der errado volta no retorno para a tela
        contar ao atendente — que aí pega o telefone certo e reenvia.

        O try/except em volta de tudo é mais agressivo que o do
        `_notificar_carro_pronto`, de propósito: a geração do PDF é código
        novo, e um erro subindo daqui viraria 500 numa chegada já gravada — o
        atendente clicaria de novo e criaria uma segunda lavagem do mesmo
        carro.
        """
        try:
            telefone = getattr(lavagem_model.cliente, "telefone", None)
            telefone = normalizar_telefone(telefone) if telefone else None

            resultado = emitir_contrato(lavagem_model, agora, telefone)

            # Grava a tentativa mesmo quando falha: serve de diagnóstico, e é o
            # que o reenvio consulta depois. Dict novo — o SQLAlchemy não
            # enxerga mutação in-place de JSONB.
            dados = dict(lavagem_model.dados_extras or {})
            registro = {
                "ok": resultado["enviada"],
                "telefone": telefone,
                "tentado_em": agora.isoformat(),
            }
            if not resultado["enviada"]:
                registro["motivo"] = resultado["motivo"]
            if resultado["caminho"]:
                registro["caminho"] = resultado["caminho"]
            if resultado["motivo_arquivo"]:
                registro["motivo_arquivo"] = resultado["motivo_arquivo"]
            dados["contrato"] = registro
            self.lavagem_repository.update_entity(lavagem_model, {"dados_extras": dados})

            return {"enviada": resultado["enviada"], "motivo": resultado["motivo"]}
        except Exception as erro:
            # Só o tipo: mensagens de erro de rede repetem URLs com credencial.
            print(f"Contrato: falha inesperada na emissão ({type(erro).__name__})")
            return {"enviada": False, "motivo": "falha_envio"}

    def _confirmar_agendamento(self, agendamento_model: AgendamentoModel) -> None:
        """Quem apareceu no pátio está confirmado.

        Só quando a transição vale: quem já estava confirmado fica como está, e
        a chegada nunca falha por causa do status do agendamento.
        """
        agendamento = Agendamento.model_validate(agendamento_model)
        if agendamento.pode_mudar_para("confirmado"):
            self.agendamento_repository.update_status(agendamento_model, "confirmado")
