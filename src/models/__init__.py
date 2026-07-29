"""Todos os models, num lugar só.

O `alembic/env.py` importa este pacote — é o import que registra cada model no
`Base.metadata`. Model que não passar por aqui fica invisível para o
autogenerate, e a migration sai vazia sem avisar.
"""

# schema public — o bot de WhatsApp e o login do painel
from .user_model import UserModel
from .agendamento_model import AgendamentoModel
from .conversa_model import ConversaModel

# schema operacao — a plataforma
from .cliente_model import ClienteModel
from .veiculo_model import VeiculoModel
from .funcionario_model import FuncionarioModel
from .lavagem_model import LavagemModel
from .importacao_model import ImportacaoModel

__all__ = [
    "UserModel",
    "AgendamentoModel",
    "ConversaModel",
    "ClienteModel",
    "VeiculoModel",
    "FuncionarioModel",
    "LavagemModel",
    "ImportacaoModel",
]
