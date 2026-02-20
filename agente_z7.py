import os
import json
import requests
from flask import Flask, request, Response, send_from_directory

app = Flask(__name__, static_folder="static")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """Você é o Agente Z7, assistente inteligente do Grupo Z7 (empresa de segurança, automação, redes e iluminação no Espírito Santo, Brasil).

Você tem acesso à internet e sempre responde com informações atualizadas de 2025/2026.

Você é especialista em:
- Criar descrições e anúncios profissionais de produtos e equipamentos
- Gerar copies para WhatsApp, Facebook e Instagram
- Criar hashtags relevantes
- Organizar e corrigir textos
- Câmeras de segurança, automação, redes, iluminação
- Anúncios para maquinários e equipamentos pesados

Sempre responda em português brasileiro, de forma profissional e clara.
Ao criar anúncios, entregue versões separadas para WhatsApp, Instagram e Facebook.
Inclua hashtags em posts para redes sociais."""

SEARCH_KEYWORDS = [
    "hoje", "atual", "atualmente", "2025", "2026", "recente", "novo", "nova",
    "lançamento", "melhor", "quais", "existe", "existem", "disponível",
    "preço", "quanto custa", "api", "ferramenta", "software", "ia ", "inteligência artificial",
    "modelo", "versão", "novidade", "tendência", "mercado"
]

def needs_search(text):
    return any(kw in text.lower() for kw in SEARCH_KEYWORDS)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        resp = Response()
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp

    body = request.get_json()
    user_messages = body.get("messages", [])
    last_msg = user_messages[-1]["content"] if user_messages else ""
    use_web = needs_search(last_msg)
    model = "compound-beta" if use_web else "llama-3.3-70b-versatile"

    def generate():
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_messages

            if use_web:
                yield f"data: {json.dumps({'content': '🌐 Buscando informações atualizadas...\\n\\n', 'done': False})}\n\n"
                print(f"  MODELO: compound-beta (web search)")
            else:
                print(f"  MODELO: llama-3.3-70b")

            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "max_tokens": 2048,
                "temperature": 0.7
            }

            with requests.post(GROQ_URL, headers=headers, json=payload, stream=True, timeout=60) as resp:
                if resp.status_code != 200:
                    print(f"  FALLBACK: {resp.status_code} — trocando para llama")
                    payload["model"] = "llama-3.3-70b-versatile"
                    resp = requests.post(GROQ_URL, headers=headers, json=payload, stream=True, timeout=60)

                for line in resp.iter_lines():
                    if not line:
                        continue
                    line = line.decode("utf-8")
                    if not line.startswith("data: "):
                        continue
                    chunk_data = line[6:]
                    if chunk_data == "[DONE]":
                        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                        break
                    try:
                        chunk = json.loads(chunk_data)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield f"data: {json.dumps({'content': delta, 'done': False})}\n\n"
                    except:
                        continue

        except Exception as e:
            yield f"data: {json.dumps({'content': f'[Erro: {str(e)}]', 'done': True})}\n\n"
            print(f"ERRO: {e}")

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": "*"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7070))
    print("=" * 50)
    print("  Agente Z7 — Groq + Web Search")
    print(f"  URL: http://0.0.0.0:{port}")
    print("  Modelo: llama-3.3-70b + compound-beta")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port)
