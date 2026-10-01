from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

# Keep the automatic route on the existing strong Hermes brain. This patch only
# changes presentation/metadata; it does not redirect automatic chat to local models.
s = s.replace('Automático · GPT-6 Sol', 'Automático · Inteligência forte')
s = s.replace('<span class="zerocost">Zero Cost Mode</span>', '<span class="zerocost">Mídia grátis primeiro</span>')
s = s.replace(
    'Zero Cost Mode: vídeo com imagem anexada é gerado localmente. Provider pago não é usado nesse caminho.',
    'Modo híbrido: cérebro forte no Automático · imagem, vídeo e ferramentas tentam recursos gratuitos/local primeiro.'
)
s = s.replace('provider = "GPT-6 Sol"', 'provider = "Hermes · inteligência forte"')

p.write_text(s)
