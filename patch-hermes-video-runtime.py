from pathlib import Path

sessions = Path('/opt/hermes/hermes_cli/web_routers/sessions.py')
text = sessions.read_text(encoding='utf-8')

# Extend the restricted media roots and MIME map created by patch-hermes-web-runtime.py.
text = text.replace(
    '    Path("/opt/data/image_cache"),\n)',
    '    Path("/opt/data/image_cache"),\n    Path("/opt/data/cache/videos"),\n)',
    1,
)
text = text.replace(
    '        ".avif": "image/avif",\n    }',
    '        ".avif": "image/avif",\n        ".mp4": "video/mp4",\n        ".webm": "video/webm",\n        ".m4v": "video/x-m4v",\n        ".mov": "video/quicktime",\n    }',
    1,
)
text = text.replace('Unsupported generated image type', 'Unsupported generated media type')
sessions.write_text(text, encoding='utf-8')

web_dist = Path('/opt/hermes/hermes_cli/web_dist')
renderer = web_dist / 'hermes-media-renderer.js'
js = renderer.read_text(encoding='utf-8')

# Replace the image-only regex with one that recognizes generated images and videos.
old_re = 'const MEDIA_RE = /MEDIA:((?:\\/opt\\/data\\/(?:cache\\/images|image_cache)\\/)[^\\n\\r\\"\'<>]+?\\.(?:png|jpe?g|webp|gif|svg|avif))/ig;'
new_re = 'const MEDIA_RE = /MEDIA:((?:\\/opt\\/data\\/(?:cache\\/images|image_cache|cache\\/videos)\\/)[^\\n\\r\\"\'<>]+?\\.(?:png|jpe?g|webp|gif|svg|avif|mp4|webm|m4v|mov))/ig;'
if old_re in js:
    js = js.replace(old_re, new_re, 1)

# Replace the image-only factory with a media-aware one.
start = js.index('  function makeImage(path) {')
end = js.index('\n  function renderTextNode(node) {', start)
new_factory = r'''  function makeImage(path) {
    const wrap = document.createElement("span");
    wrap.className = "hermes-nosso-media";
    wrap.dataset.hermesNossoMedia = VERSION;
    wrap.style.display = "block";
    wrap.style.margin = "10px 0";

    const src = "/api/hermes-nosso/media?path=" + encodeURIComponent(path);
    const isVideo = /\.(?:mp4|webm|m4v|mov)$/i.test(path);

    if (isVideo) {
      const video = document.createElement("video");
      video.src = src;
      video.controls = true;
      video.playsInline = true;
      video.preload = "metadata";
      video.style.display = "block";
      video.style.maxWidth = "min(100%, 1024px)";
      video.style.maxHeight = "75vh";
      video.style.borderRadius = "12px";
      video.style.background = "#000";
      video.style.boxShadow = "0 1px 3px rgba(0,0,0,.18)";
      wrap.appendChild(video);
      return wrap;
    }

    const img = document.createElement("img");
    img.src = src;
    img.alt = "Mídia gerada pelo Hermes";
    img.loading = "lazy";
    img.style.display = "block";
    img.style.maxWidth = "min(100%, 1024px)";
    img.style.maxHeight = "75vh";
    img.style.objectFit = "contain";
    img.style.borderRadius = "12px";
    img.style.boxShadow = "0 1px 3px rgba(0,0,0,.18)";

    const fallback = document.createElement("a");
    fallback.href = img.src;
    fallback.target = "_blank";
    fallback.rel = "noopener noreferrer";
    fallback.textContent = "Abrir mídia gerada";
    fallback.style.display = "none";
    fallback.style.fontSize = "13px";

    img.addEventListener("error", () => {
      img.style.display = "none";
      fallback.style.display = "inline";
    });

    wrap.appendChild(img);
    wrap.appendChild(fallback);
    return wrap;
  }
'''
js = js[:start] + new_factory + js[end:]
js = js.replace('const VERSION = "20261001-1";', 'const VERSION = "20261001-2";', 1)
renderer.write_text(js, encoding='utf-8')

index = web_dist / 'index.html'
html = index.read_text(encoding='utf-8')
html = html.replace('hermes-media-renderer.js?v=20261001-1', 'hermes-media-renderer.js?v=20261001-2')
index.write_text(html, encoding='utf-8')
