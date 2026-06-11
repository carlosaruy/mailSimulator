# Simulación Interactiva de Protocolos SMTP: Cliente-Servidor y Servidor-Servidor

Este documento contiene la especificación detallada de los dos flujos principales del protocolo SMTP (Simple Mail Transfer Protocol) con extensiones ESMTP. 

**Objetivo principal de la aplicación:** Crear una herramienta **educativa** de un solo archivo HTML (con CSS y JS embebidos) cuyo foco sea que el usuario **comprenda realmente** cómo funciona el envío de correo electrónico, con énfasis especial en la diferencia fundamental entre:

- El envío desde un cliente (MUA) a su servidor de correo (MSA): donde **sí existe autenticación formal** (credenciales + TLS obligatorio).
- La retransmisión entre servidores de correo (MTA a MTA): donde **no existe autenticación interactiva** con usuario/contraseña. La confianza se establece mediante identidad declarada (EHLO), IP de origen, registros DNS (MX, SPF en TXT), firmas DKIM y reputación.

La claridad conceptual es mucho más importante que animaciones espectaculares de paquetes. Se prioriza una interfaz limpia, colorida y fácil de seguir que muestre claramente quién habla, qué se está verificando y por qué un servidor acepta o rechaza correo de otro servidor sin pedir contraseña.

---

## 1. Contexto y Arquitectura del Sistema

En el ciclo de vida de un correo electrónico intervienen tres componentes clave. La aplicación debe representar visualmente el flujo de datos pasando por estas entidades:

1. **MUA (Mail User Agent):** El cliente de correo (ej. Outlook, interfaz web, o un script).
2. **MSA (Mail Submission Agent):** El componente del servidor que recibe el correo inicial enviado por el cliente. Requiere autenticación forzosa (Puertos **587** o **465**).
3. **MTA (Mail Transfer Agent):** El software del servidor que se encarga de transferir el correo entre servidores intermediarios o hacia el destino final (Puerto **25**).

---

## 2. Escenario 1: Envío de Correo (MUA a MSA)
* **Propósito:** El cliente envía un correo a su propio servidor para que este lo procese.
* **Puerto típico:** 587 (SMTP + STARTTLS) o 465 (SMTPS).
* **Características clave:** Requiere negociación de cifrado obligatoria antes de transmitir datos y autenticación cifrada por SASL (Base64).

### Transcripción del Diálogo (Puerto 587)

| Actor | Comando / Respuesta SMTP | Descripción / Significado Técnico |
| :--- | :--- | :--- |
| **Servidor** | `220 smtp.ejemplo.com ESMTP Postfix` | El servidor acepta la conexión TCP y se presenta. |
| **Cliente** | `EHLO mi-computadora.local` | El cliente se identifica e inicia el saludo extendido. |
| **Servidor** | `250-smtp.ejemplo.com Hello...`<br>`250-STARTTLS`<br>`250 8BITMIME` | El servidor responde OK y expone sus capacidades (soporta TLS). |
| **Cliente** | `STARTTLS` | El cliente solicita iniciar una capa de conexión segura. |
| **Servidor** | `220 2.0.0 Ready to start TLS` | El servidor acepta. *(Aquí ocurre el Handshake TLS invisible).* |
| **Cliente** | `EHLO mi-computadora.local` | El cliente vuelve a saludar, ahora dentro del túnel cifrado. |
| **Servidor** | `250-smtp.ejemplo.com Hello...`<br>`250-AUTH PLAIN LOGIN`<br>`250 8BITMIME` | El servidor ahora sí ofrece `AUTH` (autenticación) porque ya es seguro. |
| **Cliente** | `AUTH LOGIN` | El cliente indica que usará el método de autenticación LOGIN. |
| **Servidor** | `334 VXNlcm5hbWU6` | Desafío del servidor (Texto en Base64 que significa `"Username:"`). |
| **Cliente** | `Y2FybG9zQGVqZW1wbG8uY29t` | Nombre de usuario enviado en Base64 (`carlos@ejemplo.com`). |
| **Servidor** | `334 UGFzc3dvcmQ6` | Desafío del servidor (Texto en Base64 que significa `"Password:"`). |
| **Cliente** | `bWlwYXNzd29yZDEyMw==` | Contraseña enviada en Base64 (`mipassword123`). |
| **Servidor** | `235 2.7.0 Authentication successful` | Autenticación aprobada. El cliente queda autorizado para someter (submit) correo a través de este MSA. |
| **Cliente** | `MAIL FROM:<carlos@ejemplo.com>` | Define la dirección del remitente del mensaje. |
| **Servidor** | `250 2.1.0 Ok` | Remitente aceptado. |
| **Cliente** | `RCPT TO:<destino@cualquierdominio.com>` | Define el destinatario externo del mensaje. |
| **Servidor** | `250 2.1.5 Ok` | Destinatario aceptado en la cola. |
| **Cliente** | `DATA` | El cliente solicita comenzar el envío del contenido del correo. |
| **Servidor** | `354 End data with <CR><LF>.<CR><LF>` | Indica que está listo. Terminar el bloque con un punto `.` solo. |
| **Cliente** | *(Encabezados y Cuerpo del Mensaje)* | Envía `From:`, `To:`, `Subject:`, el texto y un punto final `.` |
| **Servidor** | `250 2.0.0 Ok: queued as 98765` | Mensaje recibido con éxito y puesto en la cola de salida (`mailq`). |
| **Cliente** | `QUIT` | El cliente cierra la sesión. |

