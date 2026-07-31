"""Uma Z-API de mentira em localhost, para testar envio sem mandar mensagem real.

O comentário no topo de `utils/enviar_whatsapp.py` promete exatamente isto:
apontar `ZAPI_BASE_URL` para um servidor local e conferir a requisição sem falar
com a Z-API. No `.env`:

    ZAPI_BASE_URL="http://localhost:8099"

Aceita os dois endpoints que o backend usa (`send-text` e `send-document/pdf`),
imprime o que chegou e, quando vem documento, decodifica o base64 e grava o PDF
ao lado — abra e confira que é o contrato. Rejeita com 400 documento que não
venha como data URI de PDF: um refactor que derrubasse o prefixo quebraria aqui,
em dev, e não em silêncio na produção.

    python scripts/zapi_falso.py [porta]
"""

import base64
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PREFIXO_PDF = "data:application/pdf;base64,"


class ZapiFalsa(BaseHTTPRequestHandler):
    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        rota = self.path.rsplit("/", 1)[-1] if "/send-text" in self.path else "documento"

        print(f"\n→ POST {self.path}")
        print(f"  Client-Token: {'presente' if self.headers.get('Client-Token') else 'AUSENTE'}")
        print(f"  phone: {corpo.get('phone')}")

        if "/send-document/" in self.path:
            documento = corpo.get("document", "")
            if not documento.startswith(PREFIXO_PDF):
                print("  ✗ document não é data URI de PDF — recusando")
                self._responder(400, {"error": "document deve ser data:application/pdf;base64,..."})
                return
            pdf = base64.b64decode(documento[len(PREFIXO_PDF):])
            arquivo = Path(corpo.get("fileName") or "documento-recebido.pdf")
            arquivo.write_bytes(pdf)
            print(f"  fileName: {corpo.get('fileName')}")
            print(f"  caption: {(corpo.get('caption') or '')[:80]}...")
            print(f"  ✓ PDF de {len(pdf) / 1024:.1f} KB gravado em ./{arquivo}")
        else:
            print(f"  message: {(corpo.get('message') or '')[:80]}")

        self._responder(200, {"zaapId": "falso", "messageId": "falso"})

    def _responder(self, status: int, corpo: dict):
        dados = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def log_message(self, *args):  # o print acima já conta a história
        pass


if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    print(f"Z-API falsa em http://localhost:{porta} — Ctrl+C para parar")
    HTTPServer(("localhost", porta), ZapiFalsa).serve_forever()
