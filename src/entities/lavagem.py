from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal, get_args
from datetime import date, datetime
from uuid import UUID

StatusLavagem = Literal["aguardando", "em_lavagem", "pronta", "concluida", "cancelada"]
OrigemLavagem = Literal["importacao", "plataforma", "bot"]

STATUS_VALIDOS: tuple[str, ...] = get_args(StatusLavagem)

# O carro anda para frente na operação. Cancelar é possível de qualquer ponto
# aberto; concluída é o fim.
TRANSICOES_PERMITIDAS: dict[str, tuple[str, ...]] = {
    "aguardando": ("em_lavagem", "cancelada"),
    "em_lavagem": ("pronta", "cancelada"),
    "pronta": ("concluida", "cancelada"),
    "concluida": (),
    "cancelada": (),
}

# Status que ainda estão no pátio — é o que a tela de operação mostra.
STATUS_ABERTOS: tuple[str, ...] = ("aguardando", "em_lavagem", "pronta")

# Qual horário cada transição carimba.
CARIMBO_POR_STATUS: dict[str, str] = {
    "em_lavagem": "iniciou_lavagem_em",
    "pronta": "terminou_lavagem_em",
    "concluida": "saiu_em",
}

# E qual duração cada transição fecha: (campo_inicio, campo_fim, campo_duracao).
# É aqui que a máquina de estados vira métrica: as três durações que a base
# histórica traz prontas são exatamente os três trechos entre os carimbos.
TRECHO_POR_STATUS: dict[str, tuple[str, str, str]] = {
    "em_lavagem": ("chegou_em", "iniciou_lavagem_em", "tempo_espera_antes_lavagem_min"),
    "pronta": ("iniciou_lavagem_em", "terminou_lavagem_em", "tempo_lavagem_total_min"),
    "concluida": ("terminou_lavagem_em", "saiu_em", "tempo_pos_lavagem_ate_retirada_min"),
}


def minutos_entre(inicio: Optional[datetime], fim: Optional[datetime]) -> Optional[float]:
    """Minutos entre dois carimbos, com uma casa decimal — a mesma precisão da
    planilha. Devolve None se faltar qualquer um dos dois."""
    if inicio is None or fim is None:
        return None
    return round((fim - inicio).total_seconds() / 60, 1)


def classificar_nps(nota: Optional[int]) -> Optional[str]:
    """Promotor 9–10, neutro 7–8, detrator 0–6 — a régua padrão do NPS."""
    if nota is None:
        return None
    if nota >= 9:
        return "promotor"
    if nota >= 7:
        return "neutro"
    return "detrator"


def calcular_nps(promotores: int, detratores: int, respostas: int) -> Optional[float]:
    """NPS = %promotores − %detratores, numa escala de −100 a +100.

    Note que NÃO é a média das notas — é a diferença entre as duas pontas, e os
    neutros só entram no denominador. Devolve None quando não houve resposta:
    com 43% das lavagens sem NPS, chamar isso de zero mentiria sobre a
    satisfação.

    Recebe contagens, não a lista de notas: contar é trabalho do banco (são 21
    mil linhas), enquanto a fórmula — o que conta como promotor, o que entra no
    denominador — é regra de negócio e fica aqui.
    """
    if not respostas:
        return None
    return round((promotores - detratores) / respostas * 100, 1)


class Lavagem(BaseModel):
    """Um carro lavado, do ponto de vista do negócio.

    Guarda horário e duração ao mesmo tempo porque as duas fontes coexistem: as
    linhas importadas da planilha só têm duração (não havia relógio, os registros
    viviam no papel), e as registradas pela plataforma têm os carimbos. A
    **duração é sempre a fonte das métricas** — quem carimba horário calcula a
    duração na hora e grava.
    """

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    id_externo: Optional[int] = None
    origem: OrigemLavagem = "plataforma"
    importacao_id: Optional[int] = None
    agendamento_id: Optional[UUID] = None

    # quem
    cliente_id: Optional[int] = None
    veiculo_id: Optional[int] = None
    tipo_carro: Optional[str] = None
    funcionario_lavagem_id: Optional[int] = None
    atendente_pagamento_id: Optional[int] = None

    # quando
    data: date
    chegou_em: Optional[datetime] = None
    iniciou_lavagem_em: Optional[datetime] = None
    terminou_lavagem_em: Optional[datetime] = None
    saiu_em: Optional[datetime] = None
    pago_em: Optional[datetime] = None

    # durações
    tempo_espera_antes_lavagem_min: Optional[float] = None
    tempo_lavagem_total_min: Optional[float] = None
    tempo_pos_lavagem_ate_retirada_min: Optional[float] = None
    tempo_ate_pagamento_min: Optional[float] = None

    # etapas
    t_teto_vidros_min: Optional[float] = None
    t_capo_parabrisa_min: Optional[float] = None
    t_laterais_portas_min: Optional[float] = None
    t_traseira_min: Optional[float] = None
    t_rodas_pneus_min: Optional[float] = None
    t_interior_min: Optional[float] = None

    # comercial
    servico: str = "Lavagem completa"
    preco_reais: Optional[float] = None
    metodo_pagamento: Optional[str] = None
    cnpj_receita: Optional[str] = None

    # satisfação
    nps_cliente: Optional[int] = None
    nota_google: Optional[float] = None

    # insumos
    shampoo_ml: Optional[float] = None
    cera_ml: Optional[float] = None
    pretinho_ml: Optional[float] = None
    aromatizante_ml: Optional[float] = None

    # controle
    status: StatusLavagem = "aguardando"
    observacoes: Optional[str] = None

    def pode_mudar_para(self, novo_status: str) -> bool:
        return novo_status in TRANSICOES_PERMITIDAS.get(self.status, ())

    def esta_no_patio(self) -> bool:
        return self.status in STATUS_ABERTOS

    def classificacao_nps(self) -> Optional[str]:
        return classificar_nps(self.nps_cliente)

    @classmethod
    def com_nomes(cls, model) -> "LavagemComNomes":
        """Monta a versão que vai para a tela, com nome no lugar de id.

        Os relacionamentos do model podem ser nulos (a base tem 14% das linhas
        sem cliente e 6% sem lavador), por isso cada acesso passa por getattr.
        """
        base = cls.model_validate(model)
        return LavagemComNomes(
            **base.model_dump(),
            cliente_nome=getattr(model.cliente, "nome", None),
            veiculo_placa=getattr(model.veiculo, "placa", None),
            funcionario_nome=getattr(model.funcionario_lavagem, "nome", None),
            atendente_nome=getattr(model.atendente_pagamento, "nome", None),
        )

    def tempo_total_no_local_min(self) -> Optional[float]:
        """Quanto tempo o cliente ficou preso ao lava-rápido, somando os três
        trechos. É o número que ele sente — e o que o diagnóstico apontou como
        maior driver da satisfação. None se faltar qualquer trecho."""
        trechos = [
            self.tempo_espera_antes_lavagem_min,
            self.tempo_lavagem_total_min,
            self.tempo_pos_lavagem_ate_retirada_min,
        ]
        if any(t is None for t in trechos):
            return None
        return round(sum(trechos), 1)


class LavagemComNomes(Lavagem):
    """A lavagem como a tela precisa dela: com nome e placa resolvidos."""

    cliente_nome: Optional[str] = None
    veiculo_placa: Optional[str] = None
    funcionario_nome: Optional[str] = None
    atendente_nome: Optional[str] = None
