from use_cases.importacao.upload_planilha.upload_planilha_use_case import UploadPlanilhaUseCase
from use_cases.importacao.motor_importacao import processar_upload
from repositories.importacao_repository import ImportacaoRepository
from middlewares.validate_dono_auth_token import validate_dono_auth_token
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Response, UploadFile
from sqlalchemy.orm import Session
from database.database import get_db

router = APIRouter()


@router.post("/importacoes", dependencies=[Depends(validate_dono_auth_token)])
async def upload_planilha(
    response: Response,
    background_tasks: BackgroundTasks,
    arquivo: UploadFile = File(...),
    substituir: bool = Form(False),
    db: Session = Depends(get_db),
):
    # Os bytes são lidos AQUI porque o UploadFile morre com o request — o
    # background task receberia um arquivo já fechado.
    conteudo = await arquivo.read()

    upload_planilha_use_case = UploadPlanilhaUseCase(ImportacaoRepository(db))
    resultado = upload_planilha_use_case.execute(arquivo.filename, conteudo, response)

    if resultado["status"] == "success":
        background_tasks.add_task(
            processar_upload,
            resultado["data"]["importacao_id"],
            conteudo,
            substituir,
        )
    return resultado
