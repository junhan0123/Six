import json, urllib.request, websocket, base64, os, time

CDP_PORT = 9224

def get_list():
    with urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json/list', timeout=5) as r:
        return json.loads(r.read())

pages = get_list()
print('CDP pages:', len(pages))
for p in pages:
    print('---')
    print('id:', p.get('id'))
    print('title:', p.get('title'))
    print('url:', p.get('url'))
    print('type:', p.get('type'))

# find dyna-orb page by url or title
orb_pages = [p for p in pages if 'dyna-orb' in (p.get('url') or '') or 'orb' in (p.get('title') or '').lower()]
if not orb_pages:
    print('NO_ORB_PAGE_FOUND')
    # try all pages that are not workspace
    orb_pages = [p for p in pages if 'zz-space' not in (p.get('url') or '')]

for p in orb_pages:
    print('>> PROBING page:', p.get('id'), p.get('url'))
    ws_url = p['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=20,
                                     header=['Origin: http://localhost:%d' % CDP_PORT])
    _msg_id = 0
    def send(method, params=None):
        global _msg_id
        _msg_id += 1
        payload = json.dumps({'id': _msg_id, 'method': method, 'params': params or {}})
        ws.send(payload)
        deadline = time.time() + 10
        while time.time() < deadline:
            ws.settimeout(max(0.5, deadline - time.time()))
            try:
                raw = ws.recv()
            except websocket._exceptions.WebSocketTimeoutException:
                continue
            try:
                m = json.loads(raw)
            except Exception:
                continue
            if m.get('id') == _msg_id:
                if 'error' in m:
                    raise RuntimeError(m['error'])
                return m.get('result')
        raise RuntimeError('timeout waiting for response to ' + method)

    send('Runtime.enable')
    send('Log.enable')
    send('Console.enable')

    expr = """
    (function(){
      var c = document.getElementById('orb-canvas');
      var ctx = c ? c.getContext('2d') : null;
      var px = null, tl=null, tr=null, bl=null, br=null, center=null;
      if (c && ctx) {
        try {
          center = Array.from(ctx.getImageData(c.width/2, c.height/2, 1, 1).data);
          tl = Array.from(ctx.getImageData(10, 10, 1, 1).data);
          tr = Array.from(ctx.getImageData(c.width-10, 10, 1, 1).data);
          bl = Array.from(ctx.getImageData(10, c.height-10, 1, 1).data);
          br = Array.from(ctx.getImageData(c.width-10, c.height-10, 1, 1).data);
        } catch(e) {}
      }
      return {
        locationHref: location.href,
        documentReadyState: document.readyState,
        ZZDynaOrbType: typeof window.ZZDynaOrb,
        orbMethods: window.ZZDynaOrb ? Object.keys(window.ZZDynaOrb) : null,
        currentState: window.ZZDynaOrb ? window.ZZDynaOrb.getState() : null,
        canvasSize: c ? {w: c.width, h: c.height} : null,
        canvasDisplay: c ? getComputedStyle(c).display : null,
        canvasOpacity: c ? getComputedStyle(c).opacity : null,
        centerPixel: center,
        tlPixel: tl, trPixel: tr, blPixel: bl, brPixel: br,
        bodyBg: getComputedStyle(document.body).backgroundColor,
        bodyChildren: document.body.children.length,
        lastError: window.__lastOrbError || null
      };
    })()
    """
    result = send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
    print('RUNTIME STATE:', json.dumps(result['result']['value'], indent=2, ensure_ascii=False))

    try:
        cap = send('Page.captureScreenshot', {'format': 'png'})
        png_path = 'G:/Xiao6/xiao6-ui/launcher/logs/orb_screenshot_%s.png' % p.get('id')[:8]
        with open(png_path, 'wb') as f:
            f.write(base64.b64decode(cap['data']))
        print('screenshot saved:', png_path, 'size:', os.path.getsize(png_path))
    except Exception as e:
        print('screenshot_error:', e)

    ws.close()
