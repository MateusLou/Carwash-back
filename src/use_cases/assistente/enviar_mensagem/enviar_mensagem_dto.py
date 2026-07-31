from pydantic import BaseModel, ConfigDict


class EnviarMensagemDTO(BaseModel):
    """Uma pergunta do usuário para o assistente de gestão.

    O limite de tamanho é validado no use case (2000 caracteres após strip):
    a mensagem vira contexto do Gemini e entra na memória da conversa no n8n —
    um textão colado sem querer estouraria as duas coisas.
    """

    model_config = ConfigDict(extra="forbid")

    mensagem: str
