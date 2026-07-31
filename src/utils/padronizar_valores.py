"""Padronização dos valores da planilha oficial de lavagens.

A planilha multi-aba escreve o mesmo fato de vários jeitos — a data em três
formatos, o preço com vírgula decimal, "Pick-up" e "picape" para o mesmo carro.
Sem este filtro a carga aborta (data BR), o Postgres rejeita o preço em
Numeric, e o dashboard mostra 22 fatias onde existem 5 categorias.

Tudo aqui é função pura sobre um valor de célula: quem conta avisos e decide o
destino da linha é o motor de importação.
"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from utils.normalizar_texto import normalizar_texto

# Chaves já passadas por normalizar_texto (minúsculas, sem acento, espaços
# colapsados) — a mesma régua da deduplicação de nomes, para as 22 grafias
# observadas de cada campo caírem nas mesmas entradas.
TIPOS_CARRO_CANONICOS: dict[str, str] = {
    "hatch": "Hatch",
    "seda": "Sedã",
    "sedan": "Sedã",
    "suv": "SUV",
    "picape": "Picape",
    "pick-up": "Picape",
    "pick up": "Picape",
    "pickup": "Picape",
    "utilitario": "Utilitário",
}

METODOS_PAGAMENTO_CANONICOS: dict[str, str] = {
    "dinheiro": "Dinheiro",
    "cartao de credito": "Cartão de crédito",
    "credito": "Cartão de crédito",
    "cartao de debito": "Cartão de débito",
    "debito": "Cartão de débito",
    "pix": "Pix",
    "fiado": "Fiado",
    "fiado/mensal": "Fiado",
    "fiado mensal": "Fiado",
}


def padronizar_data(valor, ano: int | None = None, mes: int | None = None
                    ) -> tuple[date | None, bool]:
    """A data da célula como `date`, em qualquer dos três formatos da planilha.

    Devolve `(data, foi_mm_dd)`. A planilha alterna entre datetime real, texto
    ISO e texto dd/mm/aaaa conforme a aba — e texto com barra é ambíguo, por
    isso as colunas `ano`/`mes` da própria linha (que não persistimos) servem
    de gabarito: se a leitura dd/mm diverge delas, tenta-se mm/dd, e o segundo
    booleano avisa que foi esse o caminho. Irrecuperável devolve `(None, _)` —
    a decisão de pular a linha é do motor.
    """
    if valor is None:
        return None, False
    if isinstance(valor, datetime):
        return valor.date(), False
    if isinstance(valor, date):
        return valor, False

    texto = str(valor).strip()
    if not texto:
        return None, False

    if "/" not in texto:
        try:
            return date.fromisoformat(texto[:10]), False
        except ValueError:
            return None, False

    def _bate(d: date) -> bool:
        return (ano is None or d.year == ano) and (mes is None or d.month == mes)

    dd_mm = _tentar(texto, "%d/%m/%Y")
    if dd_mm is not None and _bate(dd_mm):
        return dd_mm, False
    mm_dd = _tentar(texto, "%m/%d/%Y")
    if mm_dd is not None and _bate(mm_dd):
        return mm_dd, True
    # Sem gabarito para desempatar, dd/mm é o formato da casa.
    if dd_mm is not None and ano is None and mes is None:
        return dd_mm, False
    return None, False


def _tentar(texto: str, formato: str) -> date | None:
    try:
        return datetime.strptime(texto, formato).date()
    except ValueError:
        return None


def padronizar_preco(valor) -> Decimal | None:
    """O preço como Decimal com dois centavos, venha float, int ou "45,05".

    Decimal em vez de float porque a coluna é Numeric(10,2): 45.05 em float é
    45.0500000000000007 e estoura a precisão no Postgres. O quantize fecha em
    centavos de uma vez. Texto ilegível devolve None — a lavagem existe mesmo
    sem preço legível, quem conta o aviso é o motor.
    """
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    texto = str(valor).strip().removeprefix("R$").strip()
    if not texto:
        return None
    if "," in texto:
        # vírgula decimal → ponto; um ponto anterior só pode ser milhar
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None


def padronizar_categoria(valor, mapa: dict[str, str]) -> tuple[str | None, bool]:
    """O valor canônico de uma categoria, e se a grafia era conhecida.

    Devolve `(canonico, conhecida)`. Grafia fora do mapa não derruba nada:
    entra limpa (espaços colapsados, inicial maiúscula) e com `conhecida=False`
    para o motor listar no resumo — é assim que um "Boleto" futuro aparece para
    o dono em vez de sumir ou quebrar a carga.
    """
    if valor is None:
        return None, True
    texto = re.sub(r"\s+", " ", str(valor)).strip()
    if not texto:
        return None, True

    canonico = mapa.get(normalizar_texto(texto))
    if canonico is not None:
        return canonico, True
    return texto.capitalize(), False
