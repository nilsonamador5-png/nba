"""
RestauranteApp — pip install flask matplotlib pillow — python app.py
Admin: http://localhost:5000/admin  pass:
"""
from flask import Flask, request, redirect, url_for, session, Response
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
    db.execute("INSERT OR IGNORE INTO config_sitio(clave,valor) VALUES('nombre_sitio','RestauranteApp')")
    db.execute("INSERT OR IGNORE INTO config_sitio(clave,valor) VALUES('logo_sitio','')")
    if db.execute("SELECT COUNT(*) FROM productos").fetchone()[0] == 0:
        demos = [("Hamburguesa Clasica",8500),("Pizza Margarita",12000),
                 ("Tacos x3",9000),("Pollo Frito",10500),
                 ("Ensalada Cesar",7500),("Papas Fritas",4000)]
        db.executemany("INSERT INTO productos(nombre,precio,imagen) VALUES(?,?,NULL)", demos)
    db.commit(); db.close()


def sitio_activo():
    db = get_db()
    row = db.execute("SELECT valor FROM config_sitio WHERE clave='sitio_activo'").fetchone()
    db.close()
    return (row["valor"] == "1") if row else True

def pagina_bloqueada():
    return """<!DOCTYPE html><html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Servicio no disponible</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Bebas Neue','Segoe UI',sans-serif;background:#141414;color:#eaeaea;
  min-height:100vh;display:flex;align-items:center;justify-content:center}
.box{text-align:center;padding:50px 30px;max-width:480px}
.icon{font-size:5rem;margin-bottom:20px}
h1{font-size:2rem;color:#E50914;margin-bottom:14px;letter-spacing:2px}
p{color:#aaa;font-size:1rem;line-height:1.6}
</style></head><body>
<div class="box">
  <div class="icon">🔒</div>
  <h1>SERVICIO NO DISPONIBLE</h1>
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

# ══════════════════════════════════════════════════════════════
# CSS ESTILO NETFLIX + MARCA DE AGUA NBA
# ══════════════════════════════════════════════════════════════
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Montserrat:wght@400;600;700;800&display=swap');

:root{
  --p:#E50914;
  --s:#B20710;
  --dk:#141414;
  --cd:#1f1f1f;
  --tx:#eaeaea;
  --mu:#b3b3b3;
  --ok:#46d369;
  --wn:#e87c03;
  --er:#E50914;
  --bl:#0071eb;
  --env:#6200ea;
  --r:6px;
  --nba-blue:#1d428a;
  --nba-red:#C8102E;
}
*{box-sizing:border-box;margin:0;padding:0}

/* ── MARCA DE AGUA NBA ── */
body::before{
  content:"NBA";
  position:fixed;
  bottom:30px;
  right:40px;
  font-family:'Bebas Neue',sans-serif;
  font-size:7rem;
  font-weight:900;
  color:rgba(229,9,20,0.06);
  letter-spacing:8px;
  z-index:0;
  pointer-events:none;
  user-select:none;
  line-height:1;
}
body::after{
  content:"NBA";
  position:fixed;
  top:30%;
  left:-20px;
  font-family:'Bebas Neue',sans-serif;
  font-size:5rem;
  font-weight:900;
  color:rgba(29,66,138,0.05);
  letter-spacing:6px;
  z-index:0;
  pointer-events:none;
  user-select:none;
  transform:rotate(-90deg);
  transform-origin:left center;
}

body{
  font-family:'Montserrat',sans-serif;
  background:#141414;
  color:var(--tx);
  min-height:100vh;
  position:relative;
}

/* ── NAVBAR ── */
nav{
  background:linear-gradient(180deg,rgba(0,0,0,.9) 0%,rgba(20,20,20,.7) 100%);
  border-bottom:3px solid var(--p);
  padding:14px 40px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  position:sticky;
  top:0;
  z-index:50;
  backdrop-filter:blur(10px);
  box-shadow:0 4px 30px rgba(229,9,20,.25);
}
.nb{
  font-family:'Bebas Neue',sans-serif;
  font-size:2rem;
  font-weight:400;
  color:#fff;
  text-decoration:none;
  display:flex;
  align-items:center;
  gap:12px;
  letter-spacing:3px;
}
.nb img{height:38px;width:38px;object-fit:cover;border-radius:4px;border:2px solid var(--p)}
.nb-nba{
  font-family:'Bebas Neue',sans-serif;
  font-size:.75rem;
  letter-spacing:4px;
  color:var(--nba-red);
  background:var(--nba-blue);
  padding:2px 7px;
  border-radius:3px;
  margin-left:4px;
  vertical-align:middle;
}
.nl{display:flex;gap:6px;flex-wrap:wrap}
.nl a{
  color:var(--mu);
  text-decoration:none;
  padding:7px 16px;
  border-radius:4px;
  font-size:.85rem;
  font-weight:600;
  letter-spacing:.5px;
  text-transform:uppercase;
  transition:all .2s;
  border:1px solid transparent;
}
.nl a:hover,.nl a.act{
  background:var(--p);
  color:#fff;
  border-color:var(--s);
}

/* ── CONTENEDOR ── */
.con{max-width:1100px;margin:0 auto;padding:30px 20px;position:relative;z-index:1}

/* ── HERO ── */
.hero{
  background:linear-gradient(135deg,#000 0%,#1a0000 50%,#141414 100%);
  border-radius:var(--r);
  padding:50px 40px;
  text-align:center;
  margin-bottom:28px;
  border:1px solid rgba(229,9,20,.3);
  box-shadow:0 0 60px rgba(229,9,20,.15),inset 0 0 60px rgba(0,0,0,.5);
  position:relative;
  overflow:hidden;
}
.hero::before{
  content:"NBA";
  position:absolute;
  top:50%;left:50%;
  transform:translate(-50%,-50%);
  font-family:'Bebas Neue',sans-serif;
  font-size:12rem;
  color:rgba(229,9,20,0.04);
  letter-spacing:20px;
  pointer-events:none;
  white-space:nowrap;
}
.hero h1{
  font-family:'Bebas Neue',sans-serif;
  font-size:3rem;
  letter-spacing:4px;
  margin-bottom:10px;
  text-shadow:0 0 30px rgba(229,9,20,.5);
}
.hero p{font-size:1rem;color:var(--mu)}

/* ── CARDS ── */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}
.card{
  background:#181818;
  border-radius:var(--r);
  border:1px solid #2a2a2a;
  overflow:hidden;
  transition:transform .25s,box-shadow .25s,border-color .25s;
  cursor:pointer;
}
.card:hover{
  transform:scale(1.04) translateY(-4px);
  box-shadow:0 10px 40px rgba(229,9,20,.35);
  border-color:var(--p);
}
.ci{
  width:100%;height:150px;
  background:linear-gradient(135deg,#1a0000,#2a2a2a);
  display:flex;align-items:center;justify-content:center;font-size:3.5rem;
}
.cb{padding:16px}
.ct{font-size:1rem;font-weight:700;margin-bottom:6px;letter-spacing:.5px}
.cp{color:var(--p);font-size:1.2rem;font-weight:800;margin-bottom:12px;font-family:'Bebas Neue',sans-serif;letter-spacing:1px}

/* ── FORMS ── */
.fg{margin-bottom:14px}
.fg label{
  display:block;font-size:.78rem;color:var(--mu);margin-bottom:5px;
  font-weight:700;text-transform:uppercase;letter-spacing:.8px;
}
.fg input,.fg select{
  width:100%;padding:11px 14px;
  background:#333;
  border:1.5px solid #444;
  border-radius:4px;color:var(--tx);font-size:.93rem;
  font-family:'Montserrat',sans-serif;
  transition:border-color .2s;
}
.fg input:focus,.fg select:focus{outline:none;border-color:var(--p);background:#3a0000}

/* ── BUTTONS ── */
.btn{
  display:inline-flex;align-items:center;gap:6px;
  padding:10px 22px;border:none;border-radius:4px;
  font-size:.88rem;font-weight:700;cursor:pointer;
  transition:all .2s;text-decoration:none;white-space:nowrap;
  text-transform:uppercase;letter-spacing:.8px;
  font-family:'Montserrat',sans-serif;
}
.btp{background:var(--p);color:#fff}.btp:hover{background:#f40612;box-shadow:0 0 20px rgba(229,9,20,.5)}
.bts{background:var(--ok);color:#000}.bts:hover{background:#5ce479}
.btw{background:var(--wn);color:#fff}.btw:hover{background:#c96d02}
.btd{background:#333;color:#fff;border:1px solid #555}.btd:hover{background:var(--er)}
.bti{background:var(--bl);color:#fff}.bti:hover{background:#0060cc}
.btenv{background:var(--env);color:#fff}.btenv:hover{background:#5000c9}
.btb{width:100%;justify-content:center}

/* ── BADGES ── */
.bdg{display:inline-block;padding:3px 10px;border-radius:3px;font-size:.73rem;font-weight:700;letter-spacing:.5px;text-transform:uppercase}
.bp{background:rgba(232,124,3,.2);color:var(--wn);border:1px solid var(--wn)}
.bc{background:rgba(70,211,105,.15);color:var(--ok);border:1px solid var(--ok)}
.bx{background:rgba(229,9,20,.15);color:var(--er);border:1px solid var(--er)}
.br{background:rgba(0,113,235,.15);color:var(--bl);border:1px solid var(--bl)}
.benv{background:rgba(98,0,234,.15);color:#bb86fc;border:1px solid #6200ea}

/* ── TABLA ── */
.tw{overflow-x:auto}
table{width:100%;border-collapse:collapse}
th{
  background:#0a0a0a;padding:11px 13px;text-align:left;
  color:var(--p);font-size:.75rem;text-transform:uppercase;letter-spacing:1px;
  font-family:'Bebas Neue',sans-serif;font-size:.9rem;
}
td{padding:10px 13px;border-bottom:1px solid #2a2a2a;font-size:.87rem;vertical-align:middle}
tr:hover td{background:rgba(229,9,20,.05)}

/* ── PANELS ── */
.ag{display:grid;grid-template-columns:1fr 2fr;gap:20px}
@media(max-width:768px){.ag{grid-template-columns:1fr}}
.pnl{background:#181818;border-radius:var(--r);padding:22px;border:1px solid #2a2a2a;margin-bottom:20px}
.pnl h2{
  font-family:'Bebas Neue',sans-serif;font-size:1.3rem;letter-spacing:2px;
  margin-bottom:16px;color:var(--p);border-bottom:2px solid #2a2a2a;padding-bottom:8px;
}
.tr2{background:#181818;border-radius:var(--r);padding:22px;margin-top:16px;border:1px solid #2a2a2a}
.pi{background:#1f1f1f;border-radius:var(--r);padding:15px;margin-bottom:12px;border-left:4px solid var(--p)}
.pm{display:flex;gap:14px;flex-wrap:wrap;margin-top:9px;font-size:.83rem;color:var(--mu)}

/* ── STATS ── */
.sg{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;margin-bottom:20px}
.sc{
  background:#181818;border-radius:var(--r);padding:18px;text-align:center;
  border:1px solid #2a2a2a;border-top:3px solid var(--p);
  transition:transform .2s;
}
.sc:hover{transform:translateY(-2px)}
.sc .nm{font-family:'Bebas Neue',sans-serif;font-size:2rem;font-weight:400;color:var(--p);letter-spacing:2px}
.sc .lb{font-size:.75rem;color:var(--mu);margin-top:2px;text-transform:uppercase;letter-spacing:.5px}

/* ── LOGIN ── */
.lb2{
  max-width:380px;margin:70px auto;background:#181818;border-radius:var(--r);
  padding:40px;border:1px solid #333;box-shadow:0 0 60px rgba(229,9,20,.2);
}
.lb2 h2{
  text-align:center;margin-bottom:26px;color:#fff;
  font-family:'Bebas Neue',sans-serif;font-size:2rem;letter-spacing:3px;
}

/* ── ALERTAS ── */
.al{padding:12px 16px;border-radius:4px;margin-bottom:13px;font-size:.88rem;font-weight:600}
.al-ok{background:rgba(70,211,105,.12);border:1px solid var(--ok);color:var(--ok)}
.al-er{background:rgba(229,9,20,.12);border:1px solid var(--er);color:var(--er)}
.al-in{background:rgba(232,124,3,.12);border:1px solid var(--wn);color:var(--wn)}

/* ── PEDIDOS EN PROCESO ── */
.ob{background:#181818;border-radius:var(--r);padding:18px;margin-bottom:22px;border:1px solid #2a2a2a;border-left:4px solid var(--p)}
.ob h3{color:var(--p);font-family:'Bebas Neue',sans-serif;font-size:1.2rem;letter-spacing:2px;margin-bottom:12px}
.oc{
  background:#1f1f1f;border-radius:4px;padding:9px 14px;
  display:flex;align-items:center;gap:10px;margin-bottom:6px;
  border-left:3px solid var(--p);flex-wrap:wrap;
}
.on2{background:var(--p);color:#fff;border-radius:3px;padding:2px 8px;font-weight:800;font-size:.78rem}
.ficha{background:var(--env);color:#fff;border-radius:3px;padding:2px 8px;font-weight:800;font-size:.78rem}

/* ── MODAL ── */
.overlay{
  display:none;position:fixed;top:0;left:0;width:100%;height:100%;
  background:rgba(0,0,0,.88);z-index:99999;
  justify-content:center;align-items:flex-start;
  padding:30px 15px;overflow-y:auto;
  backdrop-filter:blur(4px);
}
.overlay.show{display:flex}
.modal-box{
  background:#181818;border-radius:var(--r);padding:28px;
  width:100%;max-width:460px;border:2px solid var(--p);
  position:relative;margin:auto;box-shadow:0 0 60px rgba(229,9,20,.3);
}
.modal-box.wide{max-width:440px}
.modal-close{
  position:absolute;top:12px;right:14px;
  background:rgba(255,255,255,.1);border:none;color:#fff;
  font-size:1.3rem;font-weight:bold;cursor:pointer;
  border-radius:4px;width:32px;height:32px;
  display:flex;align-items:center;justify-content:center;
  transition:background .2s;
}
.modal-close:hover{background:var(--er)}
.modal-title{
  font-family:'Bebas Neue',sans-serif;font-size:1.4rem;letter-spacing:2px;
  color:var(--p);margin-bottom:18px;padding-right:35px;
}

/* ── TICKET ── */
.tk{background:#fff;color:#111;border-radius:6px;padding:20px;
  font-family:'Courier New',monospace;border:1px dashed #bbb;margin-top:4px}
.tkh{text-align:center;border-bottom:2px dashed #ccc;padding-bottom:10px;margin-bottom:10px}
.tkh h2{font-size:1.1rem;color:#111}
.tkr{display:flex;justify-content:space-between;padding:3px 0;font-size:.87rem;color:#111}
.tkr.bld{font-weight:800;font-size:.95rem}
.tkd{border:none;border-top:1px dashed #bbb;margin:7px 0}
.tkf{text-align:center;margin-top:10px;border-top:2px dashed #ccc;padding-top:9px;font-size:.75rem;color:#666}

/* ── CONFIGURACION ── */
.conf-pnl{background:#181818;border-radius:var(--r);padding:22px;border:2px solid var(--p);margin-bottom:20px}
.conf-pnl h2{font-family:'Bebas Neue',sans-serif;font-size:1.3rem;letter-spacing:2px;margin-bottom:16px;color:var(--p);border-bottom:1px solid var(--p);padding-bottom:8px}
.logo-prev{width:70px;height:70px;object-fit:cover;border-radius:6px;border:2px solid var(--p);display:block;margin-bottom:10px}

/* ── ENVIADOS ── */
.env-section{background:#181818;border-radius:var(--r);padding:22px;margin-bottom:20px;border:2px solid var(--env)}
.env-section h2{font-family:'Bebas Neue',sans-serif;font-size:1.3rem;letter-spacing:2px;margin-bottom:16px;color:#bb86fc;border-bottom:1px solid var(--env);padding-bottom:8px}
.env-row{background:#1f1f1f;border-radius:4px;padding:10px 14px;margin-bottom:8px;border-left:4px solid var(--env);display:flex;align-items:center;gap:12px;flex-wrap:wrap}

/* ── EB REVISION ── */
.eb{background:rgba(0,113,235,.08);border:2px solid #0071eb;border-radius:6px;padding:15px;margin:10px 0}

/* ── FOOTER ── */
footer{
  text-align:center;padding:26px;color:#555;font-size:.78rem;
  border-top:1px solid #2a2a2a;margin-top:36px;
  letter-spacing:1px;text-transform:uppercase;position:relative;z-index:1;
}
footer span{color:var(--p);font-family:'Bebas Neue',sans-serif;letter-spacing:3px;font-size:.9rem}
"""

