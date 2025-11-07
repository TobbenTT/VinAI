from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import mysql.connector
import subprocess
import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta # Para la duración de la sesión

# Importar CORS para permitir peticiones entre puertos
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = 'cambia_esto_por_algo_muy_secreto_y_largo!'
# Configurar la duración de la sesión del usuario público
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Habilitar CORS, permitiendo credenciales (cookies) para la sesión
CORS(app, supports_credentials=True)

# --- Configuración de la DB ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'vinai_db_normalizada'
}

# --- Variables Globales para procesos del Bot ---
rasa_core_process = None
rasa_actions_process = None
project_path = os.path.dirname(os.path.abspath(__file__))

# --- Configuración de Flask-Login (Para Administradores) ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # La ruta @app.route('/login')
login_manager.login_message = u"Por favor, inicie sesión para acceder."
login_manager.login_message_category = "info"

# --- Modelo de Usuario (Para Administradores) ---
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username
    
    @staticmethod
    def get(user_id):
        conn = get_db_connection()
        user = None
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                # Busca en la tabla 'admins'
                cursor.execute("SELECT id, username FROM admins WHERE id = %s", (user_id,))
                user_data = cursor.fetchone()
                if user_data:
                    user = User(id=user_data['id'], username=user_data['username'])
                cursor.close()
                conn.close()
            except mysql.connector.Error as err:
                print(f"Error getting user by ID: {err}")
        return user

    @staticmethod
    def find_by_username(username):
        conn = get_db_connection()
        user = None
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                # Busca en la tabla 'admins'
                cursor.execute("SELECT id, username FROM admins WHERE username = %s", (username,))
                user_data = cursor.fetchone()
                if user_data:
                    user = User(id=user_data['id'], username=user_data['username'])
                cursor.close()
                conn.close()
            except mysql.connector.Error as err:
                print(f"Error finding user by username: {err}")
        return user

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# --- Conexión a DB ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error de base de datos: {err}")
        return None

# --- Rutas de Login/Logout (Para Administradores) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_panel'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user_data = None
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT id, username, password_hash FROM admins WHERE username = %s", (username,))
                user_data = cursor.fetchone()
                cursor.close()
                conn.close()
            except mysql.connector.Error as err:
                flash(f"Error de base de datos al buscar usuario: {err}", "error")
                return render_template('login.html')
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(id=user_data['id'], username=user_data['username'])
            login_user(user)
            flash("Inicio de sesión exitoso.", "success")
            return redirect(url_for('admin_panel'))
        else:
            flash("Usuario o contraseña incorrectos.", "error")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada exitosamente.", "success")
    return redirect(url_for('login'))

# ----------------------------------------------
# --- RUTAS DE ADMINISTRACIÓN (PROTEGIDAS) ---
# ----------------------------------------------

@app.route('/')
@login_required
def admin_panel():
    global rasa_core_process, rasa_actions_process
    core_status = "Detenido"
    actions_status = "Detenido"
    if rasa_core_process and rasa_core_process.poll() is None:
        core_status = "Corriendo"
    if rasa_actions_process and rasa_actions_process.poll() is None:
        actions_status = "Corriendo"
    return render_template('admin.html', core_status=core_status, actions_status=actions_status)

# --- Ruta para Añadir Vino ---
@app.route('/add_wine', methods=['POST'])
@login_required
def add_wine():
    nombre = request.form['nombre']
    cepa = request.form['cepa']
    ano = request.form['ano']
    tipo = request.form['tipo']
    vina_id = request.form['vina_id']
    link = request.form['link_compra']
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = "INSERT INTO vinos (nombre, cepa, ano, tipo, vina_id, link_compra) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(query, (nombre, cepa, ano, tipo, vina_id, link))
            conn.commit()
            cursor.close()
            conn.close()
            flash(f"¡Vino '{nombre}' añadido con éxito!", 'success')
        except mysql.connector.Error as err:
            flash(f"Error al añadir el vino: {err}", 'error')
    return redirect(url_for('admin_panel'))

