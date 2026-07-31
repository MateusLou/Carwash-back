import unicodedata
import re


def normalizar_texto(texto: str) -> str:
    """Minúsculas, sem acento, espaços colapsados.

    É a chave de deduplicação de clientes e funcionários na importação: a base
    escreve "Valdir (Val)" e "valdir (val)" como se fossem gente diferente, e
    sem telefone não há outro jeito de saber que é a mesma pessoa. O NFD separa
    a letra do acento e o \\p{Mn} remove só o acento.
    """
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def normalizar_telefone(telefone: str) -> str:
    """Só os dígitos, com o 55 do Brasil na frente.

    O bot do WhatsApp grava "5511999998888"; quem digita no check-in escreve
    "(11) 99999-8888". Sem passar pelos dois pelo mesmo filtro, o mesmo cliente
    vira dois cadastros e o cruzamento com os agendamentos não acontece.
    """
    digitos = re.sub(r"\D", "", telefone)
    if len(digitos) in (10, 11):  # DDD + número, sem código do país
        digitos = "55" + digitos
    return digitos


def normalizar_cpf(cpf) -> str:
    """Só os dígitos, com zeros à esquerda de volta.

    A planilha traz "414.594.609-01" e o check-in manda o que o atendente
    digitou; sem o mesmo filtro nos dois, o cliente importado nunca é
    reencontrado. O zfill existe porque CPF que começa com zero vira número em
    qualquer planilha — "012.345.678-90" volta como 12345678890 —, e o desvio
    do float pelo mesmo motivo: 12345678890.0 viraria 12 dígitos no str().
    """
    if isinstance(cpf, float) and cpf.is_integer():
        cpf = int(cpf)
    return re.sub(r"\D", "", str(cpf)).zfill(11)


def formatar_cpf(cpf) -> str:
    """O CPF com pontos e traço, como o cliente está acostumado a ver.

    O banco guarda só dígitos (`normalizar_cpf`); a máscara é assunto de quem
    exibe. Quem exibe hoje é o contrato — no PDF que vai para o WhatsApp, um
    "41459460901" corrido pareceria erro de sistema num documento que qualifica
    a parte. CPF com tamanho estranho volta como veio: melhor mostrar o dado
    torto do que escondê-lo atrás de uma máscara errada.
    """
    digitos = normalizar_cpf(cpf)
    if len(digitos) != 11:
        return str(cpf)
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def formatar_telefone(telefone: str) -> str:
    """O telefone em (DDD) 9NNNN-NNNN, sem o 55 do país.

    Espelha `formatarTelefone` do front. O 55 sai porque ele existe para a Z-API,
    não para o olho de quem lê. Número fora dos formatos conhecidos volta como
    veio.
    """
    digitos = re.sub(r"\D", "", telefone or "")
    if len(digitos) == 13 and digitos.startswith("55"):
        digitos = digitos[2:]
    elif len(digitos) == 12 and digitos.startswith("55"):
        digitos = digitos[2:]

    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
    return telefone


def cpf_valido(cpf) -> bool:
    """Confere os dois dígitos verificadores.

    Vale validar de verdade porque o CPF passou a ser a identidade do cliente:
    um dígito trocado não daria erro, daria um cadastro novo silencioso ao lado
    do certo. Os 795 CPFs da base histórica passam nesta conta.
    """
    digitos = normalizar_cpf(cpf)
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return False
    for corte in (9, 10):
        soma = sum(int(digitos[i]) * (corte + 1 - i) for i in range(corte))
        esperado = (soma * 10) % 11
        if esperado == 10:
            esperado = 0
        if esperado != int(digitos[corte]):
            return False
    return True