TK_CSS = "body{font-family:monospace;padding:20px;max-width:370px;margin:0 auto}.tkr{display:flex;justify-content:space-between;padding:3px 0;font-size:.87rem}.tkd{border:none;border-top:1px dashed #bbb;margin:7px 0}.tkh{text-align:center;border-bottom:2px dashed #ccc;padding-bottom:10px;margin-bottom:10px}.tkf{text-align:center;margin-top:10px;border-top:2px dashed #ccc;padding-top:9px;font-size:.75rem;color:#666}.bld{font-weight:800;font-size:.95rem}"

def head(active, cfg=None):
    if cfg is None:
        cfg = get_config()
    nombre_sitio = cfg.get("nombre_sitio","RestauranteApp")
    logo_sitio   = cfg.get("logo_sitio","")
    links = [("menu","/","Menú"),("tracking","/mis-pedidos","Mis Pedidos"),("admin","/admin","Admin")]
    li = "".join('<a href="%s" class="%s">%s</a>' % (u,"act" if active==k else "",l) for k,u,l in links)
    logo_tag = ('<img src="data:image/jpeg;base64,%s">' % logo_sitio) if logo_sitio else "🍽️"
    return """<!DOCTYPE html><html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<title>%s</title><style>%s</style></head><body>
<nav><a class="nb" href="/">%s %s <span class="nb-nba">NBA</span></a><div class="nl">%s</div></nav>""" % (nombre_sitio, CSS, logo_tag, nombre_sitio, li)

