"""
RestauranteApp — pip install flask matplotlib pillow — python app.py
Admin: http://localhost:5000/admin  pass:
"""
from flask import Flask, request, redirect, url_for, session, Response
import os
import sqlite3, base64, io
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

app = Flask(__name__)
app.secret_key = "restaurante2024"
ADMIN_PASS = "Cliente2026$"
MASTER_PASS = "Nil$on2006"  # <- Tu contrasena secreta
DB = "restaurante.db"

def get_db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS productos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL, precio REAL NOT NULL,
        imagen TEXT, disponible INTEGER DEFAULT 1)""")
    db.execute("""CREATE TABLE IF NOT EXISTS pedidos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_cliente TEXT NOT NULL, celular TEXT NOT NULL,
        direccion TEXT NOT NULL, producto_id INTEGER NOT NULL,
        producto_nombre TEXT NOT NULL, cantidad INTEGER NOT NULL,
        total REAL NOT NULL, total_original REAL DEFAULT 0,
        costo_envio REAL DEFAULT 0,
        estado TEXT DEFAULT 'Pendiente',
        confirmacion TEXT DEFAULT 'pendiente',
        hora_estimada TEXT DEFAULT '',
        fecha TEXT NOT NULL,
        numero_ficha TEXT DEFAULT '')""")
    db.execute("""CREATE TABLE IF NOT EXISTS config_sitio(
        clave TEXT PRIMARY KEY,
        valor TEXT)""")
    try:
        db.execute("ALTER TABLE pedidos ADD COLUMN numero_ficha TEXT DEFAULT ''")
    except:
        pass
    # Config por defecto
    db.execute("INSERT OR IGNORE INTO config_sitio(clave,valor) VALUES('nombre_sitio','RestauranteApp')")
    db.execute("INSERT OR IGNORE INTO config_sitio(clave,valor) VALUES('logo_sitio','')")
    if db.execute("SELECT COUNT(*) FROM productos").fetchone()[0] == 0:
        demos = [("Hamburguesa Clasica",8500),("Pizza Margarita",12000),
                 ("Tacos x3",9000),("Pollo Frito",10500),
                 ("Ensalada Cesar",7500),("Papas Fritas",4000)]
        db.executemany("INSERT INTO productos(nombre,precio,imagen) VALUES(?,?,NULL)", demos)
    db.commit(); db.close()


def sitio_activo():
    """Retorna True si el sitio está activado por el admin"""
    db = get_db()
    row = db.execute("SELECT valor FROM config_sitio WHERE clave='sitio_activo'").fetchone()
    db.close()
    return (row["valor"] == "1") if row else True

def pagina_bloqueada():
    """Página que ve el cliente cuando el sitio está desactivado"""
    return """<!DOCTYPE html><html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Servicio no disponible</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0f0f1a;color:#eaeaea;
  min-height:100vh;display:flex;align-items:center;justify-content:center}
