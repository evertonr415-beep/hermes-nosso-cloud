from pathlib import Path

p=Path('/app/hermes-simple.py')
s=p.read_text()

# Add a compact recovery control style.
css_anchor='.generated-video{display:block;max-width:min(100%,720px);width:100%;border-radius:14px;border:1px solid var(--line);margin-top:10px;box-shadow:var(--shadow);background:#000}\n'
css_insert=css_anchor + '.media-recover{display:none;margin-top:9px;border:1px solid #d7d7d2;background:#fff;color:#222;border-radius:9px;padding:8px 11px;cursor:pointer;font-size:12px}.media-recover:hover{background:#f2f2ef}.media-recover.busy{opacity:.55;pointer-events:none}\n'
if css_anchor not in s:
    raise SystemExit('recovery css anchor not found')
s=s.replace(css_anchor,css_insert,1)

# Render messages with an index so a failed old image can recover from the nearest preceding user prompt.
old=""" chat.innerHTML=c.messages.map(m=>{\n   const role=m.role==='assistant'?'<div class=\"role\">Hermes</div>':'';\n   const body=m.error?'<div class=\"err\">'+esc(m.text)+'</div>':linkifyText(m.text);\n   let media='';\n   const u=m.imageUrl || ((m.role==='assistant' && m.routeMeta && m.routeMeta.category==='Imagem')?firstUrl(m.text):null);\n   if(u) media+='<img class=\"generated-image\" src=\"'+esc(u)+'\" alt=\"Imagem\" onclick=\"window.open(this.src, \\\'_blank\\\')\" onerror=\"this.style.display=\\\'none\\\'\"/>';\n   if(m.videoUrl) media+='<video class=\"generated-video\" src=\"'+esc(m.videoUrl)+'\" controls playsinline preload=\"metadata\"></video>';\n   if(m.attachmentUrl) media+='<img class=\"generated-image\" src=\"'+esc(m.attachmentUrl)+'\" alt=\"Imagem anexada\"/>';\n   return '<div class=\"msg '+m.role+'\"><div class=\"bubble\">'+role+body+media+'</div></div>';\n }).join('');\n"""
new=""" chat.innerHTML=c.messages.map((m,mi)=>{\n   const role=m.role==='assistant'?'<div class=\"role\">Hermes</div>':'';\n   const body=m.error?'<div class=\"err\">'+esc(m.text)+'</div>':linkifyText(m.text);\n   let media='';\n   const u=m.imageUrl || ((m.role==='assistant' && m.routeMeta && m.routeMeta.category==='Imagem')?firstUrl(m.text):null);\n   if(u){\n     const recovery='<button class=\"media-recover\" id=\"recover-'+mi+'\" onclick=\"regenerateLostImage('+mi+')\">↻ Regenerar imagem perdida</button>';\n     media+='<img class=\"generated-image\" src=\"'+esc(u)+'\" alt=\"Imagem\" onclick=\"window.open(this.src, \\\'_blank\\\')\" onerror=\"this.style.display=\\\'none\\\';const b=document.getElementById(\\\'recover-'+mi+'\\\');if(b)b.style.display=\\\'inline-block\\\'\"/>'+recovery;\n   }\n   if(m.videoUrl) media+='<video class=\"generated-video\" src=\"'+esc(m.videoUrl)+'\" controls playsinline preload=\"metadata\"></video>';\n   if(m.attachmentUrl) media+='<img class=\"generated-image\" src=\"'+esc(m.attachmentUrl)+'\" alt=\"Imagem anexada\"/>';\n   return '<div class=\"msg '+m.role+'\"><div class=\"bubble\">'+role+body+media+'</div></div>';\n }).join('');\n"""
if old not in s:
    raise SystemExit('render recovery anchor not found')
s=s.replace(old,new,1)

# Regenerate using the original prompt immediately preceding the failed assistant image.
js_anchor='function titleFrom(s){s=(s||\'\').trim().replace(/\\s+/g,\' \');return s.length>38?s.slice(0,38)+\'…\':s||\'Nova conversa\'}\n'
js_insert=js_anchor + r'''async function regenerateLostImage(messageIndex){
 const c=current(); if(!c||!c.messages||!c.messages[messageIndex])return;
 let prompt='';
 for(let i=messageIndex-1;i>=0;i--){if(c.messages[i].role==='user'&&c.messages[i].text){prompt=c.messages[i].text;break}}
 if(!prompt){alert('Não encontrei o pedido original dessa imagem.');return}
 const btn=document.getElementById('recover-'+messageIndex);
 if(btn){btn.classList.add('busy');btn.textContent='Regenerando…'}
 statusEl.textContent='regenerando imagem…';
 try{
   const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({input:prompt,conversation:c.id,route:'auto'})});
   const data=await res.json().catch(()=>({}));
   if(!res.ok)throw new Error(data.error||'Falha ao regenerar imagem');
   const m=c.messages[messageIndex];
   m.text=data.text||m.text||'Imagem regenerada.';
   m.routeMeta=data.routeMeta||m.routeMeta||{category:'Imagem'};
   m.imageUrl=data.imageUrl||null;
   if(!m.imageUrl)throw new Error('O gerador não retornou uma nova imagem.');
   save();render();
 }catch(e){
   if(btn){btn.classList.remove('busy');btn.textContent='↻ Tentar novamente'}
   alert(e.message||'Não foi possível regenerar a imagem.');
 }finally{statusEl.textContent='pronto · estável'}
}
'''
if js_anchor not in s:
    raise SystemExit('recovery js anchor not found')
s=s.replace(js_anchor,js_insert,1)

p.write_text(s)
print('lost image recovery patch applied')
