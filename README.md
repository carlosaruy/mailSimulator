# Simulador SMTP Interactivo

Herramienta educativa para comprender en profundidad cómo funciona realmente el envío de correos electrónicos, con especial énfasis en la diferencia entre:

- **MUA → MSA** (cliente a servidor de correo propio): requiere autenticación formal con credenciales + TLS.
- **MTA → MTA** (servidor a servidor): **no usa autenticación con usuario/contraseña**. La confianza se basa en identidad (IP + reverse DNS + SPF + DKIM + DMARC).

## Características principales

- **Dos versiones incluidas**:
  - `simulacion_smtp.html`: Aplicación web de un solo archivo (HTML + CSS + JS embebido). Ideal para abrir directamente en el navegador.
  - `smtp_simulador.py`: Versión avanzada con **Streamlit** (recomendada). Permite marcar opciones en tiempo real y ver cómo cambia la conversación SMTP según las configuraciones.

- **Interactividad real** (en la versión Streamlit):
  - Checkboxes y selectores para activar/desactivar comportamientos:
    - Usar / no usar TLS (STARTTLS)
    - SPF pasa o falla
    - DKIM pasa o falla
    - Políticas DMARC (`p=none`, `p=quarantine`, `p=reject`)
    - **SPF-bypass + Spoof** (técnica realista): 
      - Conexión desde IP con reverse DNS válido (`mail.evil-reverso.com`)
      - Ese dominio autoriza la IP vía SPF
      - `MAIL FROM: atacante@mail.evil-reverso.com`
      - `RCPT TO: destino@cualquierdominio.com`
      - Pero en los headers del mensaje aparece como `From: "CEO" <ceo@empresa-legitima.com>`
  - La conversación (terminal) **cambia dinámicamente** según las opciones marcadas.
  - Se resalta la discrepancia entre el *envelope* (lo que lee el servidor) y los *headers* (lo que ve el usuario final).
  - Explicaciones educativas en cada paso.

- Incluye el escenario clásico de **SPF-bypass** usado por phishers cuando los dominios no tienen DMARC endurecido.

## Archivos del proyecto

| Archivo                      | Descripción |
|-----------------------------|-------------|
| `smtp_simulador.py`         | Simulador interactivo principal (Streamlit) |
| `simulacion_smtp.html`      | Versión single-file HTML (sin dependencias) |
| `especificacion_smtp_relay.md` | Especificación original del protocolo y flujos |
| `requirements.txt`          | Dependencias para la versión Python |
| `README.md`                 | Este archivo |

## Instalación y ejecución

### Versión recomendada (Streamlit)

```bash
# Clonar el repositorio
git clone https://github.com/carlosaruy/mailSimulator.git
cd mailSimulator

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
streamlit run smtp_simulador.py
```

Abre el navegador en la URL que muestre Streamlit.

### Versión HTML (sin instalar nada)

Simplemente abre el archivo `simulacion_smtp.html` en cualquier navegador.

## Objetivo educativo

Este proyecto busca que el usuario entienda que:

- Entre servidores de correo **no se autentican con credenciales**.
- La confianza se construye con:
  - IP de origen
  - Reverse DNS
  - Registros SPF (TXT)
  - Firmas DKIM
  - Políticas DMARC
- Técnicas como **SPF-bypass + spoof** explotan la diferencia entre lo que declara el envelope y lo que aparece en los headers del mensaje.
- Los grandes proveedores de correo suelen detectar estas discrepancias, pero no todos los servidores lo hacen.

## Estructura de los flujos simulados

### Escenario 1: MUA → MSA (Puerto 587)
- Requiere TLS obligatorio.
- Autenticación SASL (AUTH LOGIN) con credenciales en Base64.
- Solo después de establecer el túnel seguro se ofrece AUTH.

### Escenario 2: MTA → MTA (Puerto 25)
- No requiere (ni suele usar) AUTH con credenciales.
- STARTTLS es opcional (opportunistic).
- Validaciones basadas en:
  - IP + reverse DNS
  - SPF
  - DKIM (después de recibir el cuerpo)
  - DMARC (política del dominio del remitente)

## Licencia

Proyecto educativo de uso libre.

---

Desarrollado como herramienta de aprendizaje sobre protocolos de correo electrónico.