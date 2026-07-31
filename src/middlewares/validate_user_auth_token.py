import os
import jwt
from fastapi import Request, Response, HTTPException

def validate_user_auth_token(request: Request, response: Response):
    token = request.cookies.get("user_auth_token")

    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        payload = jwt.decode(token.split(" ")[1], os.getenv("USER_JWT_SECRET"), algorithms=["HS256"])

        user_id = payload.get("id")
        user_email = payload.get("email")
        # role ausente em token antigo (o do n8n do assistente, por exemplo)
        # vira None — os guards tratam None como funcionário, nunca como dono.
        request.state.auth_payload = {
            "user_id": user_id,
            "user_email": user_email,
            "role": payload.get("role"),
        }

    except jwt.PyJWTError:
        response.delete_cookie("user_auth_token")

        raise HTTPException(status_code=401, detail="Invalid JWT token")
    
    return True
