"""Importa a planilha oficial de lavagens para o schema `operacao`.

    python scripts/importar_base.py --arquivo "../Base_lavagens_case.xlsx" --substituir

Invólucro fino do motor em `use_cases/importacao/motor_importacao.py` — a
MESMA carga que o upload do painel dispara, com as mesmas padronizações
(data em três formatos, preço com vírgula, categorias) e o mesmo tratamento
multi-aba: toda aba com as colunas obrigatórias entra, as demais são listadas.

Reimportar o mesmo arquivo não duplica nada (`id_externo` + ON CONFLICT DO
NOTHING). O `--substituir` apaga as lavagens `origem='importacao'` e recarrega
tudo numa transação só — check-ins da plataforma, clientes e funcionários
ficam. É o modo da primeira carga da base nova, cujos ids coincidem com os da
carga antiga. Destrutivo, por isso atrás de confirmação digitada.
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from database.database import SessionLocal  # noqa: E402
from models.importacao_model import ImportacaoModel  # noqa: E402
from models.lavagem_model import LavagemModel  # noqa: E402
from use_cases.importacao.motor_importacao import LOTE_PADRAO, importar_planilha  # noqa: E402


def confirmar_substituicao(session) -> None:
    """O que o --substituir vai apagar, na tela, antes da confirmação digitada."""
    importadas = (
        session.query(LavagemModel).filter(LavagemModel.origem == "importacao").count()
    )
    preservadas = (
        session.query(LavagemModel).filter(LavagemModel.origem != "importacao").count()
    )
    print(f"\n⚠️  --substituir vai APAGAR {importadas:,} lavagens importadas e recarregar do arquivo.")
    print(f"   Ficam: {preservadas:,} lavagens da plataforma (check-ins), clientes e funcionários.")

    if input('\ndigite "SUBSTITUIR" para confirmar: ').strip() != "SUBSTITUIR":
        print("cancelado.")
        raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arquivo", required=True, help="caminho do .xlsx")
    parser.add_argument(
        "--abas",
        action="append",
        default=None,
        help="importa só esta aba (repetível); sem a flag, todas as abas válidas",
    )
    parser.add_argument("--lote", type=int, default=LOTE_PADRAO)
    parser.add_argument(
        "--substituir",
        action="store_true",
        help="APAGA as lavagens importadas antes de recarregar (transação única)",
    )
    args = parser.parse_args()

    caminho = Path(args.arquivo).expanduser().resolve()
    if not caminho.exists():
        print(f"arquivo não encontrado: {caminho}")
        return 1

    session = SessionLocal()
    if args.substituir:
        confirmar_substituicao(session)

    aba = args.abas[0] if args.abas and len(args.abas) == 1 else None
    importacao = ImportacaoModel(arquivo=caminho.name, aba=aba, status="processando")
    session.add(importacao)
    session.commit()
    session.refresh(importacao)

    try:
        resultado = importar_planilha(
            caminho,
            session,
            importacao.id,
            substituir=args.substituir,
            apenas_abas=args.abas,
            tamanho_lote=args.lote,
        )

        importacao.status = "concluida"
        importacao.linhas_lidas = resultado.lidas
        importacao.linhas_inseridas = resultado.inseridas
        importacao.linhas_ignoradas = resultado.ignoradas
        importacao.detalhes = resultado.como_detalhes()
        importacao.concluida_em = datetime.now(timezone.utc)
        session.commit()

        print(f"arquivo ....... {caminho.name}  (modo {resultado.modo})")
        if resultado.lavagens_removidas:
            print(f"removidas ..... {resultado.lavagens_removidas:,} (carga anterior)")
        for parcial in resultado.abas:
            print(
                f"  {parcial.aba:<20} {parcial.lidas:>7,} lidas | "
                f"{parcial.inseridas:>7,} inseridas | {parcial.ignoradas:>7,} ignoradas"
            )
            avisos = parcial.como_dict()["avisos"]
            problemas = {k: v for k, v in avisos.items() if v}
            if problemas:
                print(f"    avisos: {problemas}")
        for pulada in resultado.abas_puladas:
            print(f"  {pulada['aba']:<20} PULADA — {pulada['motivo']}")
        print(f"totais ........ {resultado.lidas:,} lidas | {resultado.inseridas:,} inseridas | "
              f"{resultado.ignoradas:,} ignoradas (já estavam no banco, por id_externo)")
        print(f"cadastros ..... {resultado.clientes_novos:,} clientes e "
              f"{resultado.funcionarios_novos:,} funcionários novos")
        print(f"importação #{importacao.id} concluída")
        return 0

    except Exception as erro:  # noqa: BLE001
        session.rollback()
        importacao.status = "erro"
        importacao.erro = str(erro)[:2000]
        importacao.concluida_em = datetime.now(timezone.utc)
        session.commit()
        print(f"\nfalhou: {erro}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    raise SystemExit(main())
