#!/usr/bin/env python3
"""
Hermes Render Lightweight Chat Web Interface
Fixed javascript frontend layout error.
"""
import importlib.util
import json
import os
import re
import sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import urllib.request

PORT = int(os.environ.get("PORT", 8080))
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

HTML_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hermes Inteligência Global</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f5f5f7; margin: 0; display: flex; flex-direction: column; height: 100vh; color: #1d1d1f; }
        .header { background-color: #fff; padding: 15px; text-align: center; font-weight: 600; border-bottom: 1px solid #e5e5ea; font-size: 16px; }
        .chat-container { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; }
        .message { max-width: 80%; padding: 12px 16px; border-radius: 18px; font-size: 15px; line-height: 1.4; word-wrap: break-word; }
        .user { background-color: #e9e9eb; align-self: flex-end; color: #000; border-bottom-right-radius: 4px; }
        .hermes { background-color: #007aff; align-self: flex-start; color: #fff; border-bottom-left-radius: 4px; }
        .error { background-color: #ffdad9; color: #410002; align-self: flex-start; border: 1px solid #ffb4ab; border-radius: 8px; font-family: monospace; }
        .footer { background-color: #fff; padding: 15px; border-top: 1px solid #e5e5ea; display: flex; flex-direction: column; gap: 10px; }
        .input-row { display: flex; gap: 10px; }
        textarea { flex: 1; border: 1px solid #d2d2d7; border-radius: 20px; padding: 10px 15px; resize: none; height: 24px; font-size: 15px; outline: none; }
        button { background-color: #007aff; color: #fff; border: none; border-radius: 50%; width: 44px; height: 44px; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: bold; }
        .checkbox-row { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #86868b; }
    </style>
</head>
<body>
    <div class="header">Groq grátis · Qwen 27B <span style="color:#34c759;font-size:12px;">● pronto</span></div>
    <div class="chat-container" id="chat">
        <div class="message hermes">Olá! Sou o Hermes. Como posso ajudar você hoje?</div>
    </div>
    <div class="footer">
        <div class="input-row">
            <textarea id="text" placeholder="Pergunte alguma coisa ao Hermes..."></textarea>
            <button id="send">↑</button>
        </div>
        <div class="checkbox-row">
            <input type="checkbox" id="memCheck" checked>
            <label for="memCheck">Usar memória privada nesta mensagem. Groq Free: limites diários.</label>
        </div>
    </div>
    <script>
        const chat = document.getElementById('chat');
        const text = document.getElementById('text');
        const send = document.getElementById('send');
        
        send.onclick = async () => {
            const val = text.value.trim();
            if(!val) return;
            
            text.value = '';
            appendMsg(val, 'user');
            
            // CORREÇÃO: Definição segura da variável de consentimento de memória
            const memCheckEl = document.getElementById('memCheck');
            const memoryConsent = memCheckEl ? memCheckEl.checked : false;
            
            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: val, memory: memoryConsent })
                });
                const data = await res.json();
                if(data.error) {
                    appendMsg(data.error, 'error');
                } else {
                    appendMsg(data.response, 'hermes');
                }
            } catch(e) {
                appendMsg('Erro de rede: ' + e.message, 'error');
            }
        };

        function appendMsg(txt, sender) {
            const m = document.createElement('div');
            m.className = 'message ' + sender;
            m.innerText = txt;
            chat.appendChild(m);
            chat.scrollTop = chat.scrollHeight;
        }
    </script>
</body>
</html>"""

class HermesHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/chat":
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            req_data = json.loads(body.decode('utf-8'))
            user_message = req_data.get("message", "")
            
            if not GROQ_API_KEY:
                self.send_json({"error": "GROQ_API_KEY não está configurada no Render."})
                return
                
            try:
                url = "https://groq.com"
                payload = {
                    "model": "qwen-2.5-coder-32b",
                    "messages": [{"role": "user", "content": user_message}]
                }
                req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'))
                req.add_header("Authorization", f"Bearer {GROQ_API_KEY}")
                req.add_header("Content-Type", "application/json")
                
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    ai_reply = res_data['choices'][0]['message']['content']
                    self.send_json({"response": ai_reply})
            except Exception as e:
                self.send_json({"error": f"Erro na Groq: {str(e)}"})
        else:
            self.send_error(404)

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

if __name__ == "__main__":
    print(f"Iniciando Hermes na porta {PORT}...")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), HermesHandler)
    server.serve_forever()