---

## 3. Intermedio: Procesamiento Interno del Servidor y Resolución DNS (crítico para entender el Escenario 2)

1. El **MSA** recibe el correo y lo encola internamente para que lo procese el **MTA** de salida del mismo servidor (esto suele ser una operación local, sin tráfico de red).
2. El **MTA de origen** examina el dominio del destinatario (`@cualquierdominio.com`).
3. Realiza consultas DNS reales (o simuladas en la UI):
   - Registro **MX** para saber a qué servidor(s) debe entregar el correo.
   - Registro **TXT** de tipo SPF para verificar si la IP del MTA de origen está autorizada a enviar correo en nombre del dominio del remitente.
4. Solo después de estas resoluciones, el MTA de origen abre una conexión TCP al puerto 25 del MTA de destino (usando la IP obtenida vía MX).

**Importante para la simulación:** Este paso intermedio (especialmente las consultas DNS) debe ser **visible y claro** en la interfaz, porque es la base de la confianza entre servidores que no se autentican con credenciales.

---

## 4. Escenario 2: Retransmisión entre Servidores (MTA a MTA / Relay)
* **Propósito:** El servidor de origen entrega el mensaje al servidor del destinatario final.
* **Puerto típico:** 25 (SMTP estándar entre servidores).
* **Características clave:** No requiere contraseñas (autenticación interactiva). La confianza se basa en validaciones DNS de identidad (SPF, DKIM, DMARC) y en la reputación de la IP. El servidor destino sólo acepta el correo si el destinatario es un usuario local de sus propios dominios gestionados.

### Transcripción del Diálogo (Puerto 25)