# --- Ruta para Añadir Viña (con latitud y longitud) ---
@app.route('/add_vina', methods=['POST'])
@login_required
def add_vina():
    nombre = request.form['nombre']
    valle = request.form['valle']
    descripcion_tour = request.form['descripcion_tour']
    horario_tour = request.form['horario_tour']
    link_web = request.form['link_web']
    latitud = request.form.get('latitud')
    longitud = request.form.get('longitud')
    
    latitud = latitud if latitud else None
    longitud = longitud if longitud else None

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO vinas (nombre, valle, descripcion_tour, horario_tour, link_web, latitud, longitud) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (nombre, valle, descripcion_tour, horario_tour, link_web, latitud, longitud))
            conn.commit()
            cursor.close()
            conn.close()
            flash(f"¡Viña '{nombre}' añadida con éxito!", 'success')
        except mysql.connector.Error as err:
            flash(f"Error al añadir la viña: {err}", 'error')
    return redirect(url_for('admin_panel'))

# --- Rutas de Control del Bot ---
@app.route('/start_bot')
@login_required
def start_bot():
    global rasa_core_process, rasa_actions_process
    started_core = False
    started_actions = False

    try:
        if rasa_core_process is None or rasa_core_process.poll() is not None:
            rasa_core_process = subprocess.Popen(['rasa', 'run', '--enable-api'], cwd=project_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            flash("Iniciando servidor Rasa Core...", 'info')
            started_core = True
        else:
            flash("El servidor Rasa Core ya estaba corriendo.", 'info')

        if rasa_actions_process is None or rasa_actions_process.poll() is not None:
            rasa_actions_process = subprocess.Popen(['rasa', 'run', 'actions'], cwd=project_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            flash("Iniciando servidor de Acciones...", 'info')
            started_actions = True
        else:
            flash("El servidor de Acciones ya estaba corriendo.", 'info')

        if not started_core and not started_actions:
             flash("Ambos servidores ya estaban corriendo.", 'warning')

    except Exception as e:
        flash(f"Error al iniciar los servidores: {e}", 'error')
        rasa_core_process = None
        rasa_actions_process = None
        
    return redirect(url_for('admin_panel'))

@app.route('/stop_bot')
@login_required
def stop_bot():
    global rasa_core_process, rasa_actions_process
    stopped_core = False
    stopped_actions = False

    if rasa_core_process and rasa_core_process.poll() is None:
        try:
            rasa_core_process.terminate() 
            rasa_core_process.wait(timeout=5) 
        except subprocess.TimeoutExpired:
            rasa_core_process.kill() 
        rasa_core_process = None
        flash("Servidor Rasa Core detenido.", 'success')
        stopped_core = True
        
    if rasa_actions_process and rasa_actions_process.poll() is None:
        try:
            rasa_actions_process.terminate()
            rasa_actions_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            rasa_actions_process.kill()
        rasa_actions_process = None
        flash("Servidor de Acciones detenido.", 'success')
        stopped_actions = True

    if not stopped_core and not stopped_actions:
        flash("Los servidores ya estaban detenidos.", 'info')
        
    return redirect(url_for('admin_panel'))

@app.route('/rasa_train')
@login_required
def rasa_train():
    global rasa_core_process, rasa_actions_process
    core_running = rasa_core_process and rasa_core_process.poll() is None
    actions_running = rasa_actions_process and rasa_actions_process.poll() is None

    if core_running or actions_running:
        flash("¡Error! Debes detener los servidores del bot antes de re-entrenar.", 'error')
        return redirect(url_for('admin_panel'))
        
    try:
        flash("Iniciando re-entrenamiento... Esto puede tardar unos minutos.", 'info')
        completed_process = subprocess.run(
            ['rasa', 'train'], 
            cwd=project_path, 
            capture_output=True, 
            text=True,
            check=False 
        )
        
        if completed_process.returncode != 0:
             flash(f"Error durante el entrenamiento:\n{completed_process.stderr}", 'error')
        else:
            flash("¡Re-entrenamiento completado con éxito!", 'success')
            flash("Ahora puedes INICIAR los servidores para aplicar los cambios.", 'info')
            
    except Exception as e:
        flash(f"Error inesperado al ejecutar el entrenamiento: {e}", 'error')
        
    return redirect(url_for('admin_panel'))

# ----------------------------------------------
# --- RUTAS PÚBLICAS (Para el Modal de Usuario) ---
# ----------------------------------------------
@app.route('/public_register', methods=['POST'])
def public_register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password_plana = data.get('password')

    if not username or not email or not password_plana:
        return jsonify({"success": False, "message": "Faltan datos."}), 400

    password_hash = generate_password_hash(password_plana)
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Error de conexión a la base de datos."}), 500
        
    try:
        cursor = conn.cursor()
        query = "INSERT INTO usuarios (username, email, password_hash) VALUES (%s, %s, %s)"
        cursor.execute(query, (username, email, password_hash))
        conn.commit()
        return jsonify({"success": True, "message": "¡Registro exitoso! Ahora puedes iniciar sesión."})
        
    except mysql.connector.Error as err:
        if err.errno == 1062: # Error de Llave Duplicada
            return jsonify({"success": False, "message": "El email o usuario ya está registrado."}), 409
        else:
            return jsonify({"success": False, "message": f"Error de base de datos: {err}"}), 500
    finally:
        if conn: conn.close()

@app.route('/public_login', methods=['POST'])
def public_login():
    data = request.json
    email = data.get('email')
    password_plana = data.get('password')

    if not email or not password_plana:
        return jsonify({"success": False, "message": "Faltan datos."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Error de conexión a la base de datos."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, password_hash FROM usuarios WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password_hash'], password_plana):
            user_id_str = f"user_{user['id']}"
            
            # Guardar en la Sesión de Flask
            session.permanent = True 
            session['public_user_id'] = user['id']
            session['public_username'] = user['username']
            
            return jsonify({
                "success": True, 
                "message": f"¡Bienvenido, {user['username']}!",
                "user_id": user_id_str, # ID para el bot.js/Rasa
                "username": user['username'] # Nombre para mostrar en el frontend
            })
        else:
            return jsonify({"success": False, "message": "Email o contraseña incorrectos."}), 401
            
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Error de base de datos: {err}"}), 500
    finally:
        if conn: conn.close()

# --- Ruta para la Página de Perfil ---
@app.route('/profile')
def profile():
    # Verificar si el usuario está logueado (buscando en la sesión de Flask)
    if 'public_user_id' not in session:
        flash("Debes iniciar sesión para ver tu perfil.", "error")
        return redirect(url_for('login')) 

    user_id = session['public_user_id']
    username = session.get('public_username', 'Usuario')
    
    preferencias = []
    valoraciones = []
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Buscar sus preferencias guardadas
            query_prefs = "SELECT tipo_preferencia, valor_preferencia FROM preferencias_usuario WHERE usuario_id = %s"
            cursor.execute(query_prefs, (user_id,))
            preferencias = cursor.fetchall()
            
            # Buscar sus valoraciones de tours
            query_vals = """
                SELECT v.nombre as vina_nombre, vt.rating, vt.comentario
                FROM valoraciones_tour vt
                JOIN vinas v ON vt.vina_id = v.id
                WHERE vt.usuario_id = %s
                ORDER BY vt.fecha_valoracion DESC
            """
            cursor.execute(query_vals, (user_id,))
            valoraciones = cursor.fetchall()
            
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            flash(f"Error al cargar tu perfil: {err}", "error")
            
    # Enviar los datos al nuevo template 'profile.html'
    return render_template('profile.html', 
                           username=username, 
                           preferencias=preferencias, 
                           valoraciones=valoraciones)

# --- Ruta para Cerrar Sesión Pública ---
@app.route('/public_logout')
def public_logout():
    # Limpiar la sesión pública de Flask
    session.pop('public_user_id', None)
    session.pop('public_username', None)
    
    if request.referrer and '8000' in request.referrer:
        return jsonify({"success": True, "message": "Sesión cerrada"})
    else:
        flash("Sesión cerrada exitosamente.", "success")
        return redirect("http://localhost:8000/index.html")


# --- Iniciar el servidor del panel ---
if __name__ == '__main__':
    app.run(debug=True, port=8080)