FOOT = '<footer><p>RestauranteApp 2024 &nbsp;|&nbsp; <span>NBA</span> Edition</p></footer>'

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
        ficha_row = '<div class="tkr"><span>Ficha #:</span><strong style="color:#6200ea">%s</strong></div>' % numero_ficha
    col_map = {"aceptado":"#46d369","cancelado":"#E50914","revision":"#0071eb","pendiente":"#e87c03",
               "Confirmado":"#46d369","Cancelado":"#E50914","Pendiente":"#e87c03","Enviado":"#6200ea"}
    txt_map = {"aceptado":"Confirmado","cancelado":"Cancelado","revision":"En revision",
               "pendiente":"Pendiente","Confirmado":"Confirmado","Cancelado":"Cancelado",
               "Pendiente":"Pendiente","Enviado":"Enviado 🚀"}
    col = col_map.get(str(estado_o_cc),"#e87c03")
    txt = txt_map.get(str(estado_o_cc),"Pendiente")
    pie = "Panel Admin — NBA Edition" if is_admin else "Gracias por tu pedido! Guarda este comprobante."
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
  <div class="tkr bld"><span>TOTAL:</span><span style="color:#E50914;font-size:1.05rem">%s</span></div>
  <div style="margin-top:7px">
    <span style="background:%s;color:#fff;padding:3px 10px;border-radius:3px;font-size:.78rem">%s</span>
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
    <button class="btn btp btb" onclick="openModal('moPed%d')">🛒 PEDIR AHORA</button>
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
        <input type="text" id="tot%d_m" value="%s" readonly style="color:#E50914;font-weight:800;opacity:.9"></div>
      <button type="submit" class="btn btp btb">✅ CONFIRMAR PEDIDO</button>
    </form>
  </div>
