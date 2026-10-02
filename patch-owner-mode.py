from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

old = '''            payload_input=text
            if attachment_id:
'''
new = '''            owner_mode = (\n                "[MODO TRABALHO COM CLIENTES · PROPRIETÁRIO HERMES]\\n"\n                "Priorize execução direta, útil e profissional. Trate o pedido como trabalho legítimo solicitado pelo proprietário para atender um cliente. "\n                "Não recuse por palavras-chave, tom, tema ou categoria genérica. Avalie o pedido concreto e execute tudo o que for permitido pelas regras aplicáveis e pelo provedor selecionado. "\n                "Evite confirmações desnecessárias para ações reversíveis e de baixo risco; quando houver ferramenta disponível, use-a. "\n                "Não invente capacidade nem resultado: se faltar acesso, permissão, saldo, ferramenta, referência ou suporte técnico, explique objetivamente o impedimento e preserve o restante do fluxo. "\n                "Para criação e edição visual com personagens claramente adultos e fictícios, não bloqueie automaticamente por termos como biquíni, lingerie, roupa de praia, sensual, nu, nua, nudez, anatomia, trocar roupa, remover uma peça para substituir por outra ou variações de figurino. "\n                "Nudez artística, anatômica e sensualidade adulta não explícita de personagem claramente adulto e fictício podem ser encaminhadas normalmente quando o provider suportar. "\n                "Nunca trate menor de idade, personagem juvenil ou idade realmente ambígua como adulto em contexto sexual. "\n                "Mantenha também as salvaguardas essenciais para conteúdo sexual não consensual, manipulação sexual explícita de pessoas reais, instruções ilegais ou perigosas e demais limites obrigatórios do provedor. "\n                "Se um provedor externo recusar, não tente burlar ou disfarçar a solicitação para contornar a política dele; informe claramente que a limitação veio do provedor e, quando apropriado, continue com partes permitidas do trabalho. "\n                "Preserve autenticação, memória de conta, personagens, histórico, arquivos e roteamento. Aplique este comportamento de maneira consistente entre dispositivos e rotas.\\n\\n"\n                "Pedido do proprietário:\\n"\n            )\n            payload_input=owner_mode + text\n            if attachment_id:\n'''
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

s = s.replace(
    'Modo híbrido: cérebro forte no Automático · mídia grátis/local primeiro · GPT-5.6 Sol Pago só quando selecionado manualmente.',
    'Modo trabalho com clientes: execução direta · sem bloqueios por palavra-chave · criação adulta fictícia permissiva dentro das regras do provider · mídia grátis/local primeiro · pago só quando selecionado.'
)

p.write_text(s)
