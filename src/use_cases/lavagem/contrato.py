"""O termo de adesão que o cliente recebe no WhatsApp ao fazer o check-in.

O texto abaixo é a transcrição fiel de `CONTRATOS (1).pdf` — as treze cláusulas
estão verbatim, na ordem do original. **É para ser editado aqui** (o mesmo
combinado de `montar_mensagem_carro_pronto`): quando o advogado mudar uma
cláusula, é neste arquivo que ela muda.

O que o preenchimento faz, e só isso:
- as lacunas do PRESTADOR (CNPJ, sede, representante, RG, CPF, domicílio) vêm de
  `config["contratada"]`, que lê o `.env`;
- o bloco CLIENTE — que no original diz apenas "identificado(a) no momento da
  contratação" — ganha a identificação de verdade: os dados que o atendente
  acabou de coletar no check-in.

Fica em `use_cases/lavagem/`, e não em `utils/`, porque cláusula é regra de
negócio; o que é genérico (desenhar texto em A4) mora em `utils/gerar_pdf.py`.
E fica no nível do grupo, não dentro de `registrar_chegada/`, porque o reenvio
de contrato usa exatamente as mesmas funções.
"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

from config.config import config
from entities.vistoria import rotular_danos
from utils import storage_contratos
from utils.enviar_whatsapp import enviar_whatsapp_documento
from utils.gerar_pdf import gerar_pdf
from utils.normalizar_texto import formatar_cpf, formatar_telefone
from utils.storage_contratos import StorageIndisponivel

TITULO = (
    "TERMO DE ADESÃO DE PRESTAÇÃO DE SERVIÇOS DE ESTÉTICA AUTOMOTIVA "
    "E CUSTÓDIA TEMPORÁRIA"
)

# O relógio do lava-rápido. O banco guarda UTC; o documento imprime a hora da
# parede de São Paulo, que é a que cliente e atendente viram.
FUSO_SAO_PAULO = timezone(timedelta(hours=-3))

# (título da cláusula, parágrafos) — transcrição verbatim do CONTRATOS (1).pdf.
CLAUSULAS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "CLÁUSULA PRIMEIRA – DO OBJETO E NATUREZA JURÍDICA",
        (
            "1.1. Este contrato regula a prestação de serviços de lavagem, limpeza, "
            "higienização e estética automotiva, conforme descrito na Ordem de Serviço "
            "(OS) e Vistoria de Entrada.",
            "1.2. Durante a prestação dos serviços, o veículo permanecerá sob custódia "
            "temporária (depósito voluntário) do LAVA-RÁPIDO NOGUEIRA, nos termos dos "
            "arts. 627 e ss. do Código Civil Brasileiro.",
            "1.3. A identificação do cliente e do veículo constarão da Vistoria "
            "realizada pelo atendente.",
            "1.4. Os documentos que integram este contrato são: Checklist de Vistoria, "
            "Recibos de Custódia (se houver) e Comprovantes de Pagamento.",
        ),
    ),
    (
        "CLÁUSULA SEGUNDA – VISTORIA PRÉVIA E AVARIAS PRÉ-EXISTENTES",
        (
            "2.1. O CLIENTE reconhece que o estado externo e interno do veículo no ato "
            "da entrega corresponde às marcações do diagrama de vistoria realizada pelo "
            "atendente.",
            "2.2. O LAVA-RÁPIDO NOGUEIRA não responde por danos pré-existentes (riscos, "
            "arranhões, amassados, vidros trincados, peças faltando, pintura "
            "descascada) registrados na vistoria inicial, conforme art. 14, §3º, I, do "
            "Código de Defesa do Consumidor (CDC).",
            "2.3. CONTESTAÇÕES: Danos visíveis devem ser comunicados NO MOMENTO DA "
            "RETIRADA, com conferência conjunta. Silêncio nesse momento presume "
            "conformidade, sem prejuízo do direito de reclamar vícios ocultos (art. 26, "
            "§3º, CDC) mediante prova técnica do nexo causal com os serviços prestados.",
            "2.4. Se a equipe danificar ADICIONALMENTE uma área já lesionada, "
            "respondemos pela extensão do novo dano quando comprovado nexo causal "
            "(culpa).",
        ),
    ),
    (
        "CLÁUSULA TERCEIRA – CUSTÓDIA DE PERTENCES E OBJETOS DE VALOR",
        (
            "3.1. Recomenda-se RETIRAR antes da entrega: dinheiro, cartões, celular, "
            "documentos pessoais, jóias, óculos, bolsas e demais bens de valor.",
            "3.2. Se precisar deixar algo dentro do carro durante o serviço, DECLARE "
            "OBRIGATORIAMENTE no momento da vistoria efetuada pelo atendente ou emita "
            "Recibo de Custódia discriminando o bem.",
            "3.3. Respondemos APENAS por bens previamente declarados e registrados. "
            "Para bens não declarados, respondemos apenas se comprovada culpa de nossa "
            "equipe (roubo, perda por negligência).",
            "3.4. A custódia de objetos deixados sem declaração permanece sob "
            "responsabilidade do proprietário, sem prejuízo da responsabilidade "
            "criminal/civil da empresa se houver culpa comprovada de prepostos.",
        ),
    ),
    (
        "CLÁUSULA QUARTA – MANOBRAS, OPERAÇÃO E RESPONSABILIDADE POR DANOS",
        (
            "4.1. O CLIENTE autoriza a movimentação do veículo EXCLUSIVAMENTE para "
            "execução dos serviços, organização do pátio e entrega.",
            "4.2. Se o dano ao veículo ocorrer comprovadamente por culpa da equipe "
            "(negligência, imprudência, imperícia), o LAVA-RÁPIDO NOGUEIRA responde "
            "pela reparação integral, conforme legislação aplicável.",
            "4.3. O reparo será realizado em oficina indicada pelo LAVA-RÁPIDO NOGUEIRA "
            "ou, em desacordo, em oficina escolhida de comum acordo, com despesas por "
            "conta da empresa se reconhecida culpa.",
            "4.4. Pedidos por lucros cessantes, desvalorização comercial ou outros "
            "danos indiretos serão analisados caso a caso com demonstração técnica do "
            "nexo causal, conforme arts. 402-944 do CC.",
        ),
    ),
    (
        "CLÁUSULA QUINTA – COMPONENTES MODIFICADOS E CONDIÇÕES PRÉ-EXISTENTES",
        (
            "5.1. O LAVA-RÁPIDO NOGUEIRA não responde por desprendimentos, quebras ou "
            "danos que resultem EXCLUSIVAMENTE de: desgaste natural, ressecamento, "
            "corrosão, má fixação pré-existente, ou modificações estéticas/estruturais "
            "não originais (aerofólios, saias, películas, envelopamentos, acessórios "
            "aftermarket, suspensão rebaixada), desde que registradas na vistoria ou "
            "comprovadas como pré-existentes.",
            "5.2. Exceção: Se o dano decorrer de falha na execução do serviço (uso "
            "inadequado de produtos/equipamentos), o LAVA-RÁPIDO NOGUEIRA responde "
            "integralmente.",
        ),
    ),
    (
        "CLÁUSULA SEXTA – FALHAS MECÂNICAS E ELETRÔNICAS PRÉ-EXISTENTES",
        (
            "6.1. O LAVA-RÁPIDO NOGUEIRA não responde por panes elétricas, falhas "
            "mecânicas, bateria descarregada ou desregulagens de sistemas eletrônicos "
            "que ocorram por fim de vida útil ou defeitos pré-existentes durante "
            "permanência no pátio. A equipe comunicará imediatamente o cliente para "
            "constatação conjunta.",
        ),
    ),
    (
        "CLÁUSULA SÉTIMA – RETIRADA DO VEÍCULO E TAXA DE GUARDA",
        (
            "7.1. O CLIENTE compromete-se a retirar o veículo até às 17h00 (horário de "
            "encerramento das atividades).",
            "7.2. Permanecendo o veículo após 17h00, sem prévio ajuste, incidirá Taxa "
            "de Pernoite e Guarda de Pátio de 2% sobre o valor do serviço contratado, "
            "por dia completo ou fração, cobrada diariamente até efetiva retirada, sem "
            "prejuízo do pagamento dos serviços contratados.",
            "7.3. A retirada fica condicionada ao pagamento integral dos serviços e "
            "despesas de guarda regularmente previstos.",
            "7.4. Decorridos 30 dias da conclusão dos serviços SEM retirada e SEM "
            "manifestação, o LAVA-RÁPIDO NOGUEIRA notificará o cliente "
            "(WhatsApp/E-mail/Telefone) concedendo 10 dias adicionais. Persistindo a "
            "inércia, poderão ser adotadas medidas legais e administrativas cabíveis.",
            "7.5. Diárias de guarda serão devidas até efetiva retirada ou até adoção de "
            "medida judicial.",
        ),
    ),
    (
        "CLÁUSULA OITAVA – RETIRADA POR TERCEIROS",
        (
            "8.1. Liberação a terceiro (não o titular da vistoria) depende de "
            "AUTORIZAÇÃO PRÉVIA do cliente via WhatsApp ou E-mail, com indicação de "
            "nome completo e CPF do terceiro condutor.",
        ),
    ),
    (
        "CLÁUSULA NONA – PROTEÇÃO DE DADOS (LGPD - Lei nº 13.709/2018)",
        (
            "9.1. O CLIENTE autoriza coleta, armazenamento e tratamento de dados "
            "pessoais (nome, CPF, telefone, e-mail) EXCLUSIVAMENTE para: "
            "(a) execução deste contrato; "
            "(b) segurança física do pátio; "
            "(c) emissão de comprovantes; "
            "(d) cumprimento de obrigações legais.",
            "9.2. Fundamento legal: arts. 7º, II (contrato) e V (proteção de crédito) "
            "da LGPD..",
            "9.3. O cliente possui direitos: acessar dados (art. 18, I), corrigir dados "
            "incorretos (art. 18, III), deletar dados sem causa legítima (art. 17), via "
            "WhatsApp/E-mail de contato.",
            "9.4. Dados não serão compartilhados com terceiros sem consentimento, salvo "
            "obrigação legal ou requisição judicial.",
        ),
    ),
    (
        "CLÁUSULA DÉCIMA – SERVIÇOS ADICIONAIS",
        (
            "10.1. Serviços não constantes da contratação original exigem AUTORIZAÇÃO "
            "PRÉVIA do cliente via WhatsApp, e-mail, ligação ou outro meio que comprove "
            "manifestação de vontade.",
            "10.2. Autorizado, o serviço adicional será incluído no recibo único "
            "emitido ao final do serviço e cobrado conforme tabela de preços vigente na "
            "data da execução.",
        ),
    ),
    (
        "CLÁUSULA DÉCIMA PRIMEIRA – CANCELAMENTO DE SERVIÇOS",
        (
            "11.1. Cancelamento ANTES do início dos serviços: nenhuma cobrança, "
            "ressalvadas despesas previamente autorizadas e incorridas.",
            "11.2. Cancelamento APÓS o início: cliente paga pelos serviços já "
            "executados, observando a boa-fé.",
            "11.3. Impossibilidade técnica por culpa do cliente ou condições "
            "pré-existentes do veículo: cliente paga apenas pelos serviços já "
            "realizados, sendo comunicado imediatamente.",
        ),
    ),
    (
        "CLÁUSULA DÉCIMA SEGUNDA – DISPOSIÇÕES GERAIS",
        (
            "12.1. As partes obrigam-se a agir conforme boa-fé objetiva, cooperação, "
            "transparência e confiança recíproca.",
            "12.2. A nulidade de qualquer cláusula não prejudica as demais, que "
            "permanecerão vigentes.",
        ),
    ),
    (
        "CLÁUSULA DÉCIMA TERCEIRA – FORO COMPETENTE",
        (
            "13.1. Para dirimir quaisquer controvérsias oriundas deste contrato, as "
            "partes elegem o foro da Comarca de São Paulo, Estado de São Paulo, com "
            "renúncia expressa a qualquer outro foro, por mais privilegiado que seja.",
        ),
    ),
)


def montar_contrato_pdf(lavagem_model, agora: datetime) -> bytes:
    """O termo completo, com o PRESTADOR e o CLIENTE preenchidos.

    Recebe o model com `cliente` e `veiculo` já carregados (o check-in os tem em
    mãos) e lê tudo com getattr tolerante a nulo, como `Lavagem.com_nomes` — a
    geração nunca pode falhar por um campo que o atendente deixou para depois.
    """
    empresa = config["contratada"]

    prestador = (
        f"PRESTADOR DOS SERVIÇOS: {empresa['razao_social']}, pessoa jurídica de "
        f"direito privado, inscrita no CNPJ n° {empresa['cnpj']}, com sede na Rua "
        f"{empresa['sede_rua']}, Moema, São Paulo/SP, doravante denominada CONTRATADA "
        f"e neste ato representada na forma de seus atos constitutivos, por seu "
        f"representante legal {empresa['representante']}, portador do Documento de "
        f"Identidade RG nº. {empresa['representante_rg']}, inscrito no CPF sob o nº. "
        f"{empresa['representante_cpf']}, residente e domiciliado em "
        f"{empresa['representante_domicilio']}."
    )
    celebracao = (
        "Decidem as partes, na melhor forma de direito, celebrar o presente CONTRATO "
        "DE PRESTAÇÃO DE SERVIÇOS, que reger-se-á mediante as cláusulas e condições "
        "adiante estipuladas."
    )

    blocos: list = [
        ("paragrafo", prestador),
        ("paragrafo", celebracao),
        ("espaco", 2),
        # A frase original fica intacta; a identificação prometida por ela vem logo
        # abaixo, com o que o check-in coletou.
        (
            "paragrafo",
            "CLIENTE: Pessoa física ou jurídica que contrata os serviços de lavagem "
            "de veículos oferecidos pela prestadora, identificado(a) no momento da "
            "contratação.",
        ),
        ("paragrafo", _identificacao_do_cliente(lavagem_model, agora)),
        ("espaco", 2),
    ]

    for titulo_clausula, paragrafos in CLAUSULAS:
        blocos.append(("titulo", titulo_clausula))
        blocos.extend(("paragrafo", paragrafo) for paragrafo in paragrafos)

    return gerar_pdf(TITULO, blocos)


def _identificacao_do_cliente(lavagem_model, agora: datetime) -> str:
    """A identificação do cliente e do veículo, em texto corrido como o do PRESTADOR.

    Só entra o que foi coletado — campo vazio some da frase em vez de virar
    lacuna: linha em branco num documento já entregue convidaria a preencher
    depois.
    """
    cliente = getattr(lavagem_model, "cliente", None)
    veiculo = getattr(lavagem_model, "veiculo", None)

    nome = getattr(cliente, "nome", None)
    cpf = getattr(cliente, "cpf", None)
    telefone = getattr(cliente, "telefone", None)

    partes = [f"Para os fins deste termo, o CLIENTE é {nome}" if nome
              else "Para os fins deste termo, o CLIENTE é a pessoa"]
    if cpf:
        partes.append(f"inscrito(a) no CPF sob o nº {formatar_cpf(cpf)}")
    if telefone:
        partes.append(f"telefone {formatar_telefone(telefone)}")

    frase = ", ".join(partes)

    carro = _descricao_do_veiculo(lavagem_model, veiculo)
    if carro:
        frase += f", proprietário(a) ou condutor(a) do veículo {carro}"

    chegada = (lavagem_model.chegou_em or agora).astimezone(FUSO_SAO_PAULO)
    frase += (
        f", que entregou o veículo para o serviço \"{lavagem_model.servico}\" "
        f"em {chegada.strftime('%d/%m/%Y')} às {chegada.strftime('%H:%M')} "
        f"(atendimento nº {lavagem_model.id})."
    )

    avarias = rotular_danos(
        (lavagem_model.dados_extras or {}).get("vistoria", {}).get("danos")
    )
    if avarias:
        frase += (
            " Avarias pré-existentes registradas na vistoria de entrada: "
            + "; ".join(avarias)
            + "."
        )

    return frase


def _descricao_do_veiculo(lavagem_model, veiculo) -> str:
    pedacos = [
        pedaco
        for pedaco in (
            getattr(veiculo, "modelo", None),
            getattr(lavagem_model, "tipo_carro", None)
            or getattr(veiculo, "tipo", None),
        )
        if pedaco
    ]
    descricao = " ".join(pedacos)

    placa = getattr(veiculo, "placa", None)
    if placa:
        descricao = f"{descricao}, placa {placa}" if descricao else f"de placa {placa}"

    return descricao


def nome_arquivo_contrato(lavagem_id: int) -> str:
    """O nome que aparece na bolha do WhatsApp. Sem CPF: nome de arquivo vira print."""
    return f"contrato-lava-rapido-nogueira-{lavagem_id}.pdf"


def montar_legenda_whatsapp(nome: str | None) -> str:
    """O texto que acompanha o PDF na conversa. É para ser editado aqui."""
    saudacao = f"Oi, {nome.split()[0]}!" if nome and nome.strip() else "Oi!"
    return (
        f"{saudacao} Recebemos seu carro aqui no Lava-Rápido Nogueira. 🚗\n\n"
        "Este é o seu termo de adesão, já preenchido com os dados do "
        "atendimento — ele registra a vistoria de entrada e as condições do "
        "serviço. Qualquer dúvida, é só responder por aqui!"
    )


def emitir_contrato(lavagem_model, agora: datetime, telefone: str | None) -> dict:
    """Gera o PDF, arquiva no Storage e manda no WhatsApp — nesta ordem.

    Arquivar antes de enviar porque a cópia arquivada é o registro da empresa e
    o WhatsApp é a entrega; se o processo morrer no meio, sobra o estado que
    tem conserto (guardado e não enviado). Mas uma falha do Storage **não**
    segura o envio: o base64 não depende do bucket, e o cliente receber o
    contrato vale mais que a nossa cópia.

    Nunca levanta exceção — as duas pernas de rede já engolem as suas, e o que
    escapar é problema de quem chama (o use case embrulha tudo de novo).

    Returns:
        `{"enviada", "motivo", "caminho", "motivo_arquivo"}` — as duas
        primeiras no vocabulário de `enviar_whatsapp`; `caminho` é onde o PDF
        ficou no bucket (None se não ficou) e `motivo_arquivo` é
        `nao_configurado` ou `falha_storage` quando não ficou.
    """
    pdf = montar_contrato_pdf(lavagem_model, agora)

    caminho = None
    motivo_arquivo = None
    if storage_contratos.esta_configurado():
        try:
            caminho = storage_contratos.salvar(
                f"{agora:%Y/%m}/lavagem-{lavagem_model.id}-{uuid4().hex[:8]}.pdf", pdf
            )
        except StorageIndisponivel as erro:
            print(f"Contrato: arquivamento falhou ({erro})")
            motivo_arquivo = "falha_storage"
    else:
        motivo_arquivo = "nao_configurado"

    resultado = enviar_whatsapp_documento(
        telefone or "",
        pdf,
        nome_arquivo_contrato(lavagem_model.id),
        montar_legenda_whatsapp(getattr(lavagem_model.cliente, "nome", None)),
    )

    return {**resultado, "caminho": caminho, "motivo_arquivo": motivo_arquivo}