| Actor | Comando / Respuesta SMTP | Descripción / Significado Técnico |
| :--- | :--- | :--- |
| **MTA Destino** | `220 mail.destino.com ESMTP Postfix` | El servidor remoto acepta la conexión en puerto 25 y se presenta. |
| **MTA Origen** | `EHLO mail.origen.com` | El servidor de origen se identifica usando su FQDN. |
| **MTA Destino** | `250-mail.destino.com Hello...`<br>`250-STARTTLS`<br>`250 8BITMIME` | Responde OK y ofrece capacidades de cifrado opcionales. |
| **MTA Origen** | `STARTTLS` | El origen solicita cifrar el canal de transferencia. |
| **MTA Destino** | `220 2.0.0 Ready to start TLS` | Se negocia la capa TLS de forma transparente. |
| **MTA Origen** | `EHLO mail.origen.com` | Se repite el saludo bajo la capa segura. |
| **MTA Destino** | `250-mail.destino.com Hello...`<br>`250 8BITMIME` | Confirmación final de capacidades disponibles. |
| **MTA Origen** | `MAIL FROM:<carlos@ejemplo.com>` | Identifica el origen real del mensaje. |
| **MTA Destino** | `250 2.1.0 Ok` | Remitente aceptado. *(Aquí el destino suele evaluar políticas SPF).* |
| **MTA Origen** | `RCPT TO:<destino@cualquierdominio.com>` | Identifica al destinatario final del mensaje. |
| **MTA Destino** | `250 2.1.5 Ok` | El destino acepta porque `@cualquierdominio.com` es un dominio propio. |
| **MTA Origen** | `DATA` | El origen solicita iniciar la transferencia física del paquete. |
| **MTA Destino** | `354 End data with <CR><LF>.<CR><LF>` | Servidor remoto listo para recibir el flujo de bytes. |
| **MTA Origen** | *(Contenido completo del Mail)* | Envía los datos del mail firmados con DKIM, terminando con un punto `.` |
| **MTA Destino** | `250 2.0.0 Ok: queued as 12345` | Aceptado y encolado para su entrega en el buzón local (MDA/IMAP). |
| **MTA Origen** | `QUIT` | Cierre formal de la transferencia. |

---

## 5. Requerimientos de la aplicación web (single-file HTML + CSS + JS)

El objetivo **no es** una animación cinematográfica de paquetes viajando por la red. El objetivo es **que se entienda** el protocolo y, sobre todo, el modelo de confianza completamente distinto que se usa entre servidores.

### 5.1 Estructura general de la interfaz

- Dos secciones principales claramente diferenciadas (pueden ser pestañas o bloques uno debajo del otro con buen espaciado):
  - **Escenario 1: MUA → MSA** (Cliente a su servidor de correo) — Puerto 587.
  - **Escenario 2: MTA → MTA** (Servidor de correo a servidor de correo) — Puerto 25.
- Cada escenario tiene:
  - Un diagrama simple con **2 cajas principales** (y una tercera opcional para DNS en el escenario 2).
  - Una línea de conexión entre las cajas.
  - Una terminal / log de comandos con **colores diferenciados** por actor.
  - Controles de reproducción (Paso a paso, Play/Pausa, Reiniciar, quizás velocidad).
  - Elementos explicativos adicionales (ver más abajo).

**Estilo de las cajas recomendadas (simple y claro):**
- Escenario 1: Caja izquierda = "Cliente de correo (MUA)" | Caja derecha = "Servidor de correo - MSA (smtp.ejemplo.com)"
- Escenario 2: Caja izquierda = "MTA Origen (mail.origen.com)" | Caja derecha = "MTA Destino (mail.destino.com)" + una caja o icono pequeño de "DNS / Registros públicos" (MX + SPF TXT).

### 5.2 Animación / Indicación visual de flujo (mantenerlo simple)

- Usar una **flecha o línea de conexión** entre las dos cajas principales.
- Cuando ocurre un comando o respuesta:
  - Resaltar temporalmente la línea de conexión (cambio de color o grosor).
  - Opcionalmente: una pequeña flechita, chevron o círculo que se desplace a lo largo de la línea en la dirección correcta (cliente → servidor o servidor → cliente). 
  - **No es necesario** animar "paquetes con texto" complejos ni trayectorias curvas elaboradas. Una indicación clara de "ahora viaja información en esta dirección" es suficiente y mucho más fácil de mantener sincronizada.
- La sincronización se logra fácilmente porque **el stepper avanza paso a paso** y en cada paso se actualiza simultáneamente:
  1. Se agregan las líneas al terminal.
  2. Se resalta la flecha/línea en la dirección correcta.
  3. Se activan los efectos laterales (ver 5.3 y 5.4).

### 5.3 Terminal / Conversación con colores diferenciados (importante)

- Cada línea del diálogo debe tener color según quién la emite:
  - **Azul / índigo** para todo lo que envía el lado izquierdo (MUA o MTA Origen).
  - **Verde / esmeralda** para todo lo que responde el lado derecho (MSA o MTA Destino).
