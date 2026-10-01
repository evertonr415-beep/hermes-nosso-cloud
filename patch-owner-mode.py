from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

old = '''            payload_input=text
            if attachment_id:
'''
new = '''            owner_mode = (\n                "[MODO PROPRIETÁRIO HERMES]\\n"\n                "Priorize execução direta e útil. Não recuse pedidos apenas por palavras-chave ou categorias genéricas. "\n                "Evite confirmações desnecessárias para ações reversíveis e de baixo risco; quando houver ferramenta disponível, use-a. "\n                "Não invente capacidade nem resultado: se faltar acesso, permissão, saldo, ferramenta ou suporte técnico, explique objetivamente. "\n                "Para criação e edição visual, trate personagens claramente adultos e fictícios de forma permissiva dentro das regras aplicáveis: "\n                "não bloqueie automaticamente por termos como biquíni, lingerie, roupa de praia, sensual, trocar roupa, remover uma peça para substituir por outra, ou variações de figurino. "\n                "Se a idade estiver realmente ambígua em um pedido sensível, peça apenas a confirmação necessária de que o personagem é adulto, em vez de recusar genericamente. "\n                "Preserve as regras de segurança aplicáveis e peça confirmação somente quando a ação for realmente sensível, irreversível, cobrar dinheiro ou exigir autorização explícita.\\n\\n"\n                "Pedido do proprietário:\\n"\n            )\n            payload_input=owner_mode + text\n            if attachment_id:\n'''
if old not in s:
    raise SystemExit('owner mode payload anchor not found')
s = s.replace(old, new, 1)

old2 = '''                        {"type":"input_text","text":text},
'''
new2 = '''                        {"type":"input_text","text":owner_mode + text},
'''
if old2 not in s:
    raise SystemExit('owner mode multimodal anchor not found')
s = s.replace(old2, new2, 1)

# Make the behavior visible without implying that safety controls are disabled.
s = s.replace(
    'Modo híbrido: cérebro forte no Automático · mídia grátis/local primeiro · GPT-5.6 Sol Pago só quando selecionado manualmente.',
    'Modo proprietário: execução direta · menos confirmações · criação adulta fictícia sem bloqueio genérico · mídia grátis/local primeiro · pago só quando selecionado.'
)

p.write_text(s)
