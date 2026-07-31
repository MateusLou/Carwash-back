from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, distinct, cast, literal, text, Date
from sqlalchemy.dialects.postgresql import insert as pg_insert
from repositories.base_repository import BaseRepository
from models.lavagem_model import LavagemModel
from models.funcionario_model import FuncionarioModel
from models.cliente_model import ClienteModel
from entities.lavagem import STATUS_ABERTOS
from utils.normalizar_texto import normalizar_texto
from datetime import date
from typing import Optional
from uuid import UUID

# "semana"/"mes" do filtro do dashboard → o argumento que o date_trunc entende.
GRANULARIDADES = {"dia": "day", "semana": "week", "mes": "month"}

# As quatro durações e as seis etapas, na ordem em que a operação acontece.
DURACOES = (
    "tempo_espera_antes_lavagem_min",
    "tempo_lavagem_total_min",
    "tempo_pos_lavagem_ate_retirada_min",
    "tempo_ate_pagamento_min",
)
ETAPAS = (
    "t_teto_vidros_min",
    "t_capo_parabrisa_min",
    "t_laterais_portas_min",
    "t_traseira_min",
    "t_rodas_pneus_min",
    "t_interior_min",
)


class LavagemRepository(BaseRepository[LavagemModel]):
    """Único lugar do projeto que escreve query sobre lavagens.

    Uma regra atravessa o arquivo inteiro: **cancelada não conta**. Um carro que
    não foi lavado não é receita, não é tempo operacional e não é produtividade.
    Só a contagem de canceladas em si as inclui.
    """

    def __init__(self, session: Session):
        super().__init__(session, LavagemModel)

    # ------------------------------------------------------------------
    # leitura simples
    # ------------------------------------------------------------------
    def get_by_id(self, lavagem_id: int) -> LavagemModel | None:
        return self.session.query(self.model).filter(self.model.id == lavagem_id).first()

    def get_by_id_externo(self, id_externo: int) -> LavagemModel | None:
        return self.session.query(self.model).filter(self.model.id_externo == id_externo).first()

    def get_by_agendamento_id(self, agendamento_id: UUID) -> LavagemModel | None:
        """A lavagem que nasceu deste agendamento, se o carro já chegou.

        É a trava do check-in: um agendamento vira um carro no pátio, não dois.
        """
        return (
            self.session.query(self.model)
            .filter(self.model.agendamento_id == agendamento_id)
            .first()
        )

    def mapa_por_agendamentos(self, agendamento_ids: list[UUID]) -> dict[UUID, LavagemModel]:
        """A lavagem de cada agendamento da página, numa consulta só.

        A aba de agendamentos mostra em que ponto o carro está; perguntar isso
        linha a linha seria uma ida ao Supabase por agendamento.
        """
        if not agendamento_ids:
            return {}
        lavagens = (
            self.session.query(self.model)
            .filter(self.model.agendamento_id.in_(agendamento_ids))
            .order_by(self.model.id)
            .all()
        )
        return {lavagem.agendamento_id: lavagem for lavagem in lavagens}

    def list_patio(self) -> list[LavagemModel]:
        """O que está aberto agora, do que chegou primeiro para o mais recente."""
        return (
            self.session.query(self.model)
            .options(
                joinedload(self.model.cliente),
                joinedload(self.model.veiculo),
                joinedload(self.model.funcionario_lavagem),
                joinedload(self.model.atendente_pagamento),
            )
            .filter(self.model.status.in_(STATUS_ABERTOS))
            .order_by(self.model.chegou_em.asc().nullslast(), self.model.id)
            .all()
        )

    def _filtrar(
        self,
        query,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        status: Optional[str] = None,
        funcionario_id: Optional[int] = None,
        tipo_carro: Optional[str] = None,
        cliente_id: Optional[int] = None,
        cliente_nome: Optional[str] = None,
    ):
        if data_inicio is not None:
            query = query.filter(self.model.data >= data_inicio)
        if data_fim is not None:
            query = query.filter(self.model.data <= data_fim)
        if status is not None:
            query = query.filter(self.model.status == status)
        if funcionario_id is not None:
            query = query.filter(self.model.funcionario_lavagem_id == funcionario_id)
        if tipo_carro is not None:
            query = query.filter(self.model.tipo_carro == tipo_carro)
        if cliente_id is not None:
            query = query.filter(self.model.cliente_id == cliente_id)
        if cliente_nome:
            # Subquery em vez de join: esta função é a base de todo o dashboard
            # (via _validas), e um join a mais mudaria a cardinalidade daquelas
            # agregações — além de colidir com o join que
            # produtividade_por_funcionario já faz.
            # O LIKE cai sobre nome_normalizado, que já está sem acento e em
            # minúsculas: é o mesmo truque de ClienteRepository.buscar, e por
            # isso "jose" acha "José" sem precisar de ILIKE.
            alvo = normalizar_texto(cliente_nome)
            clientes = self.session.query(ClienteModel.id).filter(
                ClienteModel.nome_normalizado.like(f"%{alvo}%")
            )
            query = query.filter(self.model.cliente_id.in_(clientes))
        return query

    def list_by_filtros(self, limite: int = 200, offset: int = 0, **filtros) -> list[LavagemModel]:
        query = self._filtrar(self.session.query(self.model), **filtros)
        return (
            # joinedload porque a tela mostra nome e placa: sem ele, uma página
            # de 100 linhas dispara 400 SELECTs extras (o clássico N+1)
            query.options(
                joinedload(self.model.cliente),
                joinedload(self.model.veiculo),
                joinedload(self.model.funcionario_lavagem),
                joinedload(self.model.atendente_pagamento),
            )
            .order_by(self.model.data.desc(), self.model.id.desc())
            .limit(limite)
            .offset(offset)
            .all()
        )

    def contar(self, **filtros) -> int:
        return self._filtrar(self.session.query(func.count(self.model.id)), **filtros).scalar() or 0

    # ------------------------------------------------------------------
    # importação
    # ------------------------------------------------------------------
    def inserir_lote_importado(self, registros: list[dict]) -> int:
        """Insere um lote da planilha e devolve quantas linhas entraram.

        ON CONFLICT DO NOTHING sobre o `id_externo` é o que torna o re-upload
        seguro: o arquivo inteiro volta, mas só a aba nova insere de fato. Todo
        dict do lote precisa ter as MESMAS chaves — o VALUES multi-linha do
        SQLAlchemy compila um comando só e uma chave a menos derruba a
        compilação (por isso o molde do motor).

        NÃO comita: no modo substituir a carga inteira é uma transação só.
        """
        if not registros:
            return 0
        comando = (
            pg_insert(LavagemModel)
            .values(registros)
            .on_conflict_do_nothing(
                index_elements=["id_externo"],
                index_where=text("id_externo is not null"),
            )
        )
        resultado = self.session.execute(comando)
        return resultado.rowcount or 0

    def apagar_importadas(self) -> int:
        """Apaga só as lavagens vindas de planilha, preservando as da operação.

        É o modo substituir. DELETE seletivo, nunca TRUNCATE: o pátio já tem
        check-ins reais (`origem='plataforma'`) que não vieram de arquivo
        nenhum — e um TRUNCATE em cascata a partir de clientes levaria a
        tabela inteira junto. NÃO comita, pela mesma razão do insert.
        """
        return (
            self.session.query(self.model)
            .filter(self.model.origem == "importacao")
            .delete(synchronize_session=False)
        )

    # ------------------------------------------------------------------
    # base das métricas
    # ------------------------------------------------------------------
    def _validas(self, colunas, data_inicio, data_fim, **extras):
        """Query já filtrada por período e sem as canceladas."""
        query = self._filtrar(
            self.session.query(*colunas), data_inicio=data_inicio, data_fim=data_fim, **extras
        )
        return query.filter(self.model.status != "cancelada")

    def resumo(self, data_inicio: Optional[date], data_fim: Optional[date]) -> dict:
        """Os números dos cards do topo, num único SELECT."""
        linha = self._validas(
            [
                func.count(self.model.id),
                func.count(distinct(self.model.cliente_id)),
                func.coalesce(func.sum(self.model.preco_reais), 0),
                func.avg(self.model.preco_reais),
                func.avg(self.model.tempo_lavagem_total_min),
                func.count(distinct(self.model.data)),
            ],
            data_inicio,
            data_fim,
        ).one()

        lavagens, clientes, receita, ticket, tempo_medio, dias = linha
        return {
            "lavagens": lavagens or 0,
            "clientes_distintos": clientes or 0,
            "receita": float(receita or 0),
            "ticket_medio": float(ticket) if ticket is not None else None,
            "tempo_lavagem_medio_min": float(tempo_medio) if tempo_medio is not None else None,
            "dias_com_operacao": dias or 0,
            "media_carros_por_dia": round(lavagens / dias, 1) if dias else None,
        }

    def serie_por_periodo(
        self, granularidade: str, data_inicio: Optional[date], data_fim: Optional[date]
    ) -> list[dict]:
        """A série que vira gráfico: lavagens, receita e clientes por semana ou mês."""
        unidade = GRANULARIDADES[granularidade]
        periodo = cast(func.date_trunc(unidade, self.model.data), Date).label("periodo")

        linhas = (
            self._validas(
                [
                    periodo,
                    func.count(self.model.id),
                    func.coalesce(func.sum(self.model.preco_reais), 0),
                    func.count(distinct(self.model.cliente_id)),
                ],
                data_inicio,
                data_fim,
            )
            .group_by(periodo)
            .order_by(periodo)
            .all()
        )
        return [
            {
                "periodo": p.isoformat(),
                "lavagens": n,
                "receita": float(receita or 0),
                "clientes": clientes,
            }
            for p, n, receita, clientes in linhas
        ]

    def por_dimensao(
        self, coluna: str, data_inicio: Optional[date], data_fim: Optional[date]
    ) -> list[dict]:
        """Quebra por tipo_carro, metodo_pagamento ou cnpj_receita.

        Nulo vira uma categoria explícita ("(sem registro)") em vez de sumir:
        `metodo_pagamento` falta em 8% das linhas, e omitir isso faria as fatias
        somarem menos que o total sem explicar por quê.
        """
        campo = getattr(self.model, coluna)
        linhas = (
            self._validas(
                [campo, func.count(self.model.id), func.coalesce(func.sum(self.model.preco_reais), 0)],
                data_inicio,
                data_fim,
            )
            .group_by(campo)
            .order_by(func.count(self.model.id).desc())
            .all()
        )
        return [
            {
                "categoria": valor if valor is not None else "(sem registro)",
                "lavagens": n,
                "receita": float(receita or 0),
            }
            for valor, n, receita in linhas
        ]

    def por_dimensoes(
        self, colunas: tuple[str, ...], data_inicio: Optional[date], data_fim: Optional[date]
    ) -> dict[str, list[dict]]:
        """As quebras de várias colunas de uma vez, num UNION ALL.

        Cada `group by` é uma consulta diferente, mas quatro chamadas separadas
        são quatro idas ao Supabase. Empilhadas com um rótulo de qual dimensão é
        cada linha, viram uma viagem só.
        """
        partes = []
        for coluna in colunas:
            campo = getattr(self.model, coluna)
            partes.append(
                self._validas(
                    [
                        literal(coluna).label("dimensao"),
                        campo.label("categoria"),
                        func.count(self.model.id).label("lavagens"),
                        func.coalesce(func.sum(self.model.preco_reais), 0).label("receita"),
                    ],
                    data_inicio,
                    data_fim,
                ).group_by(campo)
            )

        agrupado: dict[str, list[dict]] = {coluna: [] for coluna in colunas}
        for dimensao, categoria, n, receita in partes[0].union_all(*partes[1:]).all():
            agrupado[dimensao].append(
                {
                    "categoria": categoria if categoria is not None else "(sem registro)",
                    "lavagens": n,
                    "receita": float(receita or 0),
                }
            )
        for linhas in agrupado.values():
            linhas.sort(key=lambda item: item["lavagens"], reverse=True)
        return agrupado

    def tempos(self, data_inicio: Optional[date], data_fim: Optional[date]) -> list[dict]:
        """Média e p90 de cada duração e de cada etapa.

        O p90 vai junto porque média esconde fila: o dia ruim é o que o cliente
        lembra. `n` também vai — cada duração tem uma quantidade diferente de
        registros (a espera falta em 14% das linhas), e sem o n a comparação
        entre elas engana.
        """
        colunas = DURACOES + ETAPAS

        # As 30 agregações (média, p90 e contagem de 10 colunas) saem num SELECT
        # só. Uma query por métrica seria mais legível, mas são 10 idas e voltas
        # até o Supabase — que fica em outro continente. O mesmo resultado em
        # uma viagem em vez de dez.
        agregacoes = []
        for coluna in colunas:
            campo = getattr(self.model, coluna)
            agregacoes += [
                func.avg(campo),
                func.percentile_cont(0.9).within_group(campo.asc()),
                func.count(campo),
            ]

        linha = self._validas(agregacoes, data_inicio, data_fim).one()

        resultado = []
        for i, coluna in enumerate(colunas):
            media, p90, n = linha[i * 3], linha[i * 3 + 1], linha[i * 3 + 2]
            resultado.append(
                {
                    "metrica": coluna,
                    "media_min": round(float(media), 1) if media is not None else None,
                    "p90_min": round(float(p90), 1) if p90 is not None else None,
                    "n": n or 0,
                }
            )
        return resultado

    def produtividade_por_funcionario(
        self, data_inicio: Optional[date], data_fim: Optional[date], limite: int = 20
    ) -> list[dict]:
        """Quantas lavagens cada um fez, em quantos dias, e quanto leva em média."""
        linhas = (
            self._validas(
                [
                    FuncionarioModel.nome,
                    func.count(self.model.id),
                    func.count(distinct(self.model.data)),
                    func.avg(self.model.tempo_lavagem_total_min),
                ],
                data_inicio,
                data_fim,
            )
            .join(FuncionarioModel, FuncionarioModel.id == self.model.funcionario_lavagem_id)
            .group_by(FuncionarioModel.nome)
            .order_by(func.count(self.model.id).desc())
            .limit(limite)
            .all()
        )
        return [
            {
                "funcionario": nome,
                "lavagens": n,
                "dias_trabalhados": dias,
                "lavagens_por_dia": round(n / dias, 1) if dias else None,
                "tempo_medio_min": round(float(tempo), 1) if tempo is not None else None,
            }
            for nome, n, dias, tempo in linhas
        ]

    # ------------------------------------------------------------------
    # satisfação
    # ------------------------------------------------------------------
    def contagem_nps(self, data_inicio: Optional[date], data_fim: Optional[date]) -> dict:
        """Quantos promotores, neutros e detratores — contados no banco.

        Trazer as notas uma a uma seria mais simples, mas são 21 mil linhas
        atravessando a rede para virar três números. A contagem é agregação, que
        é trabalho de query; **a fórmula do NPS continua na entity**, que recebe
        estes totais.
        """
        nota = self.model.nps_cliente
        total, promotores, neutros, detratores, soma = self._validas(
            [
                func.count(nota),
                func.count(nota).filter(nota >= 9),
                func.count(nota).filter(nota.between(7, 8)),
                func.count(nota).filter(nota <= 6),
                func.coalesce(func.sum(nota), 0),
            ],
            data_inicio,
            data_fim,
        ).one()
        return {
            "respostas": total or 0,
            "promotores": promotores or 0,
            "neutros": neutros or 0,
            "detratores": detratores or 0,
            "nota_media": round(float(soma) / total, 2) if total else None,
        }

    def resumo_nota_google(self, data_inicio: Optional[date], data_fim: Optional[date]) -> dict:
        media, n = self._validas(
            [func.avg(self.model.nota_google), func.count(self.model.nota_google)],
            data_inicio,
            data_fim,
        ).one()
        return {"media": round(float(media), 2) if media is not None else None, "n": n or 0}

    def serie_nps(
        self, granularidade: str, data_inicio: Optional[date], data_fim: Optional[date]
    ) -> list[dict]:
        """Promotores, neutros e detratores por período — a matéria-prima do
        gráfico de NPS. A conta final é feita na entity."""
        unidade = GRANULARIDADES[granularidade]
        periodo = cast(func.date_trunc(unidade, self.model.data), Date).label("periodo")
        nota = self.model.nps_cliente

        linhas = (
            self._validas(
                [
                    periodo,
                    func.count(nota),
                    func.count(nota).filter(nota >= 9),
                    func.count(nota).filter(nota.between(7, 8)),
                    func.count(nota).filter(nota <= 6),
                ],
                data_inicio,
                data_fim,
            )
            .filter(nota.isnot(None))
            .group_by(periodo)
            .order_by(periodo)
            .all()
        )
        return [
            {
                "periodo": p.isoformat(),
                "respostas": total,
                "promotores": promotores,
                "neutros": neutros,
                "detratores": detratores,
                "nps": round((promotores - detratores) / total * 100, 1) if total else None,
            }
            for p, total, promotores, neutros, detratores in linhas
        ]

    # ------------------------------------------------------------------
    # escrita
    # ------------------------------------------------------------------
    def salvar(self, lavagem: LavagemModel) -> LavagemModel:
        self.session.commit()
        self.session.refresh(lavagem)
        return lavagem

    def periodo_disponivel(self) -> dict:
        """Primeira e última data com dado — o dashboard usa para não abrir num
        período vazio quando a base importada termina meses atrás."""
        minima, maxima = self.session.query(
            func.min(self.model.data), func.max(self.model.data)
        ).one()
        return {
            "data_inicio": minima.isoformat() if minima else None,
            "data_fim": maxima.isoformat() if maxima else None,
        }