- Usar un prefijo claro en cada línea del log, por ejemplo:
  - `[CLIENTE]` o `[MTA-ORIGEN]` en azul
  - `[SERVIDOR]` o `[MTA-DESTINO]` en verde
- Esto ayuda muchísimo a seguir quién está hablando en cada momento sin tener que leer los roles de la tabla.

### 5.4 Elementos pedagógicos OBLIGATORIOS (especialmente para el Escenario 2)

Este es el punto más importante de la aplicación.

**En el Escenario 1 (MUA→MSA):**
- Mantener el **traductor de Base64** (panel flotante o lateral que aparece en los pasos de `AUTH LOGIN`). Debe mostrar claramente:
  - `334 VXNlcm5hbWU6` → decodificado "Username:"
  - El valor enviado por el cliente decodificado.
- Indicar visualmente que la autenticación es **formal** (credenciales + TLS). Un candado grande o badge "Autenticación SASL requerida" que se active después del STARTTLS.

**En el Escenario 2 (MTA→MTA) — el que más hay que explicar bien:**
Agregar un panel lateral o sección inferior llamada **"¿Cómo confía el servidor destino sin pedir usuario/contraseña?"** o **"Verificaciones de identidad (sin autenticación formal)"**.

Este panel debe ir revelando / activando checks a medida que avanza el diálogo:

1. **Conexión entrante** (al recibir el 220 inicial):
   - Muestra la IP real de la conexión (simulada, ej: 203.0.113.45)
   - Muestra el nombre que declara el otro servidor vía EHLO (`mail.origen.com`)

2. **Verificación de identidad vía DNS** (después del EHLO post-TLS o en el paso intermedio):
   - Simular / mostrar consulta MX para `cualquierdominio.com` → resultado `mail.destino.com`
   - (Opcional pero muy valioso) Simular consulta de registro **SPF TXT** para el dominio del MAIL FROM (`ejemplo.com`).
     - Mostrar algo como: `ejemplo.com. TXT "v=spf1 ip4:203.0.113.0/24 include:_spf.ejemplo.com -all"`
     - Indicar si la IP del MTA Origen "pasa" o no el chequeo SPF.

3. **Después de MAIL FROM**:
   - Activar explícitamente la nota de SPF (ya está en el diálogo, pero la UI debe resaltarla).
   - Mostrar que el servidor destino **no pidió credenciales** en ningún momento.

4. **Después de DATA (o al final)**:
   - Mencionar brevemente que DKIM (firma criptográfica dentro de los headers del mensaje) y DMARC también se evalúan, pero que la decisión de aceptar el RCPT TO ya se tomó antes de recibir el cuerpo.

El mensaje conceptual clave que debe quedar clarísimo:
> "A diferencia del cliente que se autenticó con usuario y contraseña en el Escenario 1, aquí los dos servidores **no se autentican** con credenciales. El servidor de destino decide aceptar el correo basándose en que la IP + el nombre declarado + los registros DNS públicos (SPF principalmente) demuestran que este servidor está autorizado a enviar correo del dominio del remitente."

### 5.5 Otros requisitos de usabilidad

- Controles claros de reproducción + posibilidad de saltar a cualquier paso.
- En cada paso importante, un pequeño texto explicativo corto (tooltip o cajita debajo del terminal) que diga "por qué pasa esto" o "qué está verificando el servidor ahora".
- Botón o sección "Por qué es diferente este escenario" que compare lado a lado los dos flujos (autenticación con credenciales vs. verificación de identidad vía DNS/IP/reputación).
- Diseño limpio, legible, con buena tipografía para el terminal (fuente monoespaciada).
- Totalmente autocontenido: un solo archivo .html que funcione abriéndolo localmente.

### 5.6 Sincronización (ahora mucho más simple de lograr)

Dado que se simplificó la parte visual, la sincronización entre terminal y diagrama se logra con un array de pasos en JavaScript. Cada paso contiene:
- Las líneas exactas a agregar al terminal (con su color/clase).
- La acción visual en el diagrama (resaltar conexión + dirección).
- Qué checks del panel de "Verificación de identidad" activar.
- Qué explicaciones laterales mostrar.

Esto garantiza que nunca se desincronicen.
