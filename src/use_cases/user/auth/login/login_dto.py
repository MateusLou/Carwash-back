from pydantic import BaseModel


class LoginDTO(BaseModel):
    # Sem e-mail de propósito: o login do balcão é uma senha só, e é ela que
    # identifica a conta (ver LoginUseCase). Payload antigo com "email" junto
    # continua aceito — campo extra é ignorado.
    password: str
