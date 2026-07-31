from repositories.lavagem_repository import LavagemRepository
from repositories.agendamento_repository import AgendamentoRepository
from use_cases.lavagem.avancar_status_lavagem.avancar_status_lavagem_dto import (
    AvancarStatusLavagemDTO,
)
from entities.lavagem import (
    Lavagem, CARIMBO_POR_STATUS, TRECHO_POR_STATUS, TRANSICOES_PERMITIDAS, minutos_entre,
)
from entities.agendamento import Agendamento
from utils.enviar_whatsapp import enviar_whatsapp
from utils.normalizar_texto import normalizar_telefone
from fastapi import Response
from datetime import datetime, timezone


NOME_DO_ESTABELECIMENTO = "Lava-Rápido Nogueira"


def montar_mensagem_carro_pronto(nome: str | None, placa: str | None) -> str:
    """O texto que o cliente recebe no WhatsApp. É para ser editado aqui.

    Placa entre parênteses quando existe: em casa com dois carros, ou quando o
    telefone é o mesmo da esposa, é o que evita a dúvida de qual ficou pronto.
    """
    saudacao = f"Oi, {nome.split()[0]}!" if nome and nome.strip() else "Oi!"
    carro = f" ({placa})" if placa else ""
    return (
        f"{saudacao} Seu carro{carro} já está pronto e esperando por você aqui no "
        f"{NOME_DO_ESTABELECIMENTO}. 🚗✨\n\n"
        "Pode vir buscar quando quiser!"
    )