</div>""" % (mid, mid, p["nombre"], p["id"], js_esc(p["nombre"]), p["precio"],
             p["id"], p["id"], p["precio"], p["id"], fmtp(p["precio"]))

    grid = '<div class="grid">%s</div>' % cards if cards else '<div class="al al-in">No hay productos.</div>'

    return head("menu", cfg) + """
<div class="con">
  <div class="hero">
    <h1>🍽️ BIENVENIDO A %s</h1>
    <p>Pide en linea y recibe en tu puerta</p>
  </div>
  %s%s
  <h2 style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;letter-spacing:3px;margin-bottom:16px">📋 NUESTRO MENÚ</h2>
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
                borde = "border-left-color:#6200ea;opacity:.85"
            elif cc=="revision":    borde="border-left-color:#0071eb"
            elif cc=="cancelado": borde="border-left-color:#E50914;opacity:.75"
            elif estado=="Confirmado": borde="border-left-color:#46d369"
            else: borde=""

            if estado == "Enviado":
                bdg = '<span class="bdg benv">🚀 Enviado</span>'
            elif cc=="revision":    bdg='<span class="bdg br">🔵 Revision de costo</span>'
            elif cc=="cancelado": bdg='<span class="bdg bx">❌ Cancelado</span>'
            elif cc=="aceptado":  bdg='<span class="bdg bc">✅ Confirmado</span>'
            else:                 bdg='<span class="bdg bp">⏳ Pendiente</span>'

            env_banner = ""
            if estado == "Enviado":
                env_banner = """<div style="background:rgba(98,0,234,.15);border:2px solid #6200ea;
                  border-radius:6px;padding:13px;margin:10px 0;text-align:center">
                  <p style="color:#bb86fc;font-weight:700;font-size:1rem">🚀 Tu pedido fue enviado!</p>
                  <p style="font-size:.85rem;color:#aaa;margin-top:5px">Pronto llegara a tu direccion</p>
                </div>"""

            caja = ""
            if envio > 0 and cc == "revision":
                caja = """<div class="eb">
  <p style="color:#0071eb;font-weight:700;font-size:.97rem;margin-bottom:10px">
    🚨 El restaurante agrego costo de envio — confirma tu pedido
  </p>
  <div style="display:flex;justify-content:space-between;padding:4px 0">
    <span>Subtotal:</span><strong>%s</strong></div>
  <div style="display:flex;justify-content:space-between;padding:4px 0">
    <span>Envio:</span><strong style="color:#e87c03">+ %s</strong></div>
  <div style="border-top:1px dashed #0071eb;margin:9px 0"></div>
  <div style="display:flex;justify-content:space-between;font-size:1.06rem;font-weight:800">
    <span>Total a pagar:</span><span style="color:#E50914">%s</span></div>
  <div style="display:flex;gap:10px;margin-top:13px">
    <a href="/confirmar/%d/aceptar/%s" class="btn bts" style="flex:1;justify-content:center">✅ ACEPTO</a>
    <a href="/confirmar/%d/cancelar/%s" class="btn btd" style="flex:1;justify-content:center"
       onclick="return confirm('Cancelar pedido?')">❌ CANCELAR</a>
  </div>
</div>""" % (fmtp(sub), fmtp(envio), fmtp(float(p["total"])),
             p["id"], celular, p["id"], celular)

            hora_sp = '<span style="color:#46d369">⏰ Llega: %s</span>' % p["hora_estimada"] if p["hora_estimada"] else ""
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
    <div class="modal-title">🧾 COMPROBANTE</div>
    %s
    <div style="display:flex;gap:10px;margin-top:13px">
      <button class="btn btp" style="flex:1;justify-content:center" onclick="printTicket('%s')">🖨️ IMPRIMIR</button>
      <a href="/descargar/%d" class="btn bts" style="flex:1;justify-content:center">⬇️ DESCARGAR</a>
    </div>
  </div>
</div>""" % (mid_tk, mid_tk, tk_html, mid_tk, p["id"])

            items += """<div class="pi" style="%s">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:9px;flex-wrap:wrap;gap:7px">
    <strong>🛒 %s</strong>%s%s</div>
  %s%s
  <div class="pm"><span>👤 %s</span><span>📍 %s</span>
    <span>Cant: %d</span><span style="color:#E50914;font-weight:700">%s</span>
    <span>%s</span>%s</div>
  <div style="margin-top:11px;display:flex;gap:8px;flex-wrap:wrap">
    <button class="btn bti" style="font-size:.83rem;padding:6px 13px"
            onclick="openModal('moTk%d')">🧾 VER MI ORDEN</button>
    <a href="/descargar/%d" class="btn btw" style="font-size:.83rem;padding:6px 13px">⬇️ DESCARGAR</a>
  </div>
