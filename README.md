# 🍷 VinAI Sommelier - Asistente Virtual de Enoturismo 🤖

![Python](https://img.shields.io/badge/Python-3.10+-blueviolet?style=flat-square&logo=python)
![Rasa](https://img.shields.io/badge/Rasa-3.x-orange?style=flat-square&logo=rasa)
![Flask](https://img.shields.io/badge/Flask-2.x-black?style=flat-square&logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-8.x-blue?style=flat-square&logo=mysql)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-yellow?style=flat-square&logo=javascript)

👋 ¡Bienvenido al proyecto **VinAI Sommelier**!

**VinAI Sommelier** es un proyecto full-stack que implementa un chatbot de IA para actuar como un guía virtual de vinos y enoturismo. El sistema combina el poder de **Rasa** 🤖 para el procesamiento de lenguaje natural con un robusto backend de **Flask** ⚙️ y una base de datos **MySQL** 🗃️ para gestionar vinos, viñas y perfiles de usuario.

El proyecto incluye un panel de administración para la gestión de contenido, un sistema de autenticación de usuarios y una interfaz de chat web interactiva.

→ ¡Dale una ⭐️ a este repositorio si te gusta el proyecto!

## ✨ Características Principales

* **🧠 IA Conversacional (Rasa):**
    * **Recomendación de Vinos:** Recomienda vinos basándose en la cepa, tipo, maridaje o características, consultando la base de datos en tiempo real.
    * **Búsqueda de Tours:** Proporciona información detallada sobre tours en viñas específicas.
    * **Gestión de Formularios:** Maneja conversaciones complejas, como la valoración de un tour, pidiendo al usuario la viña, el puntaje y un comentario paso a paso.

* **👤 Sistema de Perfiles de Usuario:**
    * Registro e inicio de sesión de usuarios (con `Flask` y `JavaScript`).
    * Los usuarios pueden guardar sus preferencias de vino (ej. "guarda que me gusta el Carmenere").
    * El bot utiliza estas preferencias guardadas para personalizar futuras recomendaciones.
    * Los usuarios pueden ver sus preferencias y valoraciones guardadas en una página de perfil (`profile.html`).

* **⚙️ Panel de Administración (Flask):**
    * Dashboard que muestra estadísticas de uso, como las preferencias más populares y los tours mejor valorados.
    * Formularios para **añadir nuevos vinos** y **nuevas viñas** directamente a la base de datos `vinai_db_normalizada`.
    * Controles para **iniciar**, **detener** y **re-entrenar** los servidores de Rasa directamente desde la interfaz web.

## 🛠️ Stack Tecnológico

* **Chatbot (IA):** Rasa Open Source (`domain.yml`, `nlu.yml`, `rules.yml`).
* **Servidor de Acciones:** Rasa SDK (`actions.py`).
* **Backend & Servidor Web:** Flask (`admin_app.py`).
* **Base de Datos:** MySQL (el esquema está en `vinai_db_normalizada.sql`).
* **Frontend:** HTML5, CSS3, y JavaScript (Vanilla).
* **Librerías Clave de Python:** `mysql-connector-python`, `Flask-Login`, `Flask-Cors`.

## 🚀 Instalación y Ejecución

Para correr este proyecto localmente, necesitarás tener **Python 3.10+** y un servidor **MySQL** (como XAMPP, WAMP o MariaDB) instalados.
### 1. Configuración Inicial

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/TobbenTobb/VinAI.git
    cd TU_REPOSITORIO
    ```

2.  **Crea un entorno virtual y actívalo:**
    ```bash
    # Para Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```
3.  **Instala las dependencias de Python:**
    (Asegúrate de tener el archivo `requirements.txt`).
    ```bash
    pip install -r requirements.txt
    ```

### 2. Configuración de la Base de Datos

1.  **Inicia tu servidor MySQL.**
2.  Abre tu gestor de base de datos (como phpMyAdmin).
3.  Crea una nueva base de datos llamada `vinai_db_normalizada`.
4.  Importa el archivo `vinai_db_normalizada.sql` en esta nueva base de datos.
5.  **Importante:** Asegúrate de que la configuración `DB_CONFIG` en `actions.py` y `admin_app.py` coincida con tu usuario (`root`) y contraseña (actualmente `''`) de MySQL.

### 3. Entrenar el Modelo de Rasa

Antes de iniciar los servidores, debes entrenar el modelo de IA:
```bash
rasa train
```

### Terminales
Necesitarás abrir **4 terminales separadas** y mantenerlas todas corriendo.

---
### Terminal 1: Servidor Web (Frontend)
---
* **Propósito:** Sirve los archivos estáticos (index.html, bot.js, style.css).
* **Comando:**
    > python -m http.server 8000
* **Acceso:** Abre el chat en tu navegador en `http://localhost:8000/index.html`.

---
### Terminal 2: Servidor Backend (Flask Admin)
---
* **Propósito:** Ejecuta el panel de administración, perfiles y sistema de login.
* **Comando:**
    > python admin_app.py
* **Acceso:** Accede al panel de admin en `http://localhost:8080/login`.

---
### Terminal 3: Servidor de Acciones (Rasa Actions)
---
* **Propósito:** Es el "hacedor". Ejecuta la lógica personalizada (conectar a la BD, guardar valoraciones).
* **Comando:**
    > rasa run actions --debug

---
### Terminal 4: Servidor Central (Rasa Core)
---
* **Propósito:** Es el "cerebro". Procesa el lenguaje (NLU) y maneja la conversación.
* **Comando:**
    > rasa run --enable-api --cors "*" --debug

### HELP
Dentro del proyecto existe un txt llamado help por si algo Llegara a fallar
