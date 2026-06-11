#!/usr/bin/env python3
"""
Simulador Interactivo de SMTP - Cliente-Servidor (MUA->MSA) y Servidor-Servidor (MTA->MTA)

Arquitectura:
  - La conversacion completa se DERIVA de (config) en cada render (build_*_conversation).
  - El unico estado acumulado es el numero de "fase" visible por escenario.
  - Cambiar cualquier opcion reconstruye una conversacion siempre coherente.

Modelo de seguridad (escenario 2):
  - DMARC se evalua por ALIGNMENT: el dominio del header 'From:' debe coincidir con
    el dominio validado por SPF (envelope) y/o por DKIM (d=).
  - La politica DMARC la publica el dominio del 'From:' (en spoof, el dominio suplantado),
    no el receptor. Por eso un spoof entra o no segun lo que publique ese dominio.

Ejecutar:
    pip install streamlit
    streamlit run smtp_simulador.py
"""

import streamlit as st
from typing import List, Dict, Any

st.set_page_config(page_title="Simulador SMTP Interactivo", layout="wide", page_icon="@")

# ============================================
# ESTILOS
# ============================================
st.markdown("""
<style>
    .terminal {
        background-color: #0a0a0a;
        color: #ddd;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 13px;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #333;
        white-space: pre-wrap;
        line-height: 1.45;
    }
    .client { color: #60a5fa; }
    .server { color: #34d399; }
    .reject { color: #f87171; }
    .note   { color: #fbbf24; font-style: italic; }
</style>
""", unsafe_allow_html=True)

# ============================================
# ESTADO: solo la fase visible de cada escenario
# ============================================
if "s1_phase" not in st.session_state:
    st.session_state.s1_phase = 0
if "s2_phase" not in st.session_state:
    st.session_state.s2_phase = 0


