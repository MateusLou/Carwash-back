"""Texto corrido em A4, com quebra de página automática.

Não sabe o que é um contrato: recebe blocos — título de seção ou parágrafo — e
devolve os bytes do PDF. Quem sabe o que vai escrito é
`use_cases/lavagem/contrato.py`.

É o único arquivo do projeto que importa `fpdf`. Trocar de biblioteca é
reescrever este arquivo e nada mais.

Sobre a escolha do fpdf2 e não do reportlab: o `requirements.txt` documenta três
quebras deste projeto com wheel compilada sob Python 3.13 (SQLAlchemy, psycopg2,
pydantic). O fpdf2 é `py3-none-any` — Python puro, não falha pelo motivo que já
falhou três vezes aqui. E o `multi_cell` escreve o texto literalmente, enquanto
o `Paragraph` do reportlab interpreta mini-HTML: o nome do cliente e as
observações vêm de campo livre digitado no balcão, e um `&` esquecido quebraria
o documento.
"""

import unicodedata
from io import BytesIO

from fpdf import FPDF

# ("titulo" | "paragrafo" | "espaco", conteúdo)
Bloco = tuple[str, object]

FONTE = "Helvetica"
MARGEM_MM = 25
ALTURA_LINHA_MM = 4.8


def _cp1252(texto: str) -> str:
    """O que as fontes core do PDF conseguem escrever.

    Elas são cp1252, que cobre todo o português (acentos, cedilha, o travessão
    dos títulos das cláusulas e as aspas curvas). O que fica de fora é emoji e
    alfabeto não-latino — e nada disso pode derrubar um check-in, então cada
    caractere impossível vira sua versão sem acento e, se nem isso existir, um
    `?`.

    Caminho rápido primeiro: no uso normal, o texto inteiro passa direto.
    """
    try:
        texto.encode("cp1252")
        return texto
    except UnicodeEncodeError:
        pass

    saida = []
    for caractere in texto:
        try:
            caractere.encode("cp1252")
            saida.append(caractere)
        except UnicodeEncodeError:
            decomposto = "".join(
                c
                for c in unicodedata.normalize("NFKD", caractere)
                if not unicodedata.combining(c)
            )
            saida.append(decomposto.encode("cp1252", "replace").decode("cp1252"))
    return "".join(saida)


def gerar_pdf(titulo: str, blocos: list[Bloco]) -> bytes:
    """Os bytes de um PDF A4 com o título centralizado e os blocos, na ordem dada.

    O layout imita o documento original do Word: mesma margem generosa, títulos
    de cláusula em negrito, parágrafos justificados.
    """
    pdf = FPDF(format="A4", unit="mm")
    # O padrão do fpdf2 é latin-1, que não tem o travessão dos títulos das
    # cláusulas nem aspas curvas; cp1252 tem os dois e é o alvo do _cp1252.
    pdf.core_fonts_encoding = "windows-1252"
    pdf.set_auto_page_break(auto=True, margin=MARGEM_MM)
    pdf.set_margins(MARGEM_MM, MARGEM_MM, MARGEM_MM)
    pdf.add_page()

    pdf.set_font(FONTE, "B", 11.5)
    pdf.multi_cell(0, 6, _cp1252(titulo), align="C")
    pdf.ln(6)

    for tipo, conteudo in blocos:
        if tipo == "titulo":
            pdf.ln(3)
            pdf.set_font(FONTE, "B", 10)
            pdf.multi_cell(0, ALTURA_LINHA_MM + 0.4, _cp1252(str(conteudo)))
            pdf.ln(1.5)
        elif tipo == "paragrafo":
            pdf.set_font(FONTE, "", 10)
            pdf.multi_cell(0, ALTURA_LINHA_MM, _cp1252(str(conteudo)), align="J")
            pdf.ln(1.8)
        elif tipo == "espaco":
            pdf.ln(float(conteudo))
        else:  # pragma: no cover - erro de programação, não de dado
            raise ValueError(f"Bloco desconhecido no PDF: {tipo!r}")

    saida = BytesIO()
    pdf.output(saida)
    return saida.getvalue()
