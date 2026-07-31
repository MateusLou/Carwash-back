import re

from sqlalchemy.orm import Session
from sqlalchemy import or_
from repositories.base_repository import BaseRepository
from models.cliente_model import ClienteModel
from utils.normalizar_texto import normalizar_texto, normalizar_telefone, normalizar_cpf
from typing import Optional


class ClienteRepository(BaseRepository[ClienteModel]):
    def __init__(self, session: Session):
        super().__init__(session, ClienteModel)

    def get_by_id(self, cliente_id: int) -> ClienteModel | None:
        return self.session.query(self.model).filter(self.model.id == cliente_id).first()

    def get_by_cpf(self, cpf: str) -> ClienteModel | None:
        return (
            self.session.query(self.model)
            .filter(self.model.cpf == normalizar_cpf(cpf))
            .first()
        )

    def get_by_telefone(self, telefone: str) -> ClienteModel | None:
        """Telefone repete entre cadastros; na dúvida, vale o mexido por último —
        é o dono mais provável do número hoje."""
        return (
            self.session.query(self.model)
            .filter(self.model.telefone == normalizar_telefone(telefone))
            .order_by(self.model.atualizado_em.desc(), self.model.id.desc())
            .first()
        )

    def get_by_nome(self, nome: str) -> ClienteModel | None:
        return (
            self.session.query(self.model)
            .filter(self.model.nome_normalizado == normalizar_texto(nome))
            .first()
        )

    def buscar(self, termo: str, limite: int = 20) -> list[ClienteModel]:
        """Busca do autocomplete do check-in: casa por pedaço do nome (sem
        acento), do telefone ou do CPF."""
        alvo = normalizar_texto(termo)
        digitos = re.sub(r"\D", "", termo)
        condicoes = [self.model.nome_normalizado.like(f"%{alvo}%")]
        if digitos:
            condicoes.append(self.model.telefone.like(f"%{digitos}%"))
            condicoes.append(self.model.cpf.like(f"%{digitos}%"))
        return (
            self.session.query(self.model)
            .filter(or_(*condicoes))
            .order_by(self.model.nome)
            .limit(limite)
            .all()
        )

    def get_or_create(
        self,
        cpf: Optional[str] = None,
        nome: Optional[str] = None,
        telefone: Optional[str] = None,
    ) -> ClienteModel | None:
        """Acha o cliente ou cria um novo.

        O CPF manda: é o que o check-in exige e a única chave que a base
        histórica tem completa. Telefone vem depois — é ele que amarra o
        cadastro ao WhatsApp — e o nome é o último recurso, herdado da
        importação, onde dois homônimos viram um só e não há como evitar.

        Para quem foi achado pelo CPF, nome e telefone informados
        **sobrescrevem** o que estava lá: a tela mostra os dois preenchidos e
        editáveis, então uma correção do atendente tem de valer. Nos outros
        casos vale a regra antiga, de só preencher o que está vazio.

        Telefone pode repetir entre cadastros: o mesmo número serve um casal,
        ou um CPF novo que chega com o número de um cadastro antigo.
        """
        cpf_norm = normalizar_cpf(cpf) if cpf else None
        telefone_norm = normalizar_telefone(telefone) if telefone else None
        if not cpf_norm and not nome and not telefone_norm:
            return None

        cliente = self.get_by_cpf(cpf_norm) if cpf_norm else None

        if cliente is None:
            # Cadastro antigo sem CPF ganha identidade agora. Quem já tem OUTRO
            # CPF não é a mesma pessoa — são dois homônimos, ou um telefone que
            # trocou de dono —, e roubar o cadastro dele apagaria um CPF certo.
            candidato = self.get_by_telefone(telefone_norm) if telefone_norm else None
            if candidato is None and nome:
                candidato = self.get_by_nome(nome)
            if candidato is not None and not (cpf_norm and candidato.cpf):
                cliente = candidato

        if cliente is None:
            return self.add(
                ClienteModel(
                    cpf=cpf_norm,
                    nome=nome,
                    nome_normalizado=normalizar_texto(nome) if nome else None,
                    telefone=telefone_norm,
                )
            )

        achado_por_cpf = bool(cpf_norm and cliente.cpf == cpf_norm)
        mudou = False

        if cpf_norm and not cliente.cpf:
            cliente.cpf = cpf_norm
            mudou = True
        if nome and cliente.nome != nome and (achado_por_cpf or not cliente.nome):
            cliente.nome = nome
            cliente.nome_normalizado = normalizar_texto(nome)
            mudou = True
        if (
            telefone_norm
            and cliente.telefone != telefone_norm
            and (achado_por_cpf or not cliente.telefone)
        ):
            cliente.telefone = telefone_norm
            mudou = True

        if mudou:
            self.session.commit()
            self.session.refresh(cliente)
        return cliente