# ============================================
# ESCENARIO 1 (MUA -> MSA, puerto 587)
# Devuelve la conversacion COMPLETA segun config.
# Cada turno: {"client": [str...], "server": [str...], "explanation": str}
# El color de error se infiere de codigos 4xx/5xx.
# ============================================
def build_s1_conversation(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    tls = cfg["tls_completed"]
    convo: List[Dict[str, Any]] = []

    convo.append({
        "client": [],
        "server": ["220 smtp.ejemplo.com ESMTP Postfix"],
        "explanation": "El servidor acepta la conexion TCP en el puerto 587 (submission) y envia su banner.",
    })

    if tls:
        convo.append({
            "client": ["EHLO mi-computadora.local"],
            "server": ["250-smtp.ejemplo.com Hello mi-computadora.local",
                       "250-STARTTLS",
                       "250 8BITMIME"],
            "explanation": "El cliente se presenta con EHLO. El servidor anuncia sus capacidades e incluye STARTTLS. "
                           "Todavia NO ofrece AUTH: seria inseguro anunciarlo antes de cifrar.",
        })
        convo.append({
            "client": ["STARTTLS"],
            "server": ["220 2.0.0 Ready to start TLS"],
            "explanation": "Se negocia TLS. A partir de aca todo el dialogo viaja cifrado.",
        })
        convo.append({
            "client": ["EHLO mi-computadora.local"],
            "server": ["250-smtp.ejemplo.com Hello mi-computadora.local",
                       "250-AUTH PLAIN LOGIN",
                       "250 8BITMIME"],
            "explanation": "Segundo EHLO, ya sobre el canal cifrado. Ahora si el servidor ofrece AUTH, "
                           "porque las credenciales viajaran protegidas por TLS.",
        })
        convo.append({
            "client": ["AUTH LOGIN"],
            "server": ["334 VXNlcm5hbWU6"],
            "explanation": "El cliente pide autenticarse con LOGIN. El servidor responde con el challenge "
                           "'Username:' codificado en Base64 (VXNlcm5hbWU6).",
        })
        convo.append({
            "client": ["Y2FybG9zQGVqZW1wbG8uY29t"],
            "server": ["334 UGFzc3dvcmQ6"],
            "explanation": "El cliente manda el usuario en Base64 (Y2FybG9zQGVqZW1wbG8uY29t = carlos@ejemplo.com). "
                           "Base64 NO es cifrado: solo es seguro porque ya hay TLS por debajo. El servidor pide la "
                           "contrasena ('Password:' = UGFzc3dvcmQ6).",
        })
        convo.append({
            "client": ["bWlwYXNzd29yZDEyMw=="],
            "server": ["235 2.7.0 Authentication successful"],
            "explanation": "Contrasena en Base64 (bWlwYXNzd29yZDEyMw== = mipassword123). El servidor la acepta. "
                           "Esto solo es seguro porque viaja dentro de TLS.",
        })
        convo.append({
            "client": ["MAIL FROM:<carlos@ejemplo.com>"],
            "server": ["250 2.1.0 Ok"],
            "explanation": "Remitente del envelope. El servidor lo acepta porque el usuario ya esta autenticado.",
        })
        convo.append({
            "client": ["RCPT TO:<destino@otrodominio.com>"],
            "server": ["250 2.1.5 Ok"],
            "explanation": "Destinatario. Como el cliente esta autenticado, el MSA acepta hacer relay hacia un dominio "
                           "externo: justamente su trabajo es sacar el correo de su usuario hacia afuera.",
        })
        convo.append({
            "client": ["DATA",
                       "From: carlos@ejemplo.com",
                       "To: destino@otrodominio.com",
                       "Subject: Hola",
                       "",
                       "Cuerpo del mensaje.",
                       "."],
            "server": ["354 End data with <CR><LF>.<CR><LF>",
                       "250 2.0.0 Ok: queued as 98765"],
            "explanation": "El cliente envia headers + cuerpo, terminados con una linea de un unico punto. "
                           "El MSA lo encola para entregarlo. Aca termina la tarea del cliente.",
        })
        convo.append({
            "client": ["QUIT"],
            "server": ["221 2.0.0 Bye"],
            "explanation": "Sesion cerrada correctamente.",
        })
    else:
        convo.append({
            "client": ["EHLO mi-computadora.local"],
            "server": ["250-smtp.ejemplo.com Hello mi-computadora.local",
                       "250 8BITMIME"],
            "explanation": "El cliente se presenta. Sin STARTTLS negociado, el servidor NO anuncia AUTH: "
                           "es la buena practica para no invitar a mandar credenciales en claro.",
        })
        convo.append({
            "client": ["AUTH LOGIN"],
            "server": ["530 5.7.0 Must issue a STARTTLS command first"],
            "explanation": "El cliente intenta autenticarse igual. El servidor lo rechaza con 530: exige STARTTLS "
                           "antes de cualquier AUTH. Sin canal cifrado no hay login. El flujo se corta aca.",
        })
        convo.append({
            "client": ["QUIT"],
            "server": ["221 2.0.0 Bye"],
            "explanation": "Sin poder autenticarse, la sesion se cierra.",
        })

    return convo


# ============================================
# ESCENARIO 2 (MTA -> MTA, puerto 25)
# ============================================
def build_s2_conversation(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    use_tls = cfg["use_tls"]
    spf_ok  = cfg["spf_pass"]
    dkim_ok = cfg["dkim_pass"]
    policy  = cfg["dmarc_policy"]        # none | quarantine | reject
    spoof   = cfg["spf_bypass_spoof"]

    attacker_ip = "203.0.113.45"

    if spoof:
        helo_name     = "mail.evil-reverso.com"
        env_domain    = "evil-reverso.com"          # dominio del envelope (MAIL FROM)
        mail_from     = "MAIL FROM:<atacante@mail.evil-reverso.com>"
        from_header   = 'From: "CEO" <ceo@empresa-legitima.com>'
        header_domain = "empresa-legitima.com"      # dominio del From: (el suplantado)
        spf_raw_pass  = True                         # el atacante publica SPF para su IP
        spf_aligned   = False                        # evil-reverso != empresa-legitima
        dkim_aligned  = False                        # no tiene la clave de empresa-legitima
        dkim_valid    = False
    else:
        helo_name     = "mail.origen.com"
        env_domain    = "ejemplo.com"
        mail_from     = "MAIL FROM:<carlos@ejemplo.com>"
        from_header   = "From: carlos@ejemplo.com"
        header_domain = "ejemplo.com"
        spf_raw_pass  = spf_ok
        spf_aligned   = spf_ok                        # mismo dominio en envelope y From:
        dkim_aligned  = dkim_ok
        dkim_valid    = dkim_ok

    dmarc_pass = spf_aligned or dkim_aligned

    convo: List[Dict[str, Any]] = []

    # 0 - conexion
    convo.append({
        "client": [],
        "server": ["220 mail.destino.com ESMTP Postfix"],
        "explanation": (f"El MTA destino acepta la conexion en el puerto 25 desde la IP {attacker_ip}."
                        if spoof else
                        "El MTA destino acepta la conexion TCP entrante en el puerto 25 y envia su banner."),
    })

    # 1 - EHLO
    server1 = [f"250-mail.destino.com Hello {helo_name} [{attacker_ip}]"
               if spoof else f"250-mail.destino.com Hello {helo_name}"]
    if use_tls:
        server1.append("250-STARTTLS")
    server1.append("250 8BITMIME")
    convo.append({
        "client": [f"EHLO {helo_name}"],
        "server": server1,
        "explanation": ("El MTA origen se identifica con el dominio del reverse DNS del atacante. La IP tiene PTR "
                        "valido, lo que ya esquiva filtros basicos de reputacion."
                        if spoof else
                        "El MTA origen se presenta. No hay login con usuario/contrasena entre MTAs: la confianza "
                        "se basa en IP, DNS (SPF/DKIM/DMARC) y reputacion."),
    })

    # 2 - TLS opcional (+ segundo EHLO)
    if use_tls:
        convo.append({
            "client": ["STARTTLS"],
            "server": ["220 2.0.0 Ready to start TLS"],
            "explanation": "Se negocia TLS oportunista. Cifra el TRANSPORTE, pero no autentica el CONTENIDO: "
                           "SPF/DKIM/DMARC son ortogonales a TLS.",
        })
        convo.append({
            "client": [f"EHLO {helo_name}"],
            "server": ["250-mail.destino.com Hello (sobre TLS)", "250 8BITMIME"],
            "explanation": "Segundo EHLO sobre el canal ya cifrado, como en cualquier sesion ESMTP con STARTTLS.",
        })

    # 3 - MAIL FROM + evaluacion SPF
    if spf_raw_pass:
        if spoof:
            mf_expl = (f"{mail_from}. SPF se evalua sobre el dominio del envelope ({env_domain}) y PASA: el atacante "
                       f"publico un SPF que autoriza su propia IP. Pero esto valida {env_domain}, NO "
                       f"empresa-legitima.com. SPF mira el envelope, no el From: que vera la victima.")
        else:
            mf_expl = (f"{mail_from}. SPF evalua la IP de origen contra el registro del dominio del envelope "
                       f"({env_domain}) y pasa.")
    else:
        mf_expl = (f"{mail_from}. SPF FALLA para {env_domain} (la IP no esta autorizada). Muchos MTAs no cortan "
                   "aca: registran el fallo y dejan que DMARC decida sobre el resultado final.")
    convo.append({
        "client": [mail_from],
        "server": ["250 2.1.0 Ok"],
        "explanation": mf_expl,
    })

    # 4 - RCPT TO
    convo.append({
        "client": ["RCPT TO:<destino@mail.destino.com>"],
        "server": ["250 2.1.5 Ok"],
        "explanation": "El destinatario pertenece a un dominio que ESTE MTA hospeda, asi que no es relay y lo acepta. "
                       "(Si fuera un dominio ajeno responderia 554 5.7.1 relay access denied.)",
    })

    # 5 - DATA inicio
    convo.append({
        "client": ["DATA"],
        "server": ["354 End data with <CR><LF>.<CR><LF>"],
        "explanation": "El servidor autoriza el envio del contenido (headers + cuerpo).",
    })

    # 6 - cuerpo + decision DMARC por alignment
    body = [
        from_header,
        "To: destino@mail.destino.com",
        "Subject: Actualizacion importante",
        "",
        "Estimado equipo, proceder con la transferencia.",
        "",
        ("CEO" if spoof else "Carlos"),
    ]
    if dkim_valid:
        body.append(f"DKIM-Signature: v=1; a=rsa-sha256; d={header_domain}; ... (firma valida)")
    elif spoof:
        body.append("(sin DKIM valido para empresa-legitima.com: el atacante no tiene su clave privada)")
    else:
        body.append("(sin firma DKIM)")
    body.append(".")

    aligned_by = []
    if spf_aligned:
        aligned_by.append("SPF")
    if dkim_aligned:
        aligned_by.append("DKIM")

    if dmarc_pass:
        server6 = ["250 2.0.0 Ok: queued as 12345"]
        why = f"DMARC PASA: {' y '.join(aligned_by)} alinea(n) con el From: ({header_domain})."
    else:
        if policy == "reject":
            server6 = [f"550 5.7.1 rejected: DMARC policy of {header_domain} is p=reject"]
            decision = "RECHAZADO"
        elif policy == "quarantine":
            server6 = [f"250 2.0.0 Ok: queued as 12345  (a SPAM por DMARC p=quarantine de {header_domain})"]
            decision = "A CUARENTENA (spam)"
        else:
            server6 = ["250 2.0.0 Ok: queued as 12345"]
            decision = "ACEPTADO pese al fallo"
        why = (f"DMARC NO alinea: ni SPF ni DKIM validan el dominio del From: ({header_domain}). "
               f"La politica publicada por {header_domain} es p={policy}  ->  {decision}.")

    if spoof:
        expl6 = (f"Aca estan el ataque y su defensa juntos. El envelope dice {env_domain} (y su SPF pasa), pero el "
                 f"From: que ve la persona dice {header_domain}. DMARC compara el From: contra lo validado por "
                 f"SPF/DKIM y no alinea. {why}  Leccion: el spoof se frena o no segun la politica que publique "
                 f"{header_domain}, NO segun si el receptor es 'grande'. Si {header_domain} no publica DMARC (o usa "
                 f"p=none), el correo entra igual.")
    else:
        expl6 = (f"Se evaluan DKIM y DMARC sobre headers + cuerpo. {why}  "
                 "(Notar que DKIM solo puede 'rescatar' un SPF fallido: con alignment de DKIM, DMARC pasa.)")

    convo.append({
        "client": body,
        "server": server6,
        "explanation": expl6,
    })

    # 7 - QUIT
    convo.append({
        "client": ["QUIT"],
        "server": ["221 2.0.0 Bye"],
        "explanation": "Cierre de la sesion entre MTAs.",
    })

    return convo


# ============================================
# RENDER GENERICO DE UN ESCENARIO
# ============================================
def is_error_line(line: str) -> bool:
    s = line.strip()
    return len(s) >= 3 and s[:3].isdigit() and s[0] in ("4", "5")


def render_terminal(convo: List[Dict[str, Any]], phase: int,
                    client_prefix: str, server_prefix: str) -> str:
    html = ""
    for turn in convo[:phase]:
        for line in turn["client"]:
            html += f'<span class="client">{client_prefix}{line}</span><br>'
        for line in turn["server"]:
            cls = "reject" if is_error_line(line) else "server"
            html += f'<span class="{cls}">{server_prefix}{line}</span><br>'
    return html


def scenario_block(key: str, convo: List[Dict[str, Any]],
                   client_prefix: str, server_prefix: str, auto_label: str):
    phase_key = f"{key}_phase"
    total = len(convo)
    # clamp por si la config nueva acorto la conversacion
    st.session_state[phase_key] = min(st.session_state[phase_key], total)
    phase = st.session_state[phase_key]

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Avanzar paso", key=f"{key}_step", use_container_width=True,
                     disabled=(phase >= total)):
            st.session_state[phase_key] = min(phase + 1, total)
            st.rerun()
    with c2:
        if st.button("Reiniciar", key=f"{key}_reset", use_container_width=True):
            st.session_state[phase_key] = 0
            st.rerun()
    with c3:
        if st.button(auto_label, key=f"{key}_play", use_container_width=True):
            st.session_state[phase_key] = total
            st.rerun()

    st.caption(f"Paso {phase} de {total}")

    st.markdown("**Terminal SMTP**")
    if phase > 0:
        html = render_terminal(convo, phase, client_prefix, server_prefix)
        st.markdown(f'<div class="terminal">{html}</div>', unsafe_allow_html=True)
    else:
        st.info("Toca 'Avanzar paso' para comenzar. La conversacion se adapta a las opciones de arriba.")

    if phase > 0:
        st.markdown(f"<span class='note'>{convo[phase-1]['explanation']}</span>",
                    unsafe_allow_html=True)


# ============================================
# UI
# ============================================
st.title("Simulador Interactivo de SMTP")
st.caption("Marca las opciones y avanza paso a paso. La conversacion se reconstruye entera segun lo que marques, "
           "asi que siempre es coherente.")

col1, col2 = st.columns(2)

# ---- ESCENARIO 1 ----
with col1:
    st.subheader("Escenario 1: MUA -> MSA (puerto 587)")
    st.markdown("**Cliente de correo -> servidor de su empresa** (requiere autenticacion real)")

    with st.container(border=True):
        st.markdown("**Opciones**")
        tls = st.checkbox("TLS completado (STARTTLS exitoso)", value=True, key="s1_tls")
        if not tls:
            st.warning("Sin TLS el servidor no ofrece AUTH y rechaza el login con 530.")

    s1_cfg = {"tls_completed": tls}
    s1_convo = build_s1_conversation(s1_cfg)
    scenario_block("s1", s1_convo, "[CLIENTE] ", "[SERVIDOR] ", "Completar todo")

# ---- ESCENARIO 2 ----
with col2:
    st.subheader("Escenario 2: MTA -> MTA (puerto 25)")
    st.markdown("**Servidor de origen -> servidor de destino** (sin credenciales; confianza por DNS/IP)")

    with st.container(border=True):
        st.markdown("**Opciones de verificacion**")
        use_tls = st.checkbox("Usar TLS (STARTTLS oportunista)", value=True, key="s2_tls")
        spf = st.checkbox("SPF pasa (IP autorizada para el dominio del envelope)", value=True, key="s2_spf")
        dkim = st.checkbox("DKIM pasa (firma valida)", value=True, key="s2_dkim")
        dmarc = st.selectbox("Politica DMARC publicada por el dominio del From:",
                             ["none", "quarantine", "reject"], index=0, key="s2_dmarc")
        spoof = st.checkbox("SPF-bypass + Spoof (envelope del atacante, From: header suplantado)",
                            value=False, key="s2_spoof")

        if spoof:
            st.info(
                "Conexion desde **203.0.113.45** con reverse DNS `mail.evil-reverso.com`, dominio cuyo SPF "
                "autoriza esa IP. El **envelope** sera `atacante@mail.evil-reverso.com` (SPF pasa), pero el "
                "**From: header** dira `CEO <ceo@empresa-legitima.com>`. Aca el selector DMARC representa la "
                "politica de **empresa-legitima.com** (el dominio suplantado): es lo que decide si el spoof entra."
            )
        if not use_tls:
            st.warning("Sin TLS el canal va en texto claro (comun en el puerto 25, pero interceptable).")
        if not spoof and not spf and not dkim and dmarc == "none":
            st.warning("SPF y DKIM fallan y DMARC=none: el correo entra igual. Es por que p=none no protege, "
                       "solo monitorea.")

    s2_cfg = {
        "use_tls": use_tls,
        "spf_pass": spf,
        "dkim_pass": dkim,
        "dmarc_policy": dmarc,
        "spf_bypass_spoof": spoof,
    }
    s2_convo = build_s2_conversation(s2_cfg)
    scenario_block("s2", s2_convo, "[MTA-ORIGEN] ", "[MTA-DESTINO] ", "Completar todo")

# ============================================
# DIAGRAMA CONCEPTUAL
# ============================================
st.divider()
st.subheader("Diagrama conceptual")
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("""
    **MUA -> MSA**
    ```
    [Cliente]  --(587 + TLS + AUTH)-->  [Servidor de la empresa]
    ```
    Credenciales reales + TLS obligatorio para autenticar.
    """)
with col_b:
    st.markdown("""
    **MTA -> MTA**
    ```
    [MTA Origen]  --(25, TLS opcional)-->  [MTA Destino]
                          |
                 SPF / DKIM / DMARC  (sin usuario/contrasena)
    ```
    Confianza por DNS + IP + reputacion. DMARC valida *alignment* del From:.
    """)

# ============================================
# LEYENDA
# ============================================
with st.expander("Por que la conversacion cambia (y quien decide cada cosa)"):
    st.markdown("""
- **SPF** valida la IP de origen contra el registro del dominio del **envelope** (MAIL FROM). Mira el sobre, no el From:.
- **DKIM** firma criptograficamente el mensaje con la clave del dominio `d=`. Sin la clave privada no se puede firmar.
- **DMARC** exige *alignment*: que el dominio del **From: header** coincida con el dominio validado por SPF y/o por DKIM.
  Si no alinea, se aplica la **politica que publica el dominio del From:** (`none` monitorea, `quarantine` manda a spam, `reject` rechaza).
- **Caso spoof**: el atacante pasa SPF con **su propio** dominio (`evil-reverso.com`), pero el From: dice `empresa-legitima.com`.
  Como no alinea, el correo se frena **solo si `empresa-legitima.com` publica DMARC con enforcement**. No depende de que el receptor sea "grande".
- **DKIM rescata a SPF**: si SPF falla pero DKIM alinea, DMARC pasa igual. Por eso DKIM con alignment es clave.
- **MUA->MSA**: la autenticacion con credenciales solo se ofrece/acepta sobre TLS. Sin TLS, el servidor responde 530.
    """)

st.caption("Archivo unico Python + Streamlit. La conversacion se deriva de las opciones, no se acumula.")