class AvancarStatusLavagemUseCase:
    """Move o carro de uma etapa para a próxima.

    Cada transição faz duas coisas: carimba o horário do momento e **fecha a
    duração do trecho que terminou**. É esse cálculo que faz a lavagem
    registrada hoje ter os mesmos campos de tempo que as 37 mil importadas — e
    por isso as duas aparecem juntas no mesmo gráfico.
    """

    def __init__(
        self,
        lavagem_repository: LavagemRepository,
        agendamento_repository: AgendamentoRepository,
    ):
        self.lavagem_repository = lavagem_repository
        self.agendamento_repository = agendamento_repository

    def execute(self, lavagem_id: int, avancar_dto: AvancarStatusLavagemDTO, response: Response):
        lavagem_model = self.lavagem_repository.get_by_id(lavagem_id)

        if lavagem_model is None:
            response.status_code = 404
            return {"status": "error", "message": "Lavagem não encontrada"}

        lavagem = Lavagem.model_validate(lavagem_model)
        novo_status = avancar_dto.novo_status

        if not lavagem.pode_mudar_para(novo_status):
            permitidos = TRANSICOES_PERMITIDAS.get(lavagem.status, ())
            response.status_code = 409
            return {
                "status": "error",
                "message": (
                    f"Não dá para ir de '{lavagem.status}' para '{novo_status}'. "
                    + (
                        f"A partir de '{lavagem.status}', só: {', '.join(permitidos)}."
                        if permitidos
                        else f"'{lavagem.status}' é um estado final."
                    )
                ),
            }

        agora = datetime.now(timezone.utc)

        campo_carimbo = CARIMBO_POR_STATUS.get(novo_status)
        if campo_carimbo:
            setattr(lavagem_model, campo_carimbo, agora)

        trecho = TRECHO_POR_STATUS.get(novo_status)
        if trecho:
            campo_inicio, campo_fim, campo_duracao = trecho
            duracao = minutos_entre(
                getattr(lavagem_model, campo_inicio), getattr(lavagem_model, campo_fim)
            )
            # None quando a linha veio da importação e não tem carimbo de início:
            # nesse caso a duração que já está lá é a da planilha, e sobrescrever
            # com nada apagaria o dado.
            if duracao is not None:
                setattr(lavagem_model, campo_duracao, duracao)

        lavagem_model.status = novo_status
        lavagem_model.atualizado_em = agora
        self.lavagem_repository.salvar(lavagem_model)

        if novo_status == "concluida" and lavagem_model.agendamento_id is not None:
            self._concluir_agendamento(lavagem_model.agendamento_id)

        # "pronta" é o momento em que o carro terminou de ser lavado e ficou
        # parado esperando alguém vir buscar — o único ponto do ciclo em que
        # avisar o cliente ainda muda alguma coisa.
        notificacao = None
        if novo_status == "pronta":
            notificacao = self._notificar_carro_pronto(lavagem_model, agora)

        resposta = {
            "status": "success",
            "message": f"Lavagem em '{novo_status}'",
            "data": Lavagem.com_nomes(lavagem_model),
        }
        if notificacao is not None:
            resposta["notificacao"] = notificacao
        return resposta

    def _concluir_agendamento(self, agendamento_id) -> None:
        """Carro entregue fecha o agendamento que o trouxe.

        Sem isso o agendamento ficaria preso em "confirmado" e o funcionário
        teria que marcar concluído nas duas telas. É melhor-esforço: se o
        agendamento sumiu ou já está num estado final, a lavagem avança do
        mesmo jeito.
        """
        agendamento_model = self.agendamento_repository.get_by_id(agendamento_id)
        if agendamento_model is None:
            return

        agendamento = Agendamento.model_validate(agendamento_model)
        if agendamento.pode_mudar_para("concluido"):
            self.agendamento_repository.update_status(agendamento_model, "concluido")

    def _notificar_carro_pronto(self, lavagem_model, agora: datetime) -> dict:
        """Avisa o cliente no WhatsApp que o carro ficou pronto.

        Melhor-esforço, como `_concluir_agendamento`: o status já foi gravado, e
        WhatsApp fora do ar não pode desfazer isso. O que der errado volta no
        retorno para a tela contar ao funcionário — que aí liga para o cliente.
        """
        dados = dict(lavagem_model.dados_extras or {})

        # Trava de reenvio: o funcionário que marca "pronta" duas vezes (ou o
        # clique duplo) não faz o cliente receber a mesma mensagem de novo.
        if dados.get("notificacao_pronta", {}).get("ok"):
            return {"enviada": False, "motivo": "ja_avisado"}

        telefone = self._telefone_do_cliente(lavagem_model)
        if not telefone:
            return {"enviada": False, "motivo": "sem_telefone"}

        # getattr tolerante a nulo, como em Lavagem.com_nomes: 14% das lavagens
        # da base não têm cliente, e a placa some quando o carro entrou sem ela.
        mensagem = montar_mensagem_carro_pronto(
            getattr(lavagem_model.cliente, "nome", None),
            getattr(lavagem_model.veiculo, "placa", None),
        )
        resultado = enviar_whatsapp(telefone, mensagem)

        # Grava a tentativa mesmo quando falha: serve de diagnóstico, e como a
        # trava lá em cima olha só o `ok`, uma nova tentativa continua possível.
        registro = {
            "ok": resultado["enviada"],
            "telefone": telefone,
            "tentada_em": agora.isoformat(),
        }
        if not resultado["enviada"]:
            registro["motivo"] = resultado["motivo"]
        dados["notificacao_pronta"] = registro
        self.lavagem_repository.update_entity(lavagem_model, {"dados_extras": dados})

        return resultado

    def _telefone_do_cliente(self, lavagem_model) -> str | None:
        """O telefone para onde mandar, normalizado no formato da Z-API.

        A fonte normal é `clientes.telefone`. O agendamento é rede de
        segurança: hoje o check-in já copia o telefone do agendamento para o
        cadastro (`RegistrarChegadaUseCase`), então esse segundo caminho quase
        nunca roda — mas `clientes.telefone` nasce nulo em quem veio da base
        importada, e em `agendamentos` a coluna é NOT NULL. Custa uma consulta
        só quando o cadastro está sem telefone.
        """
        telefone = getattr(lavagem_model.cliente, "telefone", None)

        if not telefone and lavagem_model.agendamento_id is not None:
            agendamento_model = self.agendamento_repository.get_by_id(
                lavagem_model.agendamento_id
            )
            telefone = getattr(agendamento_model, "telefone", None)

        return normalizar_telefone(telefone) if telefone else None
