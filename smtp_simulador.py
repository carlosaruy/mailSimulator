#!/usr/bin/env python3
"""
Simulador Interactivo de SMTP - Cliente-Servidor y Servidor-Servidor
Versión dinámica con toggles/checkboxes.

Ejecutar:
    pip install streamlit
    streamlit run smtp_simulador.py
"""

import streamlit as st
from typing import List, Dict, Any

st.set_page_config(page_title="Simulador SMTP Interactivo", layout="wide", page_icon="📧")

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
    .note { color: #fbbf24; font-style: italic; }
    .box {
        border: 1px solid #444;
        border-radius: 12px;
        padding: 12px;
        background-color: #111;
        text-align: center;
    }
    .header {
        font-weight: 600;
        font-size: 1.1rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# ESTADO GLOBAL (session_state)
# ============================================
def init_state():
    if "s1_log" not in st.session_state:
        st.session_state.s1_log = []
        st.session_state.s1_phase = 0
        st.session_state.s1_config = {
            "tls_completed": True,
        }

    if "s2_log" not in st.session_state:
        st.session_state.s2_log = []
        st.session_state.s2_phase = 0
        st.session_state.s2_config = {
            "use_tls": True,
            "spf_pass": True,
            "dkim_pass": True,
            "dmarc_policy": "none",   # none | quarantine | reject
            "spf_bypass_spoof": False,
        }

init_state()

# ============================================
# LÓGICA DE DIÁLOGO - ESCENARIO 1 (MUA → MSA)
# ============================================
def get_s1_turn(phase: int, config: dict) -> Dict[str, Any]:
    """Devuelve las líneas para la fase actual según la config."""
    tls = config["tls_completed"]

    if phase == 0:
        return {
            "client": [],
            "server": ["220 smtp.ejemplo.com ESMTP Postfix"],
            "explanation": "El servidor acepta la conexión TCP en puerto 587.",
            "checks": []
        }
    elif phase == 1:
        return {
            "client": ["EHLO mi-computadora.local"],
            "server": ["250-smtp.ejemplo.com Hello...",
                       "250-STARTTLS" if tls else "250 8BITMIME",
                       "250 8BITMIME" if tls else ""],
            "explanation": "Cliente se presenta. El servidor ofrece STARTTLS solo si soporta TLS.",
            "checks": []
        }
    elif phase == 2:
        if tls:
            return {
                "client": ["STARTTLS"],
                "server": ["220 2.0.0 Ready to start TLS"],
                "explanation": "Se negocia TLS. A partir de ahora todo está cifrado.",
                "checks": ["tls"]
            }
        else:
            return {
                "client": ["[Sin STARTTLS - el cliente continúa sin cifrado]"],
                "server": ["[Servidor acepta continuar sin TLS]"],
                "explanation": "Sin TLS. Cualquier AUTH posterior sería inseguro (credenciales en claro).",
                "checks": []
            }
    elif phase == 3:
        # Segundo EHLO solo si hubo TLS
        if tls:
            lines = {
                "client": ["EHLO mi-computadora.local"],
                "server": ["250-smtp.ejemplo.com Hello...",
                           "250-AUTH PLAIN LOGIN",
                           "250 8BITMIME"],
                "explanation": "Después de TLS el servidor ofrece AUTH (solo es seguro ofrecerlo sobre TLS).",
                "checks": []
            }
        else:
            lines = {
                "client": ["EHLO mi-computadora.local"],
                "server": ["250-smtp.ejemplo.com Hello...",
                           "250 8BITMIME"],
                "explanation": "Sin TLS previo. El servidor no ofrece AUTH (buena práctica de seguridad).",
                "checks": []
            }
        return lines
    elif phase == 4:
        if tls:
            return {
                "client": ["AUTH LOGIN"],
                "server": ["334 VXNlcm5hbWU6"],
                "explanation": "Autenticación solo después de TLS.",
                "checks": ["auth"]
            }
        else:
            return {
                "client": ["AUTH LOGIN"],
                "server": ["535 5.7.0 Authentication rejected - TLS required"],
                "explanation": "El servidor rechaza AUTH porque no hay canal seguro.",
                "checks": []
            }
    elif phase == 5:
        if tls:
            return {
                "client": ["Y2FybG9zQGVqZW1wbG8uY29t   (carlos@ejemplo.com en Base64)"],
                "server": ["334 UGFzc3dvcmQ6"],
                "explanation": "Usuario enviado en Base64.",
                "checks": []
            }
        else:
            return {"client": [], "server": [], "explanation": "Flujo abortado por falta de TLS.", "checks": []}
    elif phase == 6:
        if tls:
            return {
                "client": ["bWlwYXNzd29yZDEyMw==   (mipassword123 en Base64)"],
                "server": ["235 2.7.0 Authentication successful"],
                "explanation": "Autenticación exitosa solo porque iba por TLS.",
                "checks": ["auth_ok"]
            }
        return {"client": [], "server": [], "explanation": "", "checks": []}
    elif phase == 7:
        return {
            "client": ["MAIL FROM:<carlos@ejemplo.com>"],
            "server": ["250 2.1.0 Ok"],
            "explanation": "Remitente aceptado.",
            "checks": []
        }
    elif phase == 8:
        return {
            "client": ["RCPT TO:<destino@cualquierdominio.com>"],
            "server": ["250 2.1.5 Ok"],
            "explanation": "Destinatario aceptado.",
            "checks": []
        }
    elif phase == 9:
        return {
            "client": ["DATA", "... (headers + cuerpo + . )"],
            "server": ["354 End data with <CR><LF>.<CR><LF>", "250 2.0.0 Ok: queued as 98765"],
            "explanation": "Mensaje entregado al MSA.",
            "checks": []
        }
    else:
        return {
            "client": ["QUIT"],
            "server": ["221 2.0.0 Bye"],
            "explanation": "Sesión cerrada.",
            "checks": []
        }

# ============================================
# LÓGICA DE DIÁLOGO - ESCENARIO 2 (MTA → MTA)
# ============================================
def get_s2_turn(phase: int, config: dict) -> Dict[str, Any]:
    use_tls = config["use_tls"]
    spf = config["spf_pass"]
    dkim = config["dkim_pass"]
    dmarc = config["dmarc_policy"]
    spoof = config["spf_bypass_spoof"]

    # === SPF-Bypass + Spoof realista ===
    attacker_ip = "203.0.113.45"
    reverse_domain = "mail.evil-reverso.com"

    if spoof:
        ehlo_name = reverse_domain
        mail_from = f"MAIL FROM: atacante@{reverse_domain}"
        from_header = 'From: "CEO" <ceo@empresa-legitima.com>'
        connection_note = f"Conexión desde IP {attacker_ip} (reverse DNS: {reverse_domain}). El dominio {reverse_domain} tiene SPF que autoriza esta IP."
    else:
        ehlo_name = "mail.origen.com"
        mail_from = "MAIL FROM: carlos@ejemplo.com"
        from_header = "From: carlos@ejemplo.com"
        connection_note = ""

    if phase == 0:
        explanation = "MTA destino acepta conexión en puerto 25."
        if spoof:
            explanation = f"{connection_note} El servidor ve una IP con reverse DNS válido y SPF autorizado para ese dominio."
        return {
            "client": [],
            "server": ["220 mail.destino.com ESMTP Postfix"],
            "explanation": explanation,
            "checks": ["ip"]
        }
    elif phase == 1:
        server_resp = [f"250-mail.destino.com Hello {ehlo_name}"]
        if use_tls:
            server_resp.append("250-STARTTLS")
        server_resp.append("250 8BITMIME")

        explanation = "Servidor se identifica. STARTTLS se ofrece solo si el modo lo permite."
        if spoof:
            explanation = f"EHLO usa el dominio del reverse DNS. La IP + reverse + SPF del dominio del atacante hacen que parezca legítimo."

        return {
            "client": [f"EHLO {ehlo_name}"],
            "server": server_resp,
            "explanation": explanation,
            "checks": ["ehlo", "mx"]
        }
    elif phase == 2:
        if use_tls:
            return {
                "client": ["STARTTLS"],
                "server": ["220 2.0.0 Ready to start TLS"],
                "explanation": "Se negocia TLS. Todo lo que sigue va cifrado.",
                "checks": ["tls"]
            }
        else:
            return {
                "client": ["[Sin STARTTLS - se continúa en texto claro]"],
                "server": ["[Continuando sin cifrado (común en puerto 25)]"],
                "explanation": "Sin TLS. El canal queda en texto claro (riesgo de interceptación).",
                "checks": ["no_tls"]
            }
    elif phase == 3:
        # Después de TLS (o directamente si no hay TLS) se hace MAIL FROM
        if use_tls:
            client_lines = [f"EHLO {ehlo_name}", mail_from]
        else:
            client_lines = [mail_from]

        server_lines = ["250 2.1.0 Ok"]
        if not spf:
            server_lines = ["550 5.7.1 SPF fail - IP not authorized"]

        explanation = "MAIL FROM. Aquí se evalúa SPF usando el dominio del envelope + IP + reverse DNS."
        if spoof:
            explanation = (
                f"MAIL FROM: {mail_from}. "
                f"SPF pasa porque el dominio {reverse_domain} autoriza explícitamente la IP {attacker_ip}. "
                "Sin embargo, esto es solo el 'envelope'. El contenido del mail puede mentir."
            )

        return {
            "client": client_lines,
            "server": server_lines,
            "explanation": explanation,
            "checks": ["spf"] if spf else []
        }
    elif phase == 4:
        if not spf and dmarc == "reject":
            return {
                "client": [],
                "server": ["550 5.7.1 Message rejected due to SPF+DMARC policy"],
                "explanation": "Rechazo temprano por SPF fail + DMARC p=reject.",
                "checks": []
            }

        return {
            "client": ["RCPT TO: destino@cualquierdominio.com"],
            "server": ["250 2.1.5 Ok"],
            "explanation": "Destinatario aceptado (es local del destino).",
            "checks": ["noauth"]
        }
    elif phase == 5:
        return {
            "client": ["DATA"],
            "server": ["354 End data with <CR><LF>.<CR><LF>"],
            "explanation": "Inicio de transferencia del mensaje.",
            "checks": []
        }
    elif phase == 6:
        # Contenido del mensaje
        body = [
            from_header,
            "To: destino@cualquierdominio.com",
            "Subject: Importante - Actualización de la empresa",
            "",
            "Estimado equipo,",
            "Por favor proceder con la transferencia urgente.",
            "",
            "Atentamente,",
            "CEO",
        ]
        if spoof:
            body.append("DKIM-Signature: (ausente o inválida para empresa-legitima.com)")
        else:
            body.append("DKIM-Signature: v=1; a=rsa-sha256; ... (firma válida)")

        body.append(".")

        server_resp = ["250 2.0.0 Ok: queued as 12345"]

        # Decisión final según DMARC + resultados
        if (not spf and not dkim):
            if dmarc == "reject":
                server_resp = ["550 5.7.1 Message rejected due to DMARC policy (p=reject)"]
            elif dmarc == "quarantine":
                server_resp = ["250 Ok: queued as 12345 (quarantined - DMARC p=quarantine)"]
            # si p=none sigue aceptado

        explanation = "Se envía el cuerpo completo. DKIM y DMARC se verifican sobre los headers + cuerpo."
        if spoof:
            explanation = (
                "¡Aquí está la discrepancia evidente! El 'envelope' (MAIL FROM + HELO + IP + SPF) es de atacante@mail.evil-reverso.com. "
                "Pero el 'From:' que ve el usuario es ceo@empresa-legitima.com. "
                "Servidores grandes detectan esta diferencia entre envelope y headers (DMARC alignment + otros chequeos). "
                "Algunos servidores más permisivos pueden no detectarlo y entregar el mail."
            )

        return {
            "client": body,
            "server": server_resp,
            "explanation": explanation,
            "checks": ["dkim", "dmarc"]
        }
    else:
        return {
            "client": ["QUIT"],
            "server": ["221 2.0.0 Bye"],
            "explanation": "Cierre de la sesión entre MTAs.",
            "checks": []
        }

# ============================================
# FUNCIONES DE AVANCE
# ============================================
def advance_s1():
    phase = st.session_state.s1_phase
    config = st.session_state.s1_config
    turn = get_s1_turn(phase, config)

    if turn["client"]:
        for line in turn["client"]:
            st.session_state.s1_log.append(("client", line))
    if turn["server"]:
        for line in turn["server"]:
            if line:  # evitar líneas vacías
                st.session_state.s1_log.append(("server", line))

    st.session_state.s1_phase += 1

def advance_s2():
    phase = st.session_state.s2_phase
    config = st.session_state.s2_config
    turn = get_s2_turn(phase, config)

    if turn["client"]:
        for line in turn["client"]:
            st.session_state.s2_log.append(("client", line))
    if turn["server"]:
        for line in turn["server"]:
            if line:
                st.session_state.s2_log.append(("server", line))

    st.session_state.s2_phase += 1

def reset_s1():
    st.session_state.s1_log = []
    st.session_state.s1_phase = 0

def reset_s2():
    st.session_state.s2_log = []
    st.session_state.s2_phase = 0

# ============================================
# UI - ENCABEZADO
# ============================================
st.title("📧 Simulador Interactivo de SMTP")
st.caption("Marca las opciones y avanza paso a paso. La conversación cambia según lo que marques.")

col1, col2 = st.columns(2)

# ============================================
# ESCENARIO 1 - MUA → MSA
# ============================================
with col1:
    st.subheader("Escenario 1: MUA → MSA (Puerto 587)")
    st.markdown("**Cliente de correo → Servidor de su empresa** (requiere autenticación real)")

    # Toggles para Escenario 1
    with st.container(border=True):
        st.markdown("**Opciones**")
        tls = st.checkbox("TLS completado (STARTTLS exitoso)", 
                          value=st.session_state.s1_config["tls_completed"],
                          key="s1_tls")
        st.session_state.s1_config["tls_completed"] = tls

        if not tls:
            st.warning("Sin TLS el servidor normalmente rechazará AUTH o no lo ofrecerá.")

    # Controles
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button("▶ Avanzar paso", key="s1_step", use_container_width=True):
            advance_s1()
    with c2:
        if st.button("Reiniciar", key="s1_reset", use_container_width=True):
            reset_s1()
    with c3:
        if st.button("Play (auto 5 pasos)", key="s1_play", use_container_width=True):
            for _ in range(5):
                advance_s1()

    # Terminal
    st.markdown("**Terminal SMTP**")
    if st.session_state.s1_log:
        terminal_html = ""
        for actor, line in st.session_state.s1_log:
            cls = "client" if actor == "client" else "server"
            prefix = "[CLIENTE] " if actor == "client" else "[SERVIDOR] "
            terminal_html += f'<span class="{cls}">{prefix}{line}</span><br>'
        st.markdown(f'<div class="terminal">{terminal_html}</div>', unsafe_allow_html=True)
    else:
        st.info("Haz clic en 'Avanzar paso' para comenzar.")

    # Explicación de la última acción
    if st.session_state.s1_phase > 0:
        last_turn = get_s1_turn(st.session_state.s1_phase - 1, st.session_state.s1_config)
        st.caption(last_turn.get("explanation", ""))

# ============================================
# ESCENARIO 2 - MTA → MTA
# ============================================
with col2:
    st.subheader("Escenario 2: MTA → MTA (Puerto 25)")
    st.markdown("**Servidor de origen → Servidor de destino** (sin autenticación con credenciales)")

    # Toggles para Escenario 2 - ESTO ES LO QUE EL USUARIO QUERÍA
    with st.container(border=True):
        st.markdown("**Opciones de verificación (marca y avanza)**")

        use_tls = st.checkbox("Usar TLS (STARTTLS)", 
                              value=st.session_state.s2_config["use_tls"], key="s2_tls")
        st.session_state.s2_config["use_tls"] = use_tls

        spf = st.checkbox("SPF pasa (IP autorizada para el dominio del MAIL FROM)", 
                          value=st.session_state.s2_config["spf_pass"], key="s2_spf")
        st.session_state.s2_config["spf_pass"] = spf

        dkim = st.checkbox("DKIM pasa (firma válida)", 
                           value=st.session_state.s2_config["dkim_pass"], key="s2_dkim")
        st.session_state.s2_config["dkim_pass"] = dkim

        dmarc = st.selectbox("Política DMARC", 
                             ["none", "quarantine", "reject"],
                             index=["none", "quarantine", "reject"].index(st.session_state.s2_config["dmarc_policy"]),
                             key="s2_dmarc")
        st.session_state.s2_config["dmarc_policy"] = dmarc

        spoof = st.checkbox("SPF-bypass + Spoof (MAIL FROM del atacante, From: header legítimo)", 
                            value=st.session_state.s2_config["spf_bypass_spoof"], key="s2_spoof")
        st.session_state.s2_config["spf_bypass_spoof"] = spoof

        if spoof:
            st.info(
                "La conexión viene de la IP **203.0.113.45**, cuyo **reverse DNS** es `mail.evil-reverso.com`. "
                "Ese dominio tiene SPF que autoriza explícitamente la IP. "
                "En la conversación aparecerá exactamente: **MAIL FROM: atacante@mail.evil-reverso.com** "
                "y **RCPT TO: destino@cualquierdominio.com** (estos son los valores del envelope que procesa el servidor de correo). "
                "Sin embargo, en los headers del mensaje (DATA) se identifica como `From: \"CEO\" <ceo@empresa-legitima.com>`. "
                "Servidores grandes suelen detectar la discrepancia entre envelope y headers (aunque no todos lo hacen)."
            )

        if not use_tls:
            st.warning("Sin TLS el canal queda en texto claro (común pero inseguro en puerto 25).")

    # Controles
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button("▶ Avanzar paso", key="s2_step", use_container_width=True):
            advance_s2()
    with c2:
        if st.button("Reiniciar", key="s2_reset", use_container_width=True):
            reset_s2()
    with c3:
        if st.button("Play (auto)", key="s2_play", use_container_width=True):
            for _ in range(6):
                advance_s2()

    # Terminal
    st.markdown("**Terminal SMTP**")
    if st.session_state.s2_log:
        terminal_html = ""
        for actor, line in st.session_state.s2_log:
            cls = "client" if actor == "client" else "server"
            prefix = "[MTA-ORIGEN] " if actor == "client" else "[MTA-DESTINO] "
            terminal_html += f'<span class="{cls}">{prefix}{line}</span><br>'
        st.markdown(f'<div class="terminal">{terminal_html}</div>', unsafe_allow_html=True)
    else:
        st.info("Marca las opciones de arriba y avanza. La conversación cambia según lo que marques.")

    # Explicación última
    if st.session_state.s2_phase > 0:
        last_turn = get_s2_turn(st.session_state.s2_phase - 1, st.session_state.s2_config)
        st.caption(last_turn.get("explanation", ""))

# ============================================
# DIAGRAMA SIMPLE (compartido)
# ============================================
st.divider()
st.subheader("Diagrama conceptual")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("""
    **MUA → MSA**
    ```
    [Cliente de correo]  ──(587 + TLS + AUTH)──▶  [Servidor de la empresa]
    ```
    Requiere credenciales reales + TLS obligatorio.
    """)

with col_b:
    st.markdown("""
    **MTA → MTA**
    ```
    [MTA Origen]  ──(25, opcional TLS)──▶  [MTA Destino]
                         │
                    SPF / DKIM / DMARC
                    (sin usuario/contraseña)
    ```
    Confianza basada en DNS + IP + reputación.
    """)

# ============================================
# LEYENDA EDUCATIVA
# ============================================
with st.expander("¿Por qué la conversación cambia según las opciones?"):
    st.markdown("""
    - **Sin TLS (MTA→MTA)**: En puerto 25 el STARTTLS es opcional. Si no se usa, todo viaja en claro.
    - **SPF falla**: El MAIL FROM no pasa la validación de la IP contra el registro SPF del dominio.
    - **DKIM falla**: La firma criptográfica del mensaje no valida.
    - **DMARC p=reject**: Si SPF y/o DKIM fallan (o no alinean), el servidor rechaza el mensaje.
    - **SPF-bypass + Spoof**: 
      - La conexión viene de una IP con **reverse DNS válido** (`mail.evil-reverso.com`).
      - Ese dominio tiene **SPF que autoriza la IP**.
      - En la terminal verás: **MAIL FROM: atacante@mail.evil-reverso.com**
      - y **RCPT TO: destino@cualquierdominio.com** (valores que el servidor lee del envelope).
      - Pero en los **headers del mail** (From:) se identifica como `CEO <ceo@empresa-legitima.com>`.
      - Servidores grandes suelen detectar la discrepancia entre el *envelope* y los *headers*. Algunos más permisivos pueden no hacerlo y entregar el correo.
    - **MUA-MSA**: La autenticación con credenciales **solo** se permite después de TLS. Sin TLS el servidor rechaza o no ofrece AUTH.
    """)

st.caption("Archivo único Python + Streamlit. Cambia las opciones en tiempo real y la conversación se adapta.")