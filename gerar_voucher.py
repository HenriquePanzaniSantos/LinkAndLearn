from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import base64

# 1. Carregue sua chave privada
with open("privada.pem", "rb") as f:
    private_key = RSA.importKey(f.read())

def gerar_voucher_blindado(ra, nota, atividade_id):
    # Incluímos o ID da atividade na string de dados
    # Formato: RA:173218|NOTA:10|ATIV:35
    mensagem_texto = f"RA:{ra}|NOTA:{nota}|ATIV:{atividade_id}"
    mensagem_bytes = mensagem_texto.encode('utf-8')

    # Criar Assinatura Digital
    h = SHA256.new(mensagem_bytes)
    assinatura = pkcs1_15.new(private_key).sign(h)

    # O Voucher final é o Texto + Assinatura em Base64
    voucher_final = base64.b64encode(mensagem_bytes + assinatura).decode('utf-8')
    
    print(f"\n✅ Voucher Gerado para Atividade {atividade_id}")
    print(f"Código: {voucher_final}\n")

# EXEMPLO: Gere para o RA 173218, Nota 10 e Atividade 35
gerar_voucher_blindado("254260", "10", "13")