</div>""" % (borde, p["producto_nombre"], bdg, ficha_sp, env_banner, caja,
             p["nombre_cliente"], p["direccion"], p["cantidad"],
             fmtp(float(p["total"])), p["fecha"], hora_sp,
             p["id"], p["id"])

    if peds is not None:
        result = '<div class="tr2"><h2 style="margin-bottom:14px;color:#E50914;font-family:\'Bebas Neue\',sans-serif;letter-spacing:2px">📋 TUS PEDIDOS — %s <span style="float:right;font-size:.87rem;color:#aaa;font-family:Montserrat,sans-serif">%d pedido(s)</span></h2>%s</div>' % (celular, len(peds), items) if peds else '<div class="al al-in" style="margin-top:16px;text-align:center">No se encontraron pedidos para <strong>%s</strong>.</div>' % celular
    else:
        result = ""

    return head("tracking", cfg) + """
<div class="con">
  <div class="hero">
    <h1>📦 SEGUIMIENTO DE PEDIDOS</h1>
    <p>Ingresa tu celular para ver el estado de tus pedidos</p>
  </div>
  <div class="pnl" style="max-width:500px;margin:0 auto">
    %s
    <form method="POST">
      <div class="fg"><label>Tu celular</label>
        <input type="text" name="celular" value="%s" placeholder="Ej: 3001234567" required></div>
      <button type="submit" class="btn btp btb">🔍 BUSCAR PEDIDOS</button>
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
    ln = ["="*44,"  RESTAURANTEAPP — NBA EDITION","="*44,
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
    ln += ["="*44,"  Gracias por tu pedido!","  NBA Edition 🏀","="*44]
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
  <div class="sc"><div class="nm" style="color:#e87c03">%d</div><div class="lb">⏳ Pendientes</div></div>
  <div class="sc"><div class="nm" style="color:#46d369">%d</div><div class="lb">✅ Confirmados</div></div>
  <div class="sc"><div class="nm" style="color:#bb86fc">%d</div><div class="lb">🚀 Enviados</div></div>
  <div class="sc"><div class="nm" style="color:#0071eb">%d</div><div class="lb">🔵 En Revision</div></div>
  <div class="sc"><div class="nm" style="color:#E50914">%d</div><div class="lb">❌ Cancelados</div></div>
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
    <div class="modal-title">🧾 ORDEN #%d</div>
    %s
    <button class="btn btp btb" style="margin-top:13px" onclick="printTicket('%s')">🖨️ IMPRIMIR</button>
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
    <div class="modal-title">✏️ EDITAR PEDIDO #%s</div>
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
               min="0" step="100" style="color:#E50914;font-weight:800"></div>
      <div class="fg"><label>Hora estimada</label>
        <input type="text" name="hora_estimada" value="%s"
               placeholder="Ej: 45 min / 6:30 PM"></div>
      <div class="fg"><label>Estado del pedido</label>
        <select name="estado">%s</select></div>
      <div style="background:rgba(98,0,234,.1);border:1px solid #6200ea;border-radius:6px;padding:10px;margin-bottom:14px;font-size:.82rem;color:#bb86fc">
        💡 Al marcar <strong>Enviado</strong> el pedido se movera al historial y el cliente vera que fue enviado.
      </div>
      <button type="submit" class="btn btp btb">💾 GUARDAR CAMBIOS</button>
    </form>
  </div>
</div>""" % (mid_ed, mid_ed, uid,
             uid, sub, sub,
             uid, envio,
             uid, sub,
             uid, sub+envio,
             p["hora_estimada"] or "",
             estado_opts)

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
    <div class="modal-title">🧾 ORDEN ENVIADA #%d</div>
    %s
    <button class="btn btp btb" style="margin-top:13px" onclick="printTicket('%s')">🖨️ IMPRIMIR</button>
  </div>
</div>""" % (mid_env, mid_env, p["id"], tk_html_env, mid_env)

        filas_env += """<tr style="opacity:.85">
  <td><strong>#%d</strong></td>
  <td><span class="ficha">%s</span></td>
  <td><strong>%s</strong></td>
  <td>%s</td>
  <td style="color:#E50914;font-weight:700">%s</td>
  <td style="font-size:.78rem;color:#aaa">%s</td>
  <td>
    <button class="btn btenv" style="font-size:.77rem;padding:5px 9px"
            onclick="openModal('%s')">🧾 VER</button>
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
    <div class="modal-title">✏️ EDITAR PRODUCTO</div>
    <form method="POST" action="/admin/edit-prod">
      <input type="hidden" name="producto_id" value="%d">
      <div class="fg"><label>Nombre</label>
        <input type="text" name="nombre" value="%s" required></div>
      <div class="fg"><label>Precio (₡)</label>
        <input type="number" name="precio" value="%g" required min="0" step="100"></div>
      <button type="submit" class="btn btp btb">💾 GUARDAR</button>
    </form>
  </div>
</div>""" % (mid_ep, mid_ep, p["id"], p["nombre"], p["precio"])

        filas_prod += """<tr>
  <td>%s</td>
  <td style="color:#E50914;font-weight:700">%s</td>
  <td style="display:flex;gap:6px;flex-wrap:wrap">
    <button class="btn btw" style="font-size:.8rem;padding:5px 9px"
            onclick="openModal('%s')">✏️ Editar</button>
    <a href="/admin/del-prod/%d"
       onclick="return confirm('Eliminar este producto?')"
       class="btn btd" style="font-size:.8rem;padding:5px 9px">🗑️ Borrar</a>
  </td>
</tr>""" % (p["nombre"], fmtp(p["precio"]), mid_ep, p["id"])

    graf_html = ('<div style="text-align:center"><img src="data:image/png;base64,%s" style="max-width:100%%;border-radius:var(--r)"></div>' % grafica) if grafica else '<p style="text-align:center;color:#aaa">Haz clic en Generar Grafica.</p>'

    tabla_ped = """<div class="pnl"><h2>📋 PEDIDOS ACTIVOS — en orden de llegada (%d)</h2>
<div class="tw"><table>
<thead><tr><th>#</th><th>Ficha</th><th>Nombre</th><th>Producto</th><th>Direccion Envio</th><th>Estado</th><th>Acciones</th></tr></thead>
<tbody>%s</tbody></table></div></div>""" % (
        len(peds_activos),
        filas_ped or '<tr><td colspan="7" style="text-align:center;color:#aaa;padding:20px">No hay pedidos activos.</td></tr>')

    tabla_env = """<div class="env-section"><h2>🚀 PEDIDOS ENVIADOS — Historial (%d)</h2>
<div class="tw"><table>
<thead><tr><th>#</th><th>Ficha</th><th>Nombre</th><th>Producto</th><th>Total</th><th>Fecha</th><th>Ver</th></tr></thead>
<tbody>%s</tbody></table></div></div>%s""" % (
        len(peds_enviados),
        filas_env or '<tr><td colspan="7" style="text-align:center;color:#bb86fc;padding:20px;opacity:.6">Sin pedidos enviados aun.</td></tr>',
        modales_env)

    tabla_prod = """<div class="ag">
<div class="pnl"><h2>➕ AGREGAR PRODUCTO</h2>
<form method="POST" action="/admin/add-prod" enctype="multipart/form-data">
  <div class="fg"><label>Nombre</label><input type="text" name="nombre" required placeholder="Nombre del producto"></div>
  <div class="fg"><label>Precio (₡)</label><input type="number" name="precio" required min="0" step="100" placeholder="12000"></div>
  <div class="fg"><label>Imagen (opcional)</label><input type="file" name="imagen" accept="image/*"></div>
  <button type="submit" class="btn bts btb">✅ AGREGAR</button>
</form></div>
<div class="pnl"><h2>📦 PRODUCTOS DEL MENÚ</h2>
<div class="tw"><table><thead><tr><th>Nombre</th><th>Precio</th><th>Acciones</th></tr></thead>
<tbody>%s</tbody></table></div></div></div>""" % (filas_prod or '<tr><td colspan="3" style="text-align:center;color:#aaa">No hay productos.</td></tr>')

    nombre_actual = cfg.get("nombre_sitio","RestauranteApp")
    logo_actual   = cfg.get("logo_sitio","")
    logo_preview  = ""
    if logo_actual:
        logo_preview = '<div style="margin-bottom:12px"><p style="font-size:.82rem;color:#aaa;margin-bottom:6px">Logo actual:</p><img src="data:image/jpeg;base64,%s" class="logo-prev"></div>' % logo_actual

    if session.get("master"):
        activo_ahora = cfg.get("sitio_activo","1") == "1"
        if activo_ahora:
            master_btn = '<a href="/admin/toggle-sitio" class="btn btd" style="font-size:1rem;padding:12px 28px" onclick="return confirm(&quot;Desactivar el sitio del cliente?&quot;)">&#128274; DESACTIVAR SITIO</a>'
            master_estado = '<span style="color:#46d369;font-weight:700">&#10003; ACTIVO</span>'
        else:
            master_btn = '<a href="/admin/toggle-sitio" class="btn bts" style="font-size:1rem;padding:12px 28px">&#10003; ACTIVAR SITIO</a>'
            master_estado = '<span style="color:#E50914;font-weight:700">&#128274; DESACTIVADO</span>'
        master_panel = """<div style="background:rgba(98,0,234,.12);border:2px solid #6200ea;border-radius:8px;padding:20px;margin-bottom:20px">
  <p style="color:#bb86fc;font-weight:800;font-size:1rem;margin-bottom:14px;font-family:'Bebas Neue',sans-serif;letter-spacing:2px">&#128273; PANEL MAESTRO &mdash; Estado del sitio: """ + master_estado + """</p>
  <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center">""" + master_btn + """
  <a href="/admin/reset-mes" class="btn" style="font-size:1rem;padding:12px 28px;background:linear-gradient(135deg,#E50914,#8B0000);color:#fff;border:2px solid #ff4444"
     onclick="return confirm('&#9888; RESETEAR MES\\n\\nEsto borrara TODOS los pedidos y estadisticas para empezar desde cero.\\n\\n¿Estas seguro?')">
     &#128465; RESETEAR MES
  </a>
  </div>
  <p style="color:#555;font-size:.75rem;margin-top:10px">⚠️ El boton RESETEAR MES borra todos los pedidos e ingresos del mes para empezar en cero.</p>
</div>"""
    else:
        if session.get("admin"):
            master_panel = """<div style="background:rgba(229,9,20,.12);border:2px solid #E50914;border-radius:8px;padding:20px;margin-bottom:20px">
  <p style="color:#E50914;font-weight:800;font-size:1rem;margin-bottom:14px;font-family:'Bebas Neue',sans-serif;letter-spacing:2px">&#128465; RESETEAR MES</p>
  <p style="color:#aaa;font-size:.85rem;margin-bottom:14px">Borra todos los pedidos e ingresos para empezar el mes desde cero.</p>
  <a href="/admin/reset-mes" class="btn" style="font-size:1rem;padding:12px 28px;background:#8B0000;color:#fff;border:2px solid #E50914"
     onclick="return confirm('Esto borrara TODOS los pedidos del mes. Seguro?')">
     &#128465; RESETEAR MES
  </a>
</div>"""
        else:
            master_panel = ""

    activo = cfg.get("sitio_activo","1") == "1"
    if activo:
        estado_sitio = '<div style="background:rgba(70,211,105,.12);border:1px solid #46d369;border-radius:6px;padding:13px;margin-bottom:16px;text-align:center"><span style="color:#46d369;font-weight:700;font-size:1rem">&#10003; SITIO ACTIVO &mdash; clientes pueden acceder</span></div>'
    else:
        estado_sitio = '<div style="background:rgba(229,9,20,.12);border:1px solid #E50914;border-radius:6px;padding:13px;margin-bottom:16px;text-align:center"><span style="color:#E50914;font-weight:700;font-size:1rem">&#128274; SITIO DESACTIVADO</span></div>'
    if session.get("master"):
        if activo:
            btn_toggle = '<a href="/admin/toggle-sitio" class="btn btd" style="width:100%;justify-content:center;margin-bottom:20px" onclick="return confirm(&quot;Desactivar el sitio?&quot;)">&#128274; DESACTIVAR SITIO</a>'
        else:
            btn_toggle = '<a href="/admin/toggle-sitio" class="btn bts" style="width:100%;justify-content:center;margin-bottom:20px">&#10003; ACTIVAR SITIO</a>'
    else:
        btn_toggle = ""

    tab_conf = '''<div style="background:#181818;border-radius:var(--r);padding:22px;border:2px solid var(--p);margin-bottom:20px">
  <h2 style="font-family:'Bebas Neue',sans-serif;font-size:1.4rem;letter-spacing:3px;margin-bottom:16px;color:var(--p);border-bottom:2px solid var(--p);padding-bottom:8px">🎨 MI RESTAURANTE</h2>''' + estado_sitio + btn_toggle + '''
  <hr style="border-color:#2a2a2a;margin-bottom:18px">
  <h3 style="color:var(--p);font-family:'Bebas Neue',sans-serif;letter-spacing:2px;font-size:1.1rem;margin-bottom:14px">PERSONALIZAR APARIENCIA</h3>
  <form method="POST" action="/admin/config-sitio" enctype="multipart/form-data">''' + logo_preview + '''
    <div class="fg"><label>Nombre del Restaurante</label>
      <input type="text" name="nombre_sitio" value="''' + nombre_actual + '''" required placeholder="Ej: Pizzeria Don Marco"></div>
    <div class="fg"><label>Logo / Foto del Restaurante</label>
      <input type="file" name="logo" accept="image/*"></div>
    <p style="font-size:.8rem;color:#aaa;margin-bottom:14px">💡 El nombre y logo aparecen en el navbar y en la bienvenida del inicio.</p>
    <button type="submit" class="btn bts btb">💾 GUARDAR CAMBIOS</button>
  </form>
</div>'''

    html  = head("admin", cfg)
    html += "<div class=\"con\">"
    html += "<div style=\"display:flex;justify-content:space-between;align-items:center;margin-bottom:20px\">"
    html += "<h1 style=\"font-family:'Bebas Neue',sans-serif;font-size:2.2rem;letter-spacing:4px;color:#fff\">&#9881;&#65039; PANEL DE ADMINISTRACIÓN</h1>"
    html += "<a href=\"/admin/logout\" class=\"btn btd\">&#128682; SALIR</a></div>"
    html += alerta(msg, tipo)
    html += banner_proceso(peds_activos)
    html += stats_html
    html += master_panel
    html += "<div style=\"display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap\">"
    html += "<button class=\"btn btp\" onclick=\"showTab('ped')\">&#128203; PEDIDOS ACTIVOS</button>"
    html += "<button class=\"btn btenv\" onclick=\"showTab('env')\">&#128640; ENVIADOS</button>"
    html += "<button class=\"btn btw\" onclick=\"showTab('prod')\">&#127828; PRODUCTOS</button>"
    html += "<button class=\"btn bts\" onclick=\"showTab('conf')\">&#127912; MI RESTAURANTE</button>"
    html += "<button class=\"btn bti\" onclick=\"showTab('stats')\">&#128202; ESTADÍSTICAS</button>"
    html += "</div>"
    html += "<div id=\"tab_ped\">" + tabla_ped + "</div>"
    html += "<div id=\"tab_env\" style=\"display:none\">" + tabla_env + "</div>"
    html += "<div id=\"tab_prod\" style=\"display:none\">" + tabla_prod + "</div>"
    html += "<div id=\"tab_conf\" style=\"display:none\">" + tab_conf + "</div>"
    html += "<div id=\"tab_stats\" style=\"display:none\"><div class=\"pnl\"><h2>📊 ESTADÍSTICAS</h2>"
    html += "<div style=\"text-align:center;margin-bottom:16px\">"
    html += "<a href=\"/admin/grafica\" class=\"btn btp\">&#128260; GENERAR GRÁFICA</a></div>"
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
        err = "❌ Contraseña incorrecta."
    return head("admin") + """
<div class="lb2">
  <h2>🔐 PANEL ADMIN</h2>
  <div style="text-align:center;margin-bottom:20px">
    <span style="font-family:'Bebas Neue',sans-serif;font-size:1rem;letter-spacing:4px;
      background:#1d428a;color:#fff;padding:4px 12px;border-radius:3px;border:2px solid #C8102E">
      🏀 NBA EDITION
    </span>
  </div>
  %s
  <form method="POST">
    <div class="fg"><label>Contraseña</label>
      <input type="password" name="password" placeholder="••••••••" required autofocus></div>
    <button type="submit" class="btn btp btb">INGRESAR</button>
  </form>
  <p style="text-align:center;margin-top:13px;color:#555;font-size:.82rem">Por defecto: <strong></strong></p>
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
    # Colores estilo Netflix
    cols  = ["#E50914","#B20710","#f5f5f1","#e87c03","#46d369","#0071eb","#bb86fc","#6200ea","#1d428a","#C8102E"][:len(noms)]
    fig, axes = plt.subplots(1,2,figsize=(14,6))
    fig.patch.set_facecolor("#141414")
    ax1 = axes[0]; ax1.set_facecolor("#1f1f1f")
    bars = ax1.bar(range(len(noms)),cants,color=cols,edgecolor="#333",linewidth=1.5)
    ax1.set_xticks(range(len(noms)))
    ax1.set_xticklabels([n[:16] for n in noms],rotation=28,ha="right",color="#eaeaea",fontsize=9)
    ax1.set_title("Unidades Vendidas",color="#E50914",fontsize=13,fontweight="bold",pad=12)
    ax1.set_ylabel("Unidades",color="#aaa"); ax1.tick_params(colors="#aaa")
    for sp in ax1.spines.values(): sp.set_color("#333")
    for b,v in zip(bars,cants):
        ax1.text(b.get_x()+b.get_width()/2,b.get_height()+.05,str(v),ha="center",color="#E50914",fontsize=10,fontweight="bold")
    ax2 = axes[1]; ax2.set_facecolor("#1f1f1f")
    wedges,texts,autotexts = ax2.pie(cants,colors=cols,autopct="%1.1f%%",startangle=90,pctdistance=.8,wedgeprops={"edgecolor":"#141414","linewidth":2})
    for t in texts: t.set_color("#eaeaea")
    for t in autotexts: t.set_color("white"); t.set_fontweight("bold")
    ax2.set_title("Distribucion",color="#E50914",fontsize=13,fontweight="bold",pad=12)
    patches = [mpatches.Patch(color=c,label=n[:18]) for c,n in zip(cols,noms)]
    ax2.legend(handles=patches,loc="lower center",bbox_to_anchor=(.5,-.15),ncol=2,fontsize=8,facecolor="#1f1f1f",edgecolor="#333",labelcolor="#eaeaea")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf,format="png",bbox_inches="tight",facecolor="#141414",dpi=120)
    buf.seek(0)
    g64 = base64.b64encode(buf.read()).decode()
    plt.close()
    db2 = get_db()
    peds2  = db2.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
    prods2 = db2.execute("SELECT * FROM productos ORDER BY id DESC").fetchall()
    db2.close()
    return render_admin_page(peds2, prods2, g64, "", "ok")


@app.route("/admin/reset-mes")
def reset_mes():
    if not session.get("master"): return redirect(url_for("admin_login"))
    db = get_db()
    total_peds = db.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    total_ingresos = db.execute("SELECT SUM(total) FROM pedidos WHERE estado != 'Cancelado'").fetchone()[0] or 0
    db.execute("DELETE FROM pedidos")
    db.commit()
    db.close()
    msg = "🗑️ Mes reseteado — Se borraron %d pedidos (₡ %s en ingresos). Empezando desde cero." % (total_peds, "{:,.0f}".format(total_ingresos))
    return redirect(url_for("admin", msg=msg, tipo="ok"))


@app.route("/reset-cliente1-2024")
def reset_cliente1():
    db = get_db()
    total_peds       = db.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    total_ingresos   = db.execute("SELECT SUM(total) FROM pedidos WHERE estado != 'Cancelado'").fetchone()[0] or 0
    total_enviados   = db.execute("SELECT COUNT(*) FROM pedidos WHERE estado='Enviado'").fetchone()[0]
    total_cancelados = db.execute("SELECT COUNT(*) FROM pedidos WHERE estado='Cancelado'").fetchone()[0]
    db.execute("DELETE FROM pedidos")
    db.commit()
    db.close()
    fecha    = datetime.now().strftime("%d/%m/%Y %H:%M")
    ingresos = "{:,.0f}".format(total_ingresos)
    html = (
        "<!DOCTYPE html><html lang='es'><head>"
        "<meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'>"
        "<title>Reset Cliente 1</title>"
        "<link href='https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Montserrat:wght@400;700&display=swap' rel='stylesheet'>"
        "<style>"
        "*{box-sizing:border-box;margin:0;padding:0}"
        "body{font-family:Montserrat,sans-serif;background:#141414;color:#eaeaea;"
        "min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}"
        ".box{background:#1f1f1f;border:2px solid #E50914;border-radius:10px;"
        "padding:40px;max-width:480px;width:100%;text-align:center;"
        "box-shadow:0 0 60px rgba(229,9,20,.2)}"
        ".icon{font-size:4rem;margin-bottom:16px}"
        "h1{font-family:'Bebas Neue',sans-serif;font-size:2rem;letter-spacing:3px;color:#E50914;margin-bottom:6px}"
        ".sub{color:#aaa;font-size:.85rem;margin-bottom:28px}"
        ".row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #2a2a2a;font-size:.95rem}"
        ".val{color:#E50914;font-weight:700}"
        ".total-row{display:flex;justify-content:space-between;padding:14px 0;font-size:1.1rem;font-weight:800}"
        ".verde{color:#46d369;font-size:1.2rem}"
        ".ok{background:rgba(70,211,105,.12);border:2px solid #46d369;border-radius:8px;"
        "padding:16px;margin-top:24px;color:#46d369;font-weight:700;font-size:1rem}"
        ".fecha{color:#555;font-size:.78rem;margin-top:16px}"
        ".badge{display:inline-block;background:#1d428a;color:#fff;"
        "font-family:'Bebas Neue',sans-serif;letter-spacing:3px;font-size:.9rem;"
        "padding:4px 14px;border-radius:4px;border:2px solid #C8102E;margin-bottom:20px}"
        "a{display:inline-block;margin-top:20px;background:#E50914;color:#fff;"
        "padding:10px 28px;border-radius:6px;text-decoration:none;font-weight:700;"
        "font-family:'Bebas Neue',sans-serif;letter-spacing:2px;font-size:1rem}"
        "</style></head><body>"
        "<div class='box'>"
        "<div class='icon'>🗑️</div>"
        "<div class='badge'>🏀 NBA — CLIENTE 1</div>"
        "<h1>MES RESETEADO</h1>"
        "<p class='sub'>Resumen del mes eliminado</p>"
        "<div class='row'><span>📦 Total pedidos borrados</span><span class='val'>" + str(total_peds) + "</span></div>"
        "<div class='row'><span>🚀 Enviados</span><span class='val'>" + str(total_enviados) + "</span></div>"
        "<div class='row'><span>❌ Cancelados</span><span class='val'>" + str(total_cancelados) + "</span></div>"
        "<div class='total-row'><span>💰 Ingresos del mes</span><span class='verde'>₡ " + ingresos + "</span></div>"
        "<div class='ok'>✅ Base de datos limpia — El dueño empieza el mes desde cero</div>"
        "<p class='fecha'>Reseteo realizado: " + fecha + "</p>"
        "<a href='/admin'>Ir al Panel Admin</a>"
        "</div></body></html>"
    )
    return html


if __name__ == "__main__":
    import os
    init_db()
    print("\n" + "="*48)
    print("  🏀  RestauranteApp NBA Edition!")
    print("="*48)
    print("  Cliente:  http://localhost:5000")
    print("  Admin:    http://localhost:5000/admin")
    print("="*48 + "\n")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
