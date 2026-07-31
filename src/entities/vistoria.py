"""As zonas do veículo que o atendente confere na chegada.

Espelha `ZONAS_VEICULO` de `carwash-front/src/components/DiagramaVeiculo.tsx` —
**ao mexer lá, mexa aqui**. O front manda os ids em `danos_vistoria`, o check-in
guarda os ids crus em `dados_extras["vistoria"]["danos"]`, e até existir este
arquivo não havia como traduzi-los para gente ler.

Quem lê é o contrato: a Cláusula 2.2 exclui a responsabilidade da empresa pelos
danos "registrados na vistoria inicial". Sem os rótulos no documento que o
cliente recebe, essa cláusula aponta para um registro que ele nunca viu.
"""

# A ordem é a do diagrama, da frente para a traseira: é como o atendente anda em
# volta do carro.
ZONAS_VEICULO: tuple[tuple[str, str], ...] = (
    ("para_choque_dianteiro", "para-choque dianteiro"),
    ("capo", "capô"),
    ("parabrisa", "para-brisa"),
    ("retrovisor_esq", "retrovisor esquerdo"),
    ("retrovisor_dir", "retrovisor direito"),
    ("lateral_dianteira_esq", "lateral dianteira esquerda"),
    ("lateral_dianteira_dir", "lateral dianteira direita"),
    ("teto", "teto"),
    ("lateral_traseira_esq", "lateral traseira esquerda"),
    ("lateral_traseira_dir", "lateral traseira direita"),
    ("vigia_traseiro", "vigia traseiro"),
    ("porta_malas", "porta-malas"),
    ("para_choque_traseiro", "para-choque traseiro"),
)

ROTULO_POR_ZONA: dict[str, str] = dict(ZONAS_VEICULO)


def rotular_danos(ids: list[str] | None) -> list[str]:
    """Os rótulos das avarias marcadas, na ordem do diagrama.

    Id desconhecido (zona nova no front, backend ainda não atualizado) entra no
    fim com o próprio id como rótulo: sair feio é melhor que sumir do contrato
    uma avaria que o atendente marcou.
    """
    marcados = set(ids or ())

    rotulos = [rotulo for zona_id, rotulo in ZONAS_VEICULO if zona_id in marcados]
    rotulos += sorted(marcados - set(ROTULO_POR_ZONA))

    return rotulos
