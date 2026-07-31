from repositories.lavagem_repository import LavagemRepository
from repositories.cliente_repository import ClienteRepository
from use_cases.lavagem.contrato import emitir_contrato
from use_cases.lavagem.reenviar_contrato.reenviar_contrato_dto import ReenviarContratoDTO
from utils.normalizar_texto import normalizar_telefone
from fastapi import Response
from datetime import datetime, timezone


class ReenviarContratoUseCase:
    """Manda o termo de adesão de novo, para quando o primeiro envio não saiu.

    Telefone digitado errado, cliente que apagou a mensagem, Z-API fora do ar
    na hora do check-in — sem este caminho, o único jeito de reenviar seria
    registrar uma chegada falsa, o que sujaria as métricas de movimento.

    O contrato é gerado de novo com os dados **atuais** da lavagem: se a
    vistoria foi corrigida depois do check-in, o reenviado reflete a correção.
    """

    def __init__(
        self,
        lavagem_repository: LavagemRepository,
        cliente_repository: ClienteRepository,
    ):
        self.lavagem_repository = lavagem_repository
        self.cliente_repository = cliente_repository

    def execute(self, lavagem_id: int, dto: ReenviarContratoDTO, response: Response):
        lavagem_model = self.lavagem_repository.get_by_id(lavagem_id)

        if lavagem_model is None:
            response.status_code = 404
            return {"status": "error", "message": "Lavagem não encontrada"}

        agora = datetime.now(timezone.utc)
        telefone = self._resolver_telefone(lavagem_model, dto)

        resultado = emitir_contrato(lavagem_model, agora, telefone)

        # O registro sobrescreve o da tentativa anterior — o que importa para a
        # operação é o estado da última. Dict novo: o SQLAlchemy não enxerga
        # mutação in-place de JSONB.
        dados = dict(lavagem_model.dados_extras or {})
        registro = {
            "ok": resultado["enviada"],
            "telefone": telefone,
            "tentado_em": agora.isoformat(),
            "reenvio": True,
        }
        if not resultado["enviada"]:
            registro["motivo"] = resultado["motivo"]
        if resultado["caminho"]:
            registro["caminho"] = resultado["caminho"]
        if resultado["motivo_arquivo"]:
            registro["motivo_arquivo"] = resultado["motivo_arquivo"]
        dados["contrato"] = registro
        self.lavagem_repository.update_entity(lavagem_model, {"dados_extras": dados})

        return {
            "status": "success",
            "message": "Contrato enviado" if resultado["enviada"] else "Contrato não enviado",
            "contrato": {"enviada": resultado["enviada"], "motivo": resultado["motivo"]},
        }

    def _resolver_telefone(self, lavagem_model, dto: ReenviarContratoDTO) -> str | None:
        """O número digitado ganha do cadastro — e conserta o cadastro.

        Sem a segunda parte, o aviso de "carro pronto" erraria o mesmo alvo uma
        hora depois.
        """
        digitado = normalizar_telefone(dto.telefone) if dto.telefone else None

        if digitado and lavagem_model.cliente is not None:
            self.cliente_repository.update_entity(
                lavagem_model.cliente, {"telefone": digitado}
            )

        if digitado:
            return digitado

        telefone = getattr(lavagem_model.cliente, "telefone", None)
        return normalizar_telefone(telefone) if telefone else None
