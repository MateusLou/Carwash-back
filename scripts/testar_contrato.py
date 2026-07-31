"""Gera contratos de exemplo em disco, sem rede e sem banco.

É o jeito de conferir o PDF a olho — paginação, acentos, a qualificação do
cliente — enquanto se ajusta o texto, e o mesmo papel de conferência que
`checar_conexao.py` tem para o banco (o projeto não tem suíte de testes).

    python scripts/testar_contrato.py [pasta-de-saida]

Sem argumento, grava em ./contratos-exemplo/.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

# O mesmo ajuste de path do app.py: os módulos importam a partir de src/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from use_cases.lavagem.contrato import montar_contrato_pdf  # noqa: E402


def _lavagem(**por_cima):
    """Uma lavagem de mentira com a cara do model — só os campos que o contrato lê."""
    base = dict(
        id=1234,
        servico="Lavagem completa",
        chegou_em=datetime(2026, 7, 30, 17, 30, tzinfo=timezone.utc),
        dados_extras={"vistoria": {"danos": ["capo", "retrovisor_esq"]}},
        cliente=SimpleNamespace(
            nome="José da Silva Sauro",
            cpf="52998224725",
            telefone="5511999998888",
        ),
        veiculo=SimpleNamespace(modelo="Onix", tipo="Hatch", placa="ABC1D23"),
        tipo_carro="Hatch",
    )
    base.update(por_cima)
    return SimpleNamespace(**base)


CASOS = {
    "completo": _lavagem(),
    "sem-nome": _lavagem(
        cliente=SimpleNamespace(nome=None, cpf="52998224725", telefone=None)
    ),
    "sem-veiculo": _lavagem(veiculo=None, tipo_carro=None),
    "sem-vistoria": _lavagem(dados_extras={}),
    "vistoria-cheia": _lavagem(
        dados_extras={
            "vistoria": {
                "danos": [
                    "para_choque_dianteiro", "capo", "parabrisa", "retrovisor_esq",
                    "retrovisor_dir", "lateral_dianteira_esq", "lateral_dianteira_dir",
                    "teto", "lateral_traseira_esq", "lateral_traseira_dir",
                    "vigia_traseiro", "porta_malas", "para_choque_traseiro",
                ]
            }
        }
    ),
    # Emoji e caractere fora do cp1252 no que o atendente digita: não pode quebrar.
    "texto-hostil": _lavagem(
        cliente=SimpleNamespace(
            nome="Zoë 山田 😀", cpf="52998224725", telefone="11 3222-1000"
        ),
        veiculo=SimpleNamespace(modelo="Corolla ✓", tipo=None, placa="XYZ9Z99"),
    ),
}


def main() -> int:
    destino = Path(sys.argv[1] if len(sys.argv) > 1 else "contratos-exemplo")
    destino.mkdir(parents=True, exist_ok=True)
    agora = datetime.now(timezone.utc)

    for nome, lavagem in CASOS.items():
        pdf = montar_contrato_pdf(lavagem, agora)
        arquivo = destino / f"contrato-{nome}.pdf"
        arquivo.write_bytes(pdf)
        print(f"  {arquivo}  ({len(pdf) / 1024:.1f} KB)")

    print(f"\n{len(CASOS)} contratos gerados. Abra e confira o texto e a paginação.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
