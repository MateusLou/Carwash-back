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