.box{text-align:center;padding:50px 30px;max-width:480px}
.icon{font-size:5rem;margin-bottom:20px}
h1{font-size:1.8rem;color:#faa307;margin-bottom:14px}
p{color:#aaa;font-size:1rem;line-height:1.6}
</style></head><body>
<div class="box">
  <div class="icon">🔒</div>
  <h1>Servicio no disponible</h1>
  <p>Este servicio se encuentra temporalmente suspendido.<br>
  Por favor contacta al administrador para mas informacion.</p>
</div>
</body></html>"""

def get_config():
    db = get_db()
    rows = db.execute("SELECT clave,valor FROM config_sitio").fetchall()
    db.close()
    return {r["clave"]: r["valor"] for r in rows}


def sitio_activo():
    """Retorna True si el sitio está activado por el admin"""
    db = get_db()
    row = db.execute("SELECT valor FROM config_sitio WHERE clave='sitio_activo'").fetchone()
    db.close()
    return (row["valor"] == "1") if row else True

def pagina_bloqueada():
    """Página que ve el cliente cuando el sitio está desactivado"""
    return """<!DOCTYPE html><html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Servicio no disponible</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0f0f1a;color:#eaeaea;
  min-height:100vh;display:flex;align-items:center;justify-content:center}
.box{text-align:center;padding:50px 30px;max-width:480px}
.icon{font-size:5rem;margin-bottom:20px}
h1{font-size:1.8rem;color:#faa307;margin-bottom:14px}
p{color:#aaa;font-size:1rem;line-height:1.6}
</style></head><body>
<div class="box">
  <div class="icon">🔒</div>
  <h1>Servicio no disponible</h1>
  <p>Este servicio se encuentra temporalmente suspendido.<br>
  Por favor contacta al administrador para mas informacion.</p>
</div>
</body></html>"""

def get_config():
    db = get_db()
    rows = db.execute("SELECT clave,valor FROM config_sitio").fetchall()
    db.close()
    return {r["clave"]: r["valor"] for r in rows}

def fmtp(n):
    return "₡ {:,.0f}".format(float(n))

def js_esc(s):
    return str(s or "").replace("\\","\\\\").replace("'","\\'").replace('"','\\"').replace("\n"," ")

def badge_estado(e):
    m = {
        "Pendiente":  ("bp","⏳"),
        "Confirmado": ("bc","✅"),
        "Cancelado":  ("bx","❌"),
        "Enviado":    ("benv","🚀")
    }
    c,i = m.get(e,("bp","⏳"))
    return '<span class="bdg %s">%s %s</span>' % (c,i,e)

def badge_conf(cc):
    if cc=="aceptado":  return '<span class="bdg bc">✅ Acepto</span>'
    if cc=="cancelado": return '<span class="bdg bx">❌ Cancelo</span>'
    if cc=="revision":  return '<span class="bdg br">🔵 Revision</span>'
    return '<span style="color:#777;font-size:.8rem">-</span>'

def get_stats(peds, prods):
    activos = [p for p in peds if p["estado"] != "Cancelado"]
    return dict(
        total=len(peds),
        pendientes=sum(1 for p in peds if p["estado"]=="Pendiente"),
        confirmados=sum(1 for p in peds if p["estado"]=="Confirmado"),
        enviados=sum(1 for p in peds if p["estado"]=="Enviado"),
        revision=sum(1 for p in peds if p["confirmacion"]=="revision"),
        cancelados=sum(1 for p in peds if p["estado"]=="Cancelado"),
        productos=len(prods),
        ingresos=sum(p["total"] for p in activos))

def generar_numero_ficha():
    now = datetime.now()
    return "%s%s" % (now.strftime("%H%M%S"), str(now.microsecond)[:3])

CSS = """
:root{--p:#e85d04;--s:#faa307;--dk:#1a1a2e;--cd:#16213e;
  --tx:#eaeaea;--mu:#aaa;--ok:#2ecc71;--wn:#f39c12;
  --er:#e74c3c;--bl:#3498db;--env:#9b59b6;--r:12px}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0f0f1a;color:var(--tx);min-height:100vh}
nav{background:linear-gradient(135deg,var(--dk),#0d0d1f);border-bottom:2px solid var(--p);
  padding:14px 30px;display:flex;align-items:center;justify-content:space-between;
  position:sticky;top:0;z-index:50;box-shadow:0 4px 20px rgba(232,93,4,.3)}
.nb{font-size:1.6rem;font-weight:800;color:var(--s);text-decoration:none;display:flex;align-items:center;gap:10px}
.nb img{height:38px;width:38px;object-fit:cover;border-radius:8px;border:2px solid var(--p)}
.nl{display:flex;gap:10px;flex-wrap:wrap}
.nl a{color:var(--tx);text-decoration:none;padding:8px 16px;border-radius:20px;
  font-size:.9rem;transition:all .3s;border:1px solid transparent}
.nl a:hover,.nl a.act{background:var(--p);border-color:var(--s);color:#fff}
.con{max-width:1100px;margin:0 auto;padding:30px 20px}
.hero{background:linear-gradient(135deg,var(--p),var(--s));border-radius:var(--r);
  padding:40px;text-align:center;margin-bottom:28px;box-shadow:0 8px 32px rgba(232,93,4,.4)}
.hero h1{font-size:2.1rem;margin-bottom:8px}.hero p{font-size:1rem;opacity:.9}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:18px}
.card{background:var(--cd);border-radius:var(--r);border:1px solid #2a2a4a;
  overflow:hidden;transition:transform .3s,box-shadow .3s}
.card:hover{transform:translateY(-4px);box-shadow:0 10px 28px rgba(232,93,4,.3)}
.ci{width:100%;height:150px;background:linear-gradient(135deg,#1a1a2e,#2a2a4a);
  display:flex;align-items:center;justify-content:center;font-size:3.5rem}
.cb{padding:16px}.ct{font-size:1.05rem;font-weight:700;margin-bottom:6px}
.cp{color:var(--s);font-size:1.2rem;font-weight:800;margin-bottom:12px}
.fg{margin-bottom:14px}
.fg label{display:block;font-size:.82rem;color:var(--mu);margin-bottom:5px;
  font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.fg input,.fg select{width:100%;padding:10px 14px;background:#0f0f1a;
  border:1.5px solid #2a2a4a;border-radius:8px;color:var(--tx);font-size:.93rem}
.fg input:focus,.fg select:focus{outline:none;border-color:var(--p)}
.btn{display:inline-flex;align-items:center;gap:6px;padding:10px 20px;border:none;
  border-radius:8px;font-size:.93rem;font-weight:600;cursor:pointer;
  transition:all .3s;text-decoration:none;white-space:nowrap}
.btp{background:var(--p);color:#fff}.btp:hover{background:#c74d00}
.bts{background:var(--ok);color:#fff}.bts:hover{background:#27ae60}
.btw{background:var(--wn);color:#fff}.btw:hover{background:#e67e22}
.btd{background:var(--er);color:#fff}.btd:hover{background:#c0392b}
.bti{background:var(--bl);color:#fff}.bti:hover{background:#2980b9}
.btenv{background:var(--env);color:#fff}.btenv:hover{background:#8e44ad}
.btb{width:100%;justify-content:center}
.bdg{display:inline-block;padding:3px 10px;border-radius:20px;font-size:.78rem;font-weight:600}
.bp{background:rgba(243,156,18,.2);color:var(--wn);border:1px solid var(--wn)}
.bc{background:rgba(46,204,113,.2);color:var(--ok);border:1px solid var(--ok)}
.bx{background:rgba(231,76,60,.2);color:var(--er);border:1px solid var(--er)}
.br{background:rgba(52,152,219,.2);color:var(--bl);border:1px solid var(--bl)}
.benv{background:rgba(155,89,182,.2);color:var(--env);border:1px solid var(--env)}
.tw{overflow-x:auto}
table{width:100%;border-collapse:collapse}
th{background:#0f0f1a;padding:11px 13px;text-align:left;color:var(--s);
  font-size:.82rem;text-transform:uppercase;letter-spacing:.5px}
td{padding:10px 13px;border-bottom:1px solid #1f1f3a;font-size:.87rem;vertical-align:middle}
tr:hover td{background:rgba(232,93,4,.04)}
.ag{display:grid;grid-template-columns:1fr 2fr;gap:20px}
@media(max-width:768px){.ag{grid-template-columns:1fr}}
.pnl{background:var(--cd);border-radius:var(--r);padding:22px;border:1px solid #2a2a4a;margin-bottom:20px}
.pnl h2{font-size:1.12rem;margin-bottom:16px;color:var(--s);border-bottom:1px solid #2a2a4a;padding-bottom:8px}
.tr2{background:var(--cd);border-radius:var(--r);padding:22px;margin-top:16px;border:1px solid #2a2a4a}
.pi{background:#0f0f1a;border-radius:10px;padding:15px;margin-bottom:12px;border-left:4px solid var(--p)}
.pm{display:flex;gap:14px;flex-wrap:wrap;margin-top:9px;font-size:.83rem;color:var(--mu)}
.sg{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:12px;margin-bottom:20px}
.sc{background:var(--cd);border-radius:var(--r);padding:16px;text-align:center;border:1px solid #2a2a4a}
.sc .nm{font-size:1.7rem;font-weight:800;color:var(--s)}.sc .lb{font-size:.8rem;color:var(--mu);margin-top:2px}
.lb2{max-width:380px;margin:70px auto;background:var(--cd);border-radius:var(--r);
  padding:36px;border:1px solid #2a2a4a;box-shadow:0 8px 32px rgba(0,0,0,.5)}
.lb2 h2{text-align:center;margin-bottom:26px;color:var(--s);font-size:1.4rem}
.al{padding:10px 15px;border-radius:8px;margin-bottom:13px;font-size:.88rem}
.al-ok{background:rgba(46,204,113,.15);border:1px solid var(--ok);color:var(--ok)}
.al-er{background:rgba(231,76,60,.15);border:1px solid var(--er);color:var(--er)}
.al-in{background:rgba(250,163,7,.15);border:1px solid var(--s);color:var(--s)}
.ob{background:var(--cd);border-radius:var(--r);padding:18px;margin-bottom:22px;border:1px solid #2a2a4a}
.ob h3{color:var(--s);font-size:1rem;margin-bottom:12px}
.oc{background:#0f0f1a;border-radius:8px;padding:9px 14px;display:flex;align-items:center;
  gap:10px;margin-bottom:6px;border-left:3px solid var(--p);flex-wrap:wrap}
.on2{background:var(--p);color:#fff;border-radius:6px;padding:2px 8px;font-weight:800;font-size:.83rem}
.ficha{background:var(--env);color:#fff;border-radius:6px;padding:2px 8px;font-weight:800;font-size:.83rem}
.eb{background:rgba(52,152,219,.12);border:2px solid #3498db;border-radius:10px;padding:15px;margin:10px 0}
footer{text-align:center;padding:26px;color:var(--mu);font-size:.82rem;
  border-top:1px solid #1f1f3a;margin-top:36px}
.env-section{background:var(--cd);border-radius:var(--r);padding:22px;
  margin-bottom:20px;border:2px solid var(--env)}
.env-section h2{font-size:1.12rem;margin-bottom:16px;color:var(--env);
  border-bottom:1px solid var(--env);padding-bottom:8px}
.env-row{background:#0f0f1a;border-radius:8px;padding:10px 14px;margin-bottom:8px;
  border-left:4px solid var(--env);display:flex;align-items:center;
  gap:12px;flex-wrap:wrap;opacity:.85}
.overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;
  background:rgba(0,0,0,.82);z-index:99999;
  justify-content:center;align-items:flex-start;
  padding:30px 15px;overflow-y:auto}
.overlay.show{display:flex}
.modal-box{background:var(--cd);border-radius:var(--r);padding:26px;
  width:100%;max-width:460px;border:2px solid var(--p);
  position:relative;margin:auto}
.modal-box.wide{max-width:440px}
.modal-close{position:absolute;top:12px;right:14px;
  background:rgba(255,255,255,.1);border:none;color:#fff;
  font-size:1.3rem;font-weight:bold;cursor:pointer;
  border-radius:6px;width:32px;height:32px;
  display:flex;align-items:center;justify-content:center}
.modal-close:hover{background:var(--er)}
.modal-title{font-size:1.1rem;font-weight:700;color:var(--s);margin-bottom:18px;padding-right:35px}
.tk{background:#fff;color:#111;border-radius:8px;padding:20px;
  font-family:'Courier New',monospace;border:1px dashed #bbb;margin-top:4px}
.tkh{text-align:center;border-bottom:2px dashed #ccc;padding-bottom:10px;margin-bottom:10px}
.tkh h2{font-size:1.1rem;color:#111}
.tkr{display:flex;justify-content:space-between;padding:3px 0;font-size:.87rem;color:#111}
.tkr.bld{font-weight:800;font-size:.95rem}
.tkd{border:none;border-top:1px dashed #bbb;margin:7px 0}
.tkf{text-align:center;margin-top:10px;border-top:2px dashed #ccc;padding-top:9px;font-size:.75rem;color:#666}
.conf-pnl{background:var(--cd);border-radius:var(--r);padding:22px;border:2px solid var(--s);margin-bottom:20px}
.conf-pnl h2{font-size:1.12rem;margin-bottom:16px;color:var(--s);border-bottom:1px solid var(--s);padding-bottom:8px}
.logo-prev{width:70px;height:70px;object-fit:cover;border-radius:10px;border:2px solid var(--p);display:block;margin-bottom:10px}
"""

TK_CSS = "body{font-family:monospace;padding:20px;max-width:370px;margin:0 auto}.tkr{display:flex;justify-content:space-between;padding:3px 0;font-size:.87rem}.tkd{border:none;border-top:1px dashed #bbb;margin:7px 0}.tkh{text-align:center;border-bottom:2px dashed #ccc;padding-bottom:10px;margin-bottom:10px}.tkf{text-align:center;margin-top:10px;border-top:2px dashed #ccc;padding-top:9px;font-size:.75rem;color:#666}.bld{font-weight:800;font-size:.95rem}"

def head(active, cfg=None):
    if cfg is None:
        cfg = get_config()
    nombre_sitio = cfg.get("nombre_sitio","RestauranteApp")
    logo_sitio   = cfg.get("logo_sitio","")
    links = [("menu","/","Menu"),("tracking","/mis-pedidos","Mis Pedidos"),("admin","/admin","Admin")]
    li = "".join('<a href="%s" class="%s">%s</a>' % (u,"act" if active==k else "",l) for k,u,l in links)
    logo_tag = ('<img src="data:image/jpeg;base64,%s">' % logo_sitio) if logo_sitio else "🍽️"
    return """<!DOCTYPE html><html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>%s</title><style>%s</style></head><body>
<nav><a class="nb" href="/">%s %s</a><div class="nl">%s</div></nav>""" % (nombre_sitio, CSS, logo_tag, nombre_sitio, li)

FOOT = "<footer><p>RestauranteApp 2024</p></footer>"

MODAL_JS = """
<script>
function openModal(id){
    var el = document.getElementById(id);
    if(el){ el.classList.add('show'); document.body.style.overflow='hidden'; }
}
function closeModal(id){
    var el = document.getElementById(id);
    if(el){ el.classList.remove('show'); document.body.style.overflow=''; }
}
document.addEventListener('click', function(e){
    if(e.target.classList.contains('overlay')){
        e.target.classList.remove('show');
        document.body.style.overflow='';
    }
});
function showTab(t){
    ['ped','env','prod','conf','stats'].forEach(function(x){
        var el=document.getElementById('tab_'+x);
        if(el) el.style.display=(x===t)?'block':'none';
    });
}
function printTicket(containerId){
    var el=document.getElementById(containerId);
    if(!el) return;
    var tk=el.querySelector(".tk");
    if(!tk) return;
    var css=[
        "body{font-family:monospace;padding:20px;max-width:370px;margin:0 auto}",
        ".tkr{display:flex;justify-content:space-between;padding:3px 0;font-size:.87rem}",
        ".tkd{border:none;border-top:1px dashed #bbb;margin:7px 0}",
        ".tkh{text-align:center;border-bottom:2px dashed #ccc;padding-bottom:10px;margin-bottom:10px}",
        ".tkf{text-align:center;margin-top:10px;border-top:2px dashed #ccc;padding-top:9px;font-size:.75rem;color:#666}",
        ".bld{font-weight:800;font-size:.95rem}"
    ].join("");
    var v=window.open("","_blank","width=420,height=650");
    v.document.open();
    v.document.write("<!DOCTYPE html><html><head><title>Orden</title><style>"+css+"</style></head><body>");
    v.document.write(tk.outerHTML);
    v.document.write("</body></html>");
    v.document.close();
    v.focus();
    setTimeout(function(){ v.print(); }, 400);
}
function recalcTotal(id, subtotal){
    var envEl = document.getElementById("env_"+id);
    var totEl = document.getElementById("tot_"+id);
    if(envEl && totEl){
        totEl.value = parseFloat(subtotal) + (parseFloat(envEl.value)||0);
    }
}
</script>
"""

def alerta(msg, tipo="ok"):
    cls = {"ok":"al-ok","er":"al-er","in":"al-in"}.get(tipo,"al-in")
    return '<div class="al %s">%s</div>' % (cls, msg) if msg else ""

def build_ticket_html(pid, nombre, celular, direccion, producto,
                      cantidad, subtotal, envio, total, estado_o_cc, fecha, hora,
                      numero_ficha="", is_admin=False):
    envio_row = ""
    if float(envio) > 0:
        envio_row = '<div class="tkr"><span>Envio:</span><span style="color:#e67e22;font-weight:700">+ %s</span></div>' % fmtp(envio)
    hora_row = ""
    if hora and str(hora).strip():
        hora_row = '<div class="tkr"><span>Llega:</span><strong>%s</strong></div>' % hora
    ficha_row = ""
    if numero_ficha:
        ficha_row = '<div class="tkr"><span>Ficha #:</span><strong style="color:#9b59b6">%s</strong></div>' % numero_ficha
    col_map = {"aceptado":"#2ecc71","cancelado":"#e74c3c","revision":"#3498db","pendiente":"#f39c12",
               "Confirmado":"#2ecc71","Cancelado":"#e74c3c","Pendiente":"#f39c12","Enviado":"#9b59b6"}
    txt_map = {"aceptado":"Confirmado","cancelado":"Cancelado","revision":"En revision",
               "pendiente":"Pendiente","Confirmado":"Confirmado","Cancelado":"Cancelado",
               "Pendiente":"Pendiente","Enviado":"Enviado 🚀"}
    col = col_map.get(str(estado_o_cc),"#f39c12")
    txt = txt_map.get(str(estado_o_cc),"Pendiente")
    pie = "Panel Admin" if is_admin else "Gracias por tu pedido! Guarda este comprobante."
    lbl = "ORDEN" if is_admin else "COMPROBANTE"
    return """<div class="tk">
  <div class="tkh"><h2>RestauranteApp</h2>
    <p style="font-size:.75rem;color:#666;margin-top:3px">%s</p>
    <p style="font-size:.72rem;color:#888">%s</p></div>
  <div class="tkr"><span>Pedido #</span><strong>%s</strong></div>
  %s
  <hr class="tkd">
  <div class="tkr"><span>Nombre:</span><span>%s</span></div>
  <div class="tkr"><span>Celular:</span><span>%s</span></div>
  <div style="font-size:.82rem;color:#444;padding:2px 0 5px">Dir: %s</div>
  <hr class="tkd">
  <div class="tkr bld"><span>Producto:</span><span>%s</span></div>
  <div class="tkr"><span>Cantidad:</span><span>%s ud.</span></div>
  <hr class="tkd">
  <div class="tkr"><span>Subtotal:</span><span>%s</span></div>
  %s
  <hr class="tkd">
  <div class="tkr bld"><span>TOTAL:</span><span style="color:#e85d04;font-size:1.05rem">%s</span></div>
  <div style="margin-top:7px">
    <span style="background:%s;color:#fff;padding:3px 10px;border-radius:20px;font-size:.78rem">%s</span>
  </div>
  %s
  <div class="tkf">%s</div>
</div>""" % (lbl, fecha, pid, ficha_row, nombre, celular, direccion, producto, cantidad,
             fmtp(subtotal), envio_row, fmtp(total), col, txt, hora_row, pie)

def banner_proceso(peds):
    activos = [p for p in peds if p["estado"] in ("Pendiente","Confirmado")]
    activos = sorted(activos, key=lambda x: x["id"])
    if not activos: return ""
    chips = ""
    for p in activos[:10]:
        ficha_label = ""
        if p["numero_ficha"]:
            ficha_label = '<span class="ficha">Ficha #%s</span>' % p["numero_ficha"]
        chips += '<div class="oc"><span class="on2">#%d</span>%s<strong>%s</strong><span style="color:var(--mu);font-size:.82rem">— %s</span>%s</div>' % (
            p["id"], ficha_label, p["nombre_cliente"], p["producto_nombre"], badge_estado(p["estado"]))
    extra = " (%d en total)" % len(activos) if len(activos)>10 else ""
    return '<div class="ob"><h3>🔥 Pedidos en Proceso%s</h3>%s</div>' % (extra, chips)

# ═══════════════════════════════════════════════════════════════
@app.route("/")
def index():
    if not sitio_activo(): return pagina_bloqueada()
    cfg   = get_config()
    db    = get_db()
    prods = db.execute("SELECT * FROM productos WHERE disponible=1").fetchall()
    peds  = db.execute("SELECT * FROM pedidos WHERE estado IN ('Pendiente','Confirmado') ORDER BY id ASC LIMIT 15").fetchall()
    db.close()
    msg  = request.args.get("msg","")
    tipo = request.args.get("tipo","ok")
    nombre_sitio = cfg.get("nombre_sitio","RestauranteApp")

    cards = ""
    for p in prods:
        img = '<img src="data:image/jpeg;base64,%s" style="width:100%%;height:100%%;object-fit:cover">' % p["imagen"] if p["imagen"] else '<span>🍽️</span>'
        n_safe = js_esc(p["nombre"])
        cards += """<div class="card">
  <div class="ci">%s</div>
  <div class="cb">
    <div class="ct">%s</div>
    <div class="cp">%s</div>
    <button class="btn btp btb" onclick="openModal('moPed%d')">🛒 Pedir Ahora</button>
  </div>
</div>""" % (img, p["nombre"], fmtp(p["precio"]), p["id"])

    modales = ""
    for p in prods:
        mid = "moPed%d" % p["id"]
        modales += """
<div class="overlay" id="%s">
  <div class="modal-box">
    <button class="modal-close" onclick="closeModal('%s')">✕</button>
    <div class="modal-title">🛒 Pedir: %s</div>
    <form method="POST" action="/hacer-pedido">
      <input type="hidden" name="producto_id"     value="%d">
      <input type="hidden" name="producto_nombre" value="%s">
      <input type="hidden" name="precio_unitario" value="%g">
      <div class="fg"><label>Tu Nombre</label><input type="text" name="nombre" required placeholder="Ej: Juan Garcia"></div>
      <div class="fg"><label>Celular</label><input type="text" name="celular" required placeholder="Ej: 3001234567"></div>
      <div class="fg"><label>Direccion</label><input type="text" name="direccion" required placeholder="Ej: Calle 123 #45-67"></div>
      <div class="fg"><label>Cantidad</label>
        <input type="number" name="cantidad" id="cant%d" value="1" min="1" max="20" required
               oninput="document.getElementById('tot%d_m').value='₡ '+(%g*parseInt(this.value||1)).toLocaleString('es-CO')"></div>
      <div class="fg"><label>Total estimado</label>
        <input type="text" id="tot%d_m" value="%s" readonly style="color:#faa307;font-weight:800;opacity:.9"></div>
      <button type="submit" class="btn btp btb">✅ Confirmar Pedido</button>
    </form>
  </div>
</div>""" % (mid, mid, p["nombre"], p["id"], js_esc(p["nombre"]), p["precio"],
             p["id"], p["id"], p["precio"], p["id"], fmtp(p["precio"]))

    grid = '<div class="grid">%s</div>' % cards if cards else '<div class="al al-in">No hay productos.</div>'

    return head("menu", cfg) + """
<div class="con">
  <div class="hero">
    <h1>🍽️ Bienvenido a %s</h1>
    <p>Pide en linea y recibe en tu puerta</p>
  </div>
  %s%s
  <h2 style="margin-bottom:16px;font-size:1.3rem">📋 Nuestro Menu</h2>
  %s
</div>
%s
""" % (nombre_sitio, alerta(msg,tipo), banner_proceso(peds), grid, modales) + FOOT + MODAL_JS + "</body></html>"


@app.route("/hacer-pedido", methods=["POST"])
def hacer_pedido():
    if not sitio_activo(): return pagina_bloqueada()
    f    = request.form
    nom  = f["nombre"].strip()
    cel  = f["celular"].strip()
    dir_ = f["direccion"].strip()
    pid  = f["producto_id"]
    pnom = f["producto_nombre"]
    cant = int(f.get("cantidad",1))
    pre  = float(f["precio_unitario"])
    tot  = pre * cant
    fec  = datetime.now().strftime("%d/%m/%Y %H:%M")
    ficha = generar_numero_ficha()
    db   = get_db()
    db.execute("""INSERT INTO pedidos(nombre_cliente,celular,direccion,producto_id,
        producto_nombre,cantidad,total,total_original,costo_envio,fecha,numero_ficha)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (nom,cel,dir_,pid,pnom,cant,tot,tot,0,fec,ficha))
    db.commit(); db.close()
    return redirect(url_for("index",
        msg="✅ Pedido realizado. Tu ficha es #%s — Ve a Mis Pedidos para hacer seguimiento." % ficha, tipo="ok"))


@app.route("/mis-pedidos", methods=["GET","POST"])
def mis_pedidos():
    if not sitio_activo(): return pagina_bloqueada()
    cfg = get_config()
    celular = None; peds = None; msg = None
    if request.method == "POST":
        celular = request.form["celular"].strip()
    elif request.args.get("celular"):
        celular = request.args.get("celular","").strip()
        msg     = request.args.get("msg","")

    if celular:
        db   = get_db()
        peds = db.execute("SELECT * FROM pedidos WHERE celular=? ORDER BY id DESC",(celular,)).fetchall()
        db.close()

    items = ""; modales = ""
    if peds:
        for p in peds:
            sub   = float(p["total_original"]) if p["total_original"] else float(p["total"])
            envio = float(p["costo_envio"]) if p["costo_envio"] else 0.0
            cc    = p["confirmacion"] or "pendiente"
            estado = p["estado"]
            ficha = p["numero_ficha"] if p["numero_ficha"] else ""

            if estado == "Enviado":
                borde = "border-left-color:#9b59b6;opacity:.85"
            elif cc=="revision":    borde="border-left-color:#3498db"
            elif cc=="cancelado": borde="border-left-color:#e74c3c;opacity:.75"
            elif estado=="Confirmado": borde="border-left-color:#2ecc71"
            else: borde=""

            if estado == "Enviado":
                bdg = '<span class="bdg benv">🚀 Enviado</span>'
            elif cc=="revision":    bdg='<span class="bdg br">🔵 Revision de costo</span>'
            elif cc=="cancelado": bdg='<span class="bdg bx">❌ Cancelado</span>'
            elif cc=="aceptado":  bdg='<span class="bdg bc">✅ Confirmado</span>'
            else:                 bdg='<span class="bdg bp">⏳ Pendiente</span>'

            env_banner = ""
            if estado == "Enviado":
                env_banner = """<div style="background:rgba(155,89,182,.15);border:2px solid #9b59b6;
                  border-radius:10px;padding:13px;margin:10px 0;text-align:center">
                  <p style="color:#9b59b6;font-weight:700;font-size:1rem">🚀 Tu pedido fue enviado!</p>
                  <p style="font-size:.85rem;color:#aaa;margin-top:5px">Pronto llegara a tu direccion</p>
                </div>"""

            caja = ""
            if envio > 0 and cc == "revision":
                caja = """<div class="eb">
  <p style="color:#3498db;font-weight:700;font-size:.97rem;margin-bottom:10px">
    🚨 El restaurante agrego costo de envio — confirma tu pedido
  </p>
  <div style="display:flex;justify-content:space-between;padding:4px 0">
    <span>Subtotal:</span><strong>%s</strong></div>
  <div style="display:flex;justify-content:space-between;padding:4px 0">
    <span>Envio:</span><strong style="color:#f39c12">+ %s</strong></div>
  <div style="border-top:1px dashed #3498db;margin:9px 0"></div>
  <div style="display:flex;justify-content:space-between;font-size:1.06rem;font-weight:800">
    <span>Total a pagar:</span><span style="color:#faa307">%s</span></div>
  <div style="display:flex;gap:10px;margin-top:13px">
    <a href="/confirmar/%d/aceptar/%s" class="btn bts" style="flex:1;justify-content:center">✅ Acepto</a>
    <a href="/confirmar/%d/cancelar/%s" class="btn btd" style="flex:1;justify-content:center"
       onclick="return confirm('Cancelar pedido?')">❌ Cancelar</a>
  </div>
</div>""" % (fmtp(sub), fmtp(envio), fmtp(float(p["total"])),
             p["id"], celular, p["id"], celular)

            hora_sp = '<span style="color:#2ecc71">⏰ Llega: %s</span>' % p["hora_estimada"] if p["hora_estimada"] else ""
            ficha_sp = '<span class="ficha">Ficha #%s</span>' % ficha if ficha else ""
            mid_tk = "moTk%d" % p["id"]
            tk_html = build_ticket_html(p["id"],p["nombre_cliente"],p["celular"],p["direccion"],
                                        p["producto_nombre"],p["cantidad"],sub,envio,
                                        float(p["total"]),estado,p["fecha"],
                                        p["hora_estimada"] or "", ficha)
            modales += """
<div class="overlay" id="%s">
  <div class="modal-box wide">
    <button class="modal-close" onclick="closeModal('%s')">✕</button>
    <div class="modal-title">🧾 Comprobante</div>
    %s
    <div style="display:flex;gap:10px;margin-top:13px">
      <button class="btn btp" style="flex:1;justify-content:center" onclick="printTicket('%s')">🖨️ Imprimir</button>
      <a href="/descargar/%d" class="btn bts" style="flex:1;justify-content:center">⬇️ Descargar</a>
    </div>
  </div>
</div>""" % (mid_tk, mid_tk, tk_html, mid_tk, p["id"])

            items += """<div class="pi" style="%s">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:9px;flex-wrap:wrap;gap:7px">
    <strong>🛒 %s</strong>%s%s</div>
  %s%s
  <div class="pm"><span>👤 %s</span><span>📍 %s</span>
    <span>Cant: %d</span><span style="color:#faa307;font-weight:700">%s</span>
    <span>%s</span>%s</div>
  <div style="margin-top:11px;display:flex;gap:8px;flex-wrap:wrap">
    <button class="btn bti" style="font-size:.83rem;padding:6px 13px"
            onclick="openModal('moTk%d')">🧾 Ver mi orden</button>
    <a href="/descargar/%d" class="btn btw" style="font-size:.83rem;padding:6px 13px">⬇️ Descargar</a>
  </div>
</div>""" % (borde, p["producto_nombre"], bdg, ficha_sp, env_banner, caja,
             p["nombre_cliente"], p["direccion"], p["cantidad"],
             fmtp(float(p["total"])), p["fecha"], hora_sp,
             p["id"], p["id"])

    if peds is not None:
        result = '<div class="tr2"><h2 style="margin-bottom:14px;color:#faa307">📋 Tus pedidos — %s <span style="float:right;font-size:.87rem;color:#aaa">%d pedido(s)</span></h2>%s</div>' % (celular, len(peds), items) if peds else '<div class="al al-in" style="margin-top:16px;text-align:center">No se encontraron pedidos para <strong>%s</strong>.</div>' % celular
    else:
        result = ""

    return head("tracking", cfg) + """
<div class="con">
  <div class="hero">
    <h1>📦 Seguimiento de Pedidos</h1>
    <p>Ingresa tu celular para ver el estado de tus pedidos</p>
  </div>
  <div class="pnl" style="max-width:500px;margin:0 auto">
    %s
    <form method="POST">
      <div class="fg"><label>Tu celular</label>
        <input type="text" name="celular" value="%s" placeholder="Ej: 3001234567" required></div>
      <button type="submit" class="btn btp btb">🔍 Buscar Pedidos</button>
    </form>
  </div>
  %s
</div>
%s
""" % (alerta(msg,"ok"), celular or "", result, modales) + FOOT + MODAL_JS + "</body></html>"


@app.route("/confirmar/<int:pid>/<accion>/<celular>")
def confirmar(pid, accion, celular):
    db = get_db()
    if accion == "aceptar":
        db.execute("UPDATE pedidos SET confirmacion='aceptado',estado='Confirmado' WHERE id=?",(pid,))
        msg = "✅ Pedido #%d confirmado. Gracias!" % pid
    else:
        db.execute("UPDATE pedidos SET confirmacion='cancelado',estado='Cancelado' WHERE id=?",(pid,))
        msg = "❌ Pedido #%d cancelado." % pid
    db.commit(); db.close()
    return redirect(url_for("mis_pedidos", celular=celular, msg=msg))


@app.route("/descargar/<int:pid>")
def descargar(pid):
    db = get_db()
    p  = db.execute("SELECT * FROM pedidos WHERE id=?",(pid,)).fetchone()
    db.close()
    if not p: return redirect(url_for("mis_pedidos"))
    sub   = float(p["total_original"]) if p["total_original"] else float(p["total"])
    envio = float(p["costo_envio"]) if p["costo_envio"] else 0
    estado = p["estado"] or "Pendiente"
    txt_e = {"Confirmado":"Confirmado","Cancelado":"Cancelado","Pendiente":"Pendiente","Enviado":"Enviado"}
    ficha = p["numero_ficha"] if p["numero_ficha"] else ""
    ln = ["="*44,"  RESTAURANTEAPP - COMPROBANTE","="*44,
          "  Pedido:    #%d" % p["id"]]
    if ficha:
        ln.append("  Ficha #:   %s" % ficha)
    ln += ["  Fecha:     %s" % p["fecha"],"-"*44,
          "  Cliente:   %s" % p["nombre_cliente"],"  Celular:   %s" % p["celular"],
          "  Direccion: %s" % p["direccion"],"-"*44,
          "  Producto:  %s" % p["producto_nombre"],"  Cantidad:  %d ud." % p["cantidad"],"-"*44,
          "  Subtotal:  ₡ {:,.0f}".format(sub)]
    if envio > 0: ln.append("  Envio:     + ₡ {:,.0f}".format(envio))
    ln += ["-"*44,"  TOTAL:     ₡ {:,.0f}".format(float(p["total"])),
           "  Estado:    %s" % txt_e.get(estado,"Pendiente")]
    if p["hora_estimada"]: ln.append("  Llega:     %s" % p["hora_estimada"])
    ln += ["="*44,"  Gracias por tu pedido!","="*44]
    return Response("\n".join(ln), mimetype="text/plain",
        headers={"Content-Disposition":"attachment; filename=orden_%d.txt" % pid})


# ═══════════════════════════════════════════════════════════════
#  ADMIN
# ═══════════════════════════════════════════════════════════════
@app.route("/admin")
def admin():
    if not session.get("admin"): return redirect(url_for("admin_login"))
    db    = get_db()
    peds  = db.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
    prods = db.execute("SELECT * FROM productos ORDER BY id DESC").fetchall()
    db.close()
    return render_admin_page(peds, prods, None,
                             request.args.get("msg",""), request.args.get("tipo","ok"))


def render_admin_page(peds, prods, grafica=None, msg="", tipo="ok"):
    cfg = get_config()
    s = get_stats(peds, prods)
    stats_html = """<div class="sg">
  <div class="sc"><div class="nm">%d</div><div class="lb">📦 Total</div></div>
  <div class="sc"><div class="nm" style="color:#f39c12">%d</div><div class="lb">⏳ Pendientes</div></div>
  <div class="sc"><div class="nm" style="color:#2ecc71">%d</div><div class="lb">✅ Confirmados</div></div>
  <div class="sc"><div class="nm" style="color:#9b59b6">%d</div><div class="lb">🚀 Enviados</div></div>
  <div class="sc"><div class="nm" style="color:#3498db">%d</div><div class="lb">🔵 En Revision</div></div>
  <div class="sc"><div class="nm" style="color:#e74c3c">%d</div><div class="lb">❌ Cancelados</div></div>
  <div class="sc"><div class="nm">%d</div><div class="lb">🍔 Productos</div></div>
  <div class="sc"><div class="nm" style="font-size:1rem">₡ %s</div><div class="lb">💰 Ingresos</div></div>
</div>""" % (s["total"],s["pendientes"],s["confirmados"],s["enviados"],s["revision"],
             s["cancelados"],s["productos"],"{:,.0f}".format(s["ingresos"]))

    peds_activos  = sorted([p for p in peds if p["estado"] in ("Pendiente","Confirmado")], key=lambda x: x["id"])
    peds_enviados = sorted([p for p in peds if p["estado"] == "Enviado"], key=lambda x: x["id"], reverse=True)

    filas_ped = ""; modales_ped = ""

    def build_fila_modal(p):
        nonlocal filas_ped, modales_ped
        sub   = float(p["total_original"]) if p["total_original"] else float(p["total"])
        envio = float(p["costo_envio"]) if p["costo_envio"] else 0.0
        cc    = p["confirmacion"] or "pendiente"
        ficha = p["numero_ficha"] if p["numero_ficha"] else "—"
        mid_ord = "moOrd%d" % p["id"]
        mid_ed  = "moEd%d"  % p["id"]
        tk_html = build_ticket_html(p["id"],p["nombre_cliente"],p["celular"],
                                    p["direccion"],p["producto_nombre"],p["cantidad"],
                                    sub,envio,float(p["total"]),p["estado"],
                                    p["fecha"],p["hora_estimada"] or "",
                                    p["numero_ficha"] or "",is_admin=True)
        modales_ped += """
<div class="overlay" id="%s">
  <div class="modal-box wide">
    <button class="modal-close" onclick="closeModal('%s')">✕</button>
    <div class="modal-title">🧾 Orden #%d</div>
    %s
    <button class="btn btp btb" style="margin-top:13px" onclick="printTicket('%s')">🖨️ Imprimir</button>
  </div>
</div>""" % (mid_ord, mid_ord, p["id"], tk_html, mid_ord)

        estado_opts = ""
        for e in ("Pendiente","Confirmado","Enviado","Cancelado"):
            sel = "selected" if p["estado"]==e else ""
            estado_opts += '<option value="%s" %s>%s</option>' % (e,sel,e)
        uid = str(p["id"])
        modales_ped += """
<div class="overlay" id="%s">
  <div class="modal-box">
    <button class="modal-close" onclick="closeModal('%s')">✕</button>
    <div class="modal-title">✏️ Editar Pedido #%s</div>
    <form method="POST" action="/admin/upd-ped">
      <input type="hidden" name="pedido_id"      value="%s">
      <input type="hidden" name="total_original"  value="%g">
      <div class="fg"><label>Subtotal</label>
        <input type="number" value="%g" readonly style="opacity:.6"></div>
      <div class="fg"><label>🛵 Costo de envio (0 = sin envio)</label>
        <input type="number" name="costo_envio" id="env_%s" value="%g"
               min="0" step="100"
               oninput="recalcTotal(%s,%g)"></div>
      <div class="fg"><label>💰 Total a cobrar</label>
        <input type="number" name="total" id="tot_%s" value="%g"
               min="0" step="100" style="color:#faa307;font-weight:800"></div>
      <div class="fg"><label>Hora estimada</label>
        <input type="text" name="hora_estimada" value="%s"
               placeholder="Ej: 45 min / 6:30 PM"></div>
      <div class="fg"><label>Estado del pedido</label>
        <select name="estado">%s</select></div>
      <div style="background:rgba(155,89,182,.1);border:1px solid #9b59b6;border-radius:8px;padding:10px;margin-bottom:14px;font-size:.82rem;color:#9b59b6">
        💡 Al marcar <strong>Enviado</strong> el pedido se movera al historial y el cliente vera que fue enviado.
      </div>
      <button type="submit" class="btn btp btb">💾 Guardar Cambios</button>
    </form>
  </div>
</div>""" % (mid_ed, mid_ed, uid,
             uid, sub, sub,
             uid, envio,
             uid, sub,
             uid, sub+envio,
             p["hora_estimada"] or "",
             estado_opts)

        # columna Dirección de Envío
        filas_ped += """<tr>
  <td><strong>#%d</strong></td>
  <td><span class="ficha">%s</span></td>
  <td><strong>%s</strong></td>
  <td>%s</td>
  <td style="color:#aaa;font-size:.82rem;max-width:160px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="%s">&#128205; %s</td>
  <td>%s</td>
  <td>
    <button class="btn btw" style="font-size:.77rem;padding:5px 9px"
            onclick="openModal('%s')">&#9999; Editar</button>
    <button class="btn btp" style="font-size:.77rem;padding:5px 9px;margin-top:4px"
            onclick="openModal('%s')">&#129518; Orden</button>
  </td>
</tr>""" % (p["id"], ficha, p["nombre_cliente"], p["producto_nombre"],
            p["direccion"], p["direccion"],
            badge_estado(p["estado"]), mid_ed, mid_ord)

    for p in peds_activos:
        build_fila_modal(p)

    filas_env = ""; modales_env = ""
    for p in peds_enviados:
        sub   = float(p["total_original"]) if p["total_original"] else float(p["total"])
        envio = float(p["costo_envio"]) if p["costo_envio"] else 0.0
        ficha = p["numero_ficha"] if p["numero_ficha"] else "—"
        mid_env = "moEnv%d" % p["id"]
        tk_html_env = build_ticket_html(p["id"],p["nombre_cliente"],p["celular"],
                                    p["direccion"],p["producto_nombre"],p["cantidad"],
                                    sub,envio,float(p["total"]),"Enviado",
                                    p["fecha"],p["hora_estimada"] or "",
                                    p["numero_ficha"] or "",is_admin=True)
        modales_env += """
<div class="overlay" id="%s">
  <div class="modal-box wide">
    <button class="modal-close" onclick="closeModal('%s')">✕</button>
    <div class="modal-title">🧾 Orden Enviada #%d</div>
    %s
    <button class="btn btp btb" style="margin-top:13px" onclick="printTicket('%s')">🖨️ Imprimir</button>
  </div>
</div>""" % (mid_env, mid_env, p["id"], tk_html_env, mid_env)

        filas_env += """<tr style="opacity:.85">
  <td><strong>#%d</strong></td>
  <td><span class="ficha">%s</span></td>
  <td><strong>%s</strong></td>
  <td>%s</td>
  <td style="color:#faa307;font-weight:700">%s</td>
  <td style="font-size:.78rem;color:#aaa">%s</td>
  <td>
    <button class="btn btenv" style="font-size:.77rem;padding:5px 9px"
            onclick="openModal('%s')">🧾 Ver</button>
  </td>
</tr>""" % (p["id"], ficha, p["nombre_cliente"], p["producto_nombre"],
            fmtp(float(p["total"])), p["fecha"], mid_env)

    filas_prod = ""; modales_prod = ""
    for p in prods:
        mid_ep = "moEP%d" % p["id"]
        modales_prod += """
<div class="overlay" id="%s">
  <div class="modal-box">
    <button class="modal-close" onclick="closeModal('%s')">✕</button>
    <div class="modal-title">✏️ Editar Producto</div>
    <form method="POST" action="/admin/edit-prod">
      <input type="hidden" name="producto_id" value="%d">
      <div class="fg"><label>Nombre</label>
        <input type="text" name="nombre" value="%s" required></div>
      <div class="fg"><label>Precio (₡)</label>
        <input type="number" name="precio" value="%g" required min="0" step="100"></div>
      <button type="submit" class="btn btp btb">💾 Guardar</button>
    </form>
  </div>
</div>""" % (mid_ep, mid_ep, p["id"], p["nombre"], p["precio"])

        filas_prod += """<tr>
  <td>%s</td>
  <td style="color:#faa307;font-weight:700">%s</td>
  <td style="display:flex;gap:6px;flex-wrap:wrap">
    <button class="btn btw" style="font-size:.8rem;padding:5px 9px"
            onclick="openModal('%s')">✏️ Editar</button>
    <a href="/admin/del-prod/%d"
       onclick="return confirm('Eliminar este producto?')"
       class="btn btd" style="font-size:.8rem;padding:5px 9px">🗑️ Borrar</a>
  </td>
</tr>""" % (p["nombre"], fmtp(p["precio"]), mid_ep, p["id"])

    graf_html = ('<div style="text-align:center"><img src="data:image/png;base64,%s" style="max-width:100%%;border-radius:var(--r)"></div>' % grafica) if grafica else '<p style="text-align:center;color:#aaa">Haz clic en Generar Grafica.</p>'

    # ── CAMBIO 1: cabecera con columna Dirección Envío ──
    tabla_ped = """<div class="pnl"><h2>📋 Pedidos Activos — en orden de llegada (%d)</h2>
<div class="tw"><table>
<thead><tr><th>#</th><th>Ficha</th><th>Nombre</th><th>Producto</th><th>Direccion Envio</th><th>Estado</th><th>Acciones</th></tr></thead>
<tbody>%s</tbody></table></div></div>""" % (
        len(peds_activos),
        filas_ped or '<tr><td colspan="7" style="text-align:center;color:#aaa;padding:20px">No hay pedidos activos.</td></tr>')

    tabla_env = """<div class="env-section"><h2>🚀 Pedidos Enviados — Historial (%d)</h2>
<div class="tw"><table>
<thead><tr><th>#</th><th>Ficha</th><th>Nombre</th><th>Producto</th><th>Total</th><th>Fecha</th><th>Ver</th></tr></thead>
<tbody>%s</tbody></table></div></div>%s""" % (
        len(peds_enviados),
        filas_env or '<tr><td colspan="7" style="text-align:center;color:#9b59b6;padding:20px;opacity:.6">Sin pedidos enviados aun.</td></tr>',
        modales_env)

    tabla_prod = """<div class="ag">
<div class="pnl"><h2>➕ Agregar Producto</h2>
<form method="POST" action="/admin/add-prod" enctype="multipart/form-data">
  <div class="fg"><label>Nombre</label><input type="text" name="nombre" required placeholder="Nombre del producto"></div>
  <div class="fg"><label>Precio (₡)</label><input type="number" name="precio" required min="0" step="100" placeholder="12000"></div>
  <div class="fg"><label>Imagen (opcional)</label><input type="file" name="imagen" accept="image/*"></div>
  <button type="submit" class="btn bts btb">✅ Agregar</button>
</form></div>
<div class="pnl"><h2>📦 Productos del Menu</h2>
<div class="tw"><table><thead><tr><th>Nombre</th><th>Precio</th><th>Acciones</th></tr></thead>
<tbody>%s</tbody></table></div></div></div>""" % (filas_prod or '<tr><td colspan="3" style="text-align:center;color:#aaa">No hay productos.</td></tr>')

    # ── CAMBIO 2: Pestaña Mi Restaurante ──
    nombre_actual = cfg.get("nombre_sitio","RestauranteApp")
    logo_actual   = cfg.get("logo_sitio","")
    logo_preview  = ""
    if logo_actual:
        logo_preview = '<div style="margin-bottom:12px"><p style="font-size:.82rem;color:#aaa;margin-bottom:6px">Logo actual:</p><img src="data:image/jpeg;base64,%s" class="logo-prev"></div>' % logo_actual

    tab_conf = """<div class="conf-pnl">
  <h2>🎨 Personalizar Pagina de Inicio</h2>
  <form method="POST" action="/admin/config-sitio" enctype="multipart/form-data">
    <div class="fg"><label>Nombre del Restaurante</label>
      <input type="text" name="nombre_sitio" value="%s" required
             placeholder="Ej: Pizzeria Don Marco"></div>
    %s
    <div class="fg"><label>Logo / Foto del Restaurante</label>
      <input type="file" name="logo" accept="image/*"></div>
    <p style="font-size:.8rem;color:#aaa;margin-bottom:14px">
      💡 El nombre y logo aparecen en la barra de navegacion y en la bienvenida de la pagina de inicio.
    </p>
    <button type="submit" class="btn bts btb">💾 Guardar Cambios</button>
  </form>
</div>""" % (nombre_actual, logo_preview)

    # Panel maestro (solo visible con contraseña maestra)
    if session.get("master"):
        activo_ahora = cfg.get("sitio_activo","1") == "1"
        if activo_ahora:
            master_btn = '<a href="/admin/toggle-sitio" class="btn btd" style="font-size:1rem;padding:12px 28px" onclick="return confirm(&quot;Desactivar el sitio del cliente?&quot;)">&#128274; Desactivar Sitio</a>'
            master_estado = '<span style="color:#2ecc71;font-weight:700">&#10003; ACTIVO</span>'
        else:
            master_btn = '<a href="/admin/toggle-sitio" class="btn bts" style="font-size:1rem;padding:12px 28px">&#10003; Activar Sitio</a>'
            master_estado = '<span style="color:#e74c3c;font-weight:700">&#128274; DESACTIVADO</span>'
        master_panel = """<div style="background:rgba(155,89,182,.15);border:2px solid #9b59b6;border-radius:12px;padding:20px;margin-bottom:20px">
  <p style="color:#9b59b6;font-weight:800;font-size:1rem;margin-bottom:14px">&#128273; Panel Maestro &mdash; Estado del sitio: """ + master_estado + """</p>
  <div style="display:flex;gap:12px;flex-wrap:wrap">""" + master_btn + """</div>
</div>"""
    else:
        master_panel = ""

    # Pestaña Mi Restaurante
    nombre_actual = cfg.get("nombre_sitio","RestauranteApp")
    logo_actual   = cfg.get("logo_sitio","")
    logo_preview  = ('<div style="margin-bottom:10px"><p style="font-size:.82rem;color:#aaa;margin-bottom:6px">Logo actual:</p><img src="data:image/jpeg;base64,%s" style="height:70px;width:70px;object-fit:cover;border-radius:10px;border:2px solid var(--p)"></div>' % logo_actual) if logo_actual else ""
    activo = cfg.get("sitio_activo","1") == "1"
    if activo:
        estado_sitio = '<div style="background:rgba(46,204,113,.15);border:1px solid #2ecc71;border-radius:10px;padding:13px;margin-bottom:16px;text-align:center"><span style="color:#2ecc71;font-weight:700;font-size:1rem">&#10003; Sitio ACTIVO &mdash; clientes pueden acceder</span></div>'
    else:
        estado_sitio = '<div style="background:rgba(231,76,60,.15);border:1px solid #e74c3c;border-radius:10px;padding:13px;margin-bottom:16px;text-align:center"><span style="color:#e74c3c;font-weight:700;font-size:1rem">&#128274; Sitio DESACTIVADO</span></div>'
    if session.get("master"):
        if activo:
            btn_toggle = '<a href="/admin/toggle-sitio" class="btn btd" style="width:100%;justify-content:center;margin-bottom:20px" onclick="return confirm(&quot;Desactivar el sitio?&quot;)">&#128274; Desactivar Sitio</a>'
        else:
            btn_toggle = '<a href="/admin/toggle-sitio" class="btn bts" style="width:100%;justify-content:center;margin-bottom:20px">&#10003; Activar Sitio</a>'
    else:
        btn_toggle = ""
    tab_conf = '''<div style="background:var(--cd);border-radius:var(--r);padding:22px;border:2px solid var(--s);margin-bottom:20px">
  <h2 style="font-size:1.12rem;margin-bottom:16px;color:var(--s);border-bottom:1px solid var(--s);padding-bottom:8px">🎨 Mi Restaurante</h2>''' + estado_sitio + btn_toggle + '''
  <hr style="border-color:#2a2a4a;margin-bottom:18px">
  <h3 style="color:var(--s);font-size:.95rem;margin-bottom:14px">Personalizar apariencia</h3>
  <form method="POST" action="/admin/config-sitio" enctype="multipart/form-data">''' + logo_preview + '''
    <div class="fg"><label>Nombre del Restaurante</label>
      <input type="text" name="nombre_sitio" value="''' + nombre_actual + '''" required placeholder="Ej: Pizzeria Don Marco"></div>
    <div class="fg"><label>Logo / Foto del Restaurante</label>
      <input type="file" name="logo" accept="image/*"></div>
    <p style="font-size:.8rem;color:#aaa;margin-bottom:14px">💡 El nombre y logo aparecen en el navbar y en la bienvenida del inicio.</p>
    <button type="submit" class="btn bts btb">💾 Guardar Cambios</button>
  </form>
</div>'''
    html  = head("admin", cfg)
    html += "<div class=\"con\">"
    html += "<div style=\"display:flex;justify-content:space-between;align-items:center;margin-bottom:20px\">"
    html += "<h1 style=\"font-size:1.65rem\">&#9881;&#65039; Panel de Administracion</h1>"
    html += "<a href=\"/admin/logout\" class=\"btn btd\">&#128682; Salir</a></div>"
    html += alerta(msg, tipo)
    html += banner_proceso(peds_activos)
    html += stats_html
    html += master_panel
    html += "<div style=\"display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap\">"
    html += "<button class=\"btn btp\" onclick=\"showTab('ped')\">&#128203; Pedidos Activos</button>"
    html += "<button class=\"btn btenv\" onclick=\"showTab('env')\">&#128640; Enviados</button>"
    html += "<button class=\"btn btw\" onclick=\"showTab('prod')\">&#127828; Productos</button>"
    html += "<button class=\"btn bts\" onclick=\"showTab('conf')\">&#127912; Mi Restaurante</button>"
    html += "<button class=\"btn bti\" onclick=\"showTab('stats')\">&#128202; Estadisticas</button>"
    html += "</div>"
    html += "<div id=\"tab_ped\">" + tabla_ped + "</div>"
    html += "<div id=\"tab_env\" style=\"display:none\">" + tabla_env + "</div>"
    html += "<div id=\"tab_prod\" style=\"display:none\">" + tabla_prod + "</div>"
    html += "<div id=\"tab_conf\" style=\"display:none\">" + tab_conf + "</div>"
    html += "<div id=\"tab_stats\" style=\"display:none\"><div class=\"pnl\"><h2>&#128202; Estadisticas</h2>"
    html += "<div style=\"text-align:center;margin-bottom:16px\">"
    html += "<a href=\"/admin/grafica\" class=\"btn btp\">&#128260; Generar Grafica</a></div>"
    html += graf_html + "</div></div>"
    html += "</div>"
    html += modales_ped + modales_prod
    html += FOOT + MODAL_JS + "</body></html>"
    return html



@app.route("/admin/toggle-sitio")
def toggle_sitio():
    if not session.get("admin"): return redirect(url_for("admin_login"))
    db = get_db()
    row = db.execute("SELECT valor FROM config_sitio WHERE clave='sitio_activo'").fetchone()
    nuevo = "0" if (row and row["valor"]=="1") else "1"
    db.execute("INSERT OR REPLACE INTO config_sitio(clave,valor) VALUES('sitio_activo',?)",(nuevo,))
    db.commit(); db.close()
    msg = "✅ Sitio ACTIVADO — los clientes pueden acceder." if nuevo=="1" else "🔒 Sitio DESACTIVADO — los clientes ven pagina de bloqueo."
    return redirect(url_for("admin", msg=msg, tipo="ok"))

@app.route("/admin/config-sitio", methods=["POST"])
def config_sitio():
    if not session.get("admin"): return redirect(url_for("admin_login"))
    nombre = request.form.get("nombre_sitio","").strip() or "RestauranteApp"
    db = get_db()
    db.execute("INSERT OR REPLACE INTO config_sitio(clave,valor) VALUES('nombre_sitio',?)", (nombre,))
    if "logo" in request.files:
        f2 = request.files["logo"]
        if f2 and f2.filename:
            raw = f2.read()
            if len(raw) < 2_000_000:
                db.execute("INSERT OR REPLACE INTO config_sitio(clave,valor) VALUES('logo_sitio',?)", (base64.b64encode(raw).decode(),))
    db.commit(); db.close()
    return redirect(url_for("admin", msg="✅ Restaurante actualizado.", tipo="ok"))

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    err = ""
    if request.method == "POST":
        pw = request.form["password"]
        if pw == MASTER_PASS:
            session["admin"] = True
            session["master"] = True
            return redirect(url_for("admin"))
        elif pw == ADMIN_PASS:
            session["admin"] = True
            session["master"] = False
            return redirect(url_for("admin"))
        err = "❌ Contrasena incorrecta."
    return head("admin") + """
<div class="lb2"><h2>🔐 Panel Admin</h2>%s
  <form method="POST">
    <div class="fg"><label>Contrasena</label>
      <input type="password" name="password" placeholder="••••••••" required autofocus></div>
    <button type="submit" class="btn btp btb">Ingresar</button>
  </form>
  <p style="text-align:center;margin-top:13px;color:#aaa;font-size:.82rem">Por defecto: <strong></strong></p>
</div>""" % alerta(err,"er") + FOOT + MODAL_JS + "</body></html>"


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    session.pop("master", None)
    return redirect(url_for("index"))

@app.route("/admin/add-prod", methods=["POST"])
def add_prod():
    if not session.get("admin"): return redirect(url_for("admin_login"))
    n = request.form["nombre"].strip()
    p = float(request.form["precio"])
    img = None
    if "imagen" in request.files:
        f2 = request.files["imagen"]
        if f2 and f2.filename:
            raw = f2.read()
            if len(raw) < 2_000_000: img = base64.b64encode(raw).decode()
    db = get_db()
    db.execute("INSERT INTO productos(nombre,precio,imagen) VALUES(?,?,?)",(n,p,img))
    db.commit(); db.close()
    return redirect(url_for("admin", msg="✅ Producto agregado.", tipo="ok"))

@app.route("/admin/del-prod/<int:pid>")
def del_prod(pid):
    if not session.get("admin"): return redirect(url_for("admin_login"))
    db = get_db()
    db.execute("DELETE FROM productos WHERE id=?",(pid,))
    db.commit(); db.close()
    return redirect(url_for("admin", msg="🗑️ Producto eliminado.", tipo="ok"))

@app.route("/admin/edit-prod", methods=["POST"])
def edit_prod():
    if not session.get("admin"): return redirect(url_for("admin_login"))
    db = get_db()
    db.execute("UPDATE productos SET nombre=?,precio=? WHERE id=?",
               (request.form["nombre"].strip(), float(request.form["precio"]), request.form["producto_id"]))
    db.commit(); db.close()
    return redirect(url_for("admin", msg="✅ Producto actualizado.", tipo="ok"))

@app.route("/admin/upd-ped", methods=["POST"])
def upd_ped():
    if not session.get("admin"): return redirect(url_for("admin_login"))
    f   = request.form
    pid = f["pedido_id"]
    sub = float(f.get("total_original",0))
    env = float(f.get("costo_envio",0))
    tot = float(f["total"])
    hr  = f.get("hora_estimada","").strip()
    est = f["estado"]
    if est == "Enviado":
        cc = "aceptado"
    elif env > 0:
        cc = "revision"
    else:
        cc = "pendiente"
    db  = get_db()
    db.execute("""UPDATE pedidos SET total=?,total_original=?,costo_envio=?,
        hora_estimada=?,estado=?,confirmacion=? WHERE id=?""",
        (tot,sub,env,hr,est,cc,pid))
    db.commit(); db.close()
    if est == "Enviado":
        msg = "🚀 Pedido #%s marcado como ENVIADO. El cliente lo vera en su seguimiento." % pid
    elif env > 0:
        msg = "✅ Pedido #%s actualizado con envio %s. El cliente debera confirmar." % (pid,fmtp(env))
    else:
        msg = "✅ Pedido #%s actualizado." % pid
    return redirect(url_for("admin", msg=msg, tipo="ok"))

@app.route("/admin/grafica")
def grafica_route():
    if not session.get("admin"): return redirect(url_for("admin_login"))
    db    = get_db()
    peds  = db.execute("SELECT * FROM pedidos").fetchall()
    prods_all = db.execute("SELECT * FROM productos ORDER BY id DESC").fetchall()
    db.close()
    ventas = {}
    for p in peds:
        ventas[p["producto_nombre"]] = ventas.get(p["producto_nombre"],0) + p["cantidad"]
    if not ventas:
        return redirect(url_for("admin", msg="No hay pedidos para generar estadisticas.", tipo="in"))
    noms  = list(ventas.keys())
    cants = [ventas[n] for n in noms]
    cols  = ["#e85d04","#faa307","#f48c06","#dc2f02","#d62828","#e9c46a","#2ecc71","#3498db","#9b59b6","#1abc9c"][:len(noms)]
    fig, axes = plt.subplots(1,2,figsize=(14,6))
    fig.patch.set_facecolor("#0f0f1a")
    ax1 = axes[0]; ax1.set_facecolor("#16213e")
    bars = ax1.bar(range(len(noms)),cants,color=cols,edgecolor="#2a2a4a",linewidth=1.5)
    ax1.set_xticks(range(len(noms)))
    ax1.set_xticklabels([n[:16] for n in noms],rotation=28,ha="right",color="#eaeaea",fontsize=9)
    ax1.set_title("Unidades Vendidas",color="#faa307",fontsize=12,fontweight="bold",pad=12)
    ax1.set_ylabel("Unidades",color="#aaa"); ax1.tick_params(colors="#aaa")
    for sp in ax1.spines.values(): sp.set_color("#2a2a4a")
    for b,v in zip(bars,cants):
        ax1.text(b.get_x()+b.get_width()/2,b.get_height()+.05,str(v),ha="center",color="#faa307",fontsize=10,fontweight="bold")
    ax2 = axes[1]; ax2.set_facecolor("#16213e")
    wedges,texts,autotexts = ax2.pie(cants,colors=cols,autopct="%1.1f%%",startangle=90,pctdistance=.8,wedgeprops={"edgecolor":"#0f0f1a","linewidth":2})
    for t in texts: t.set_color("#eaeaea")
    for t in autotexts: t.set_color("white"); t.set_fontweight("bold")
    ax2.set_title("Distribucion",color="#faa307",fontsize=12,fontweight="bold",pad=12)
    patches = [mpatches.Patch(color=c,label=n[:18]) for c,n in zip(cols,noms)]
    ax2.legend(handles=patches,loc="lower center",bbox_to_anchor=(.5,-.15),ncol=2,fontsize=8,facecolor="#16213e",edgecolor="#2a2a4a",labelcolor="#eaeaea")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf,format="png",bbox_inches="tight",facecolor="#0f0f1a",dpi=120)
    buf.seek(0)
    g64 = base64.b64encode(buf.read()).decode()
    plt.close()
    db2 = get_db()
    peds2  = db2.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
    prods2 = db2.execute("SELECT * FROM productos ORDER BY id DESC").fetchall()
    db2.close()
    return render_admin_page(peds2, prods2, g64, "", "ok")


if __name__ == "__main__":
    init_db()
    print("\n" + "="*48)
    print("  🍽️  RestauranteApp lista!")
    print("="*48)
    print("  Cliente:  http://localhost:5000")
    print("  Admin:    http://localhost:5000/admin")
    print("  Password: ")
    print("="*48 + "\n")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
