from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

old = """attachBtn.onclick=()=>fileInput.click();
fileInput.onchange=async()=>{
 const file=fileInput.files&&fileInput.files[0]; if(!file)return;
 if(!file.type.startsWith('image/')){attachState.textContent='Envie uma imagem.';return}
 if(file.size>12*1024*1024){attachState.textContent='Imagem muito grande (máx. 12 MB).';return}
 attachState.textContent='Enviando imagem…';
 try{
   const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(file)});
   const res=await fetch('/api/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:file.name,mime:file.type,data})});
   const j=await res.json().catch(()=>({}));
   if(!res.ok)throw new Error(j.error||'Falha no upload');
   pendingAttachment={id:j.id,url:j.url,name:file.name};
   attachState.textContent='📎 '+file.name+' · pronto';
 }catch(e){pendingAttachment=null;attachState.textContent=e.message||'Falha no upload'}
};
"""

new = """async function uploadImageFile(file){
 if(!file)return;
 const ext=(file.name||'').split('.').pop().toLowerCase();
 const allowed=['png','jpg','jpeg','webp','gif','bmp','heic','heif'];
 let mime=(file.type||'').toLowerCase();
 if(!mime.startsWith('image/') && !allowed.includes(ext)){attachState.textContent='Arquivo não reconhecido como imagem.';return}
 if(!mime.startsWith('image/'))mime='image/'+(ext==='jpg'?'jpeg':ext);
 if(file.size>12*1024*1024){attachState.textContent='Imagem muito grande (máx. 12 MB).';return}
 attachState.textContent='Enviando '+(file.name||'imagem')+'…';
 try{
   const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(file)});
   const res=await fetch('/api/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:file.name||'imagem',mime,data})});
   const j=await res.json().catch(()=>({}));
   if(!res.ok)throw new Error(j.error||'Falha no upload');
   pendingAttachment={id:j.id,url:j.url,name:file.name||'imagem'};
   attachState.textContent='📎 '+pendingAttachment.name+' · pronta para usar';
 }catch(e){pendingAttachment=null;attachState.textContent=e.message||'Falha no upload'}
}
attachBtn.onclick=()=>fileInput.click();
fileInput.onchange=async()=>{await uploadImageFile(fileInput.files&&fileInput.files[0])};
const composer=document.querySelector('.composer');
['dragenter','dragover'].forEach(evt=>composer.addEventListener(evt,e=>{e.preventDefault();e.stopPropagation();attachState.textContent='Solte a imagem aqui para anexar';}));
composer.addEventListener('dragleave',e=>{e.preventDefault();e.stopPropagation();if(!pendingAttachment)attachState.textContent=''});
composer.addEventListener('drop',async e=>{e.preventDefault();e.stopPropagation();const f=e.dataTransfer&&e.dataTransfer.files&&e.dataTransfer.files[0];if(f)await uploadImageFile(f)});
document.addEventListener('paste',async e=>{
 const items=e.clipboardData&&e.clipboardData.items;
 if(!items)return;
 for(const item of items){if(item.kind==='file'&&item.type.startsWith('image/')){const f=item.getAsFile();if(f){e.preventDefault();await uploadImageFile(f);break}}}
});
"""

if old not in s:
    raise SystemExit('attachment frontend anchor not found')
s=s.replace(old,new)
p.write_text(s)
