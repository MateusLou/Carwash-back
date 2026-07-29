from sqlalchemy.orm import Session
from sqlalchemy import or_
from repositories.base_repository import BaseRepository
from models.cliente_model import ClienteModel
from utils.normalizar_texto import normalizar_texto, normalizar_telefone
from typing import Optional


class ClienteRepository(BaseRepository[ClienteModel]):
    def __init__(self, session: Session):
        super().__init__(session, ClienteModel)

    def get_by_id(self, cliente_id: int) -> ClienteModel | None:
        return self.session.query(self.model).filter(self.model.id == cliente_id).first()

    def get_by_telefone(self, telefone: str) -> ClienteModel | None:
        return (
            self.session.query(self.model)
            .filter(self.model.telefone == normalizar_telefone(telefone))
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
        acento) ou por pedaço do telefone."""
        alvo = normalizar_texto(termo)
        digitos = normalizar_telefone(termo)
        condicoes = [self.model.nome_normalizado.like(f"%{alvo}%")]
        if digitos:
            condicoes.append(self.model.telefone.like(f"%{digitos}%"))
        return (
            self.session.query(self.model)
            .filter(or_(*condicoes))
            .order_by(self.model.nome)
            .limit(limite)
            .all()
        )

    def get_or_create(
        self, nome: Optional[str] = None, telefone: Optional[str] = None
    ) -> ClienteModel | None:
        """Acha o cliente ou cria um novo.

        O telefone manda: é chave de verdade. O nome é o desempate herdado da
        base histórica, que não tem telefone nenhum — dois clientes de mesmo
        nome viram um só, e não há como evitar isso sem telefone. Quando o
        cadastro achado por nome ainda não tem telefone e agora veio um, o
        telefone é preenchido: é o cadastro antigo ganhando identidade real.
        """
        if not nome and not telefone:
            return None

        cliente = None
        if telefone:
            cliente = self.get_by_telefone(telefone)
        if cliente is None and nome:
            cliente = self.get_by_nome(nome)

        if cliente is None:
            cliente = ClienteModel(
                nome=nome,
                nome_normalizado=normalizar_texto(nome) if nome else None,
                telefone=normalizar_telefone(telefone) if telefone else None,
            )
            return self.add(cliente)

        mudou = False
        if telefone and not cliente.telefone:
            cliente.telefone = normalizar_telefone(telefone)
            mudou = True
        if nome and not cliente.nome:
            cliente.nome = nome
            cliente.nome_normalizado = normalizar_texto(nome)
            mudou = True
        if mudou:
            self.session.commit()
            self.session.refresh(cliente)
        return cliente
