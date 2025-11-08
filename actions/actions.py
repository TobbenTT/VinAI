import re
from typing import Any, Text, Dict, List, Optional
import logging
from rasa_sdk.forms import FormValidationAction
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configuración de la Base de Datos ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'vinai_db_normalizada'
}

# --- Configuración de Mapas ---
GOOGLE_MAPS_API_KEY = "PEGA_TU_GOOGLE_MAPS_API_KEY_AQUÍ"
VALLEY_MAPS = {
    "Valle del Maipo": "https://i.imgur.com/g8iY8fD.png",
    "Valle de Colchagua": "https://i.imgur.com/R3Zf1jX.png",
    "Valle de Casablanca": "https://i.imgur.com/0iYfH2e.png",
    "Valle de Aconcagua": "https://i.imgur.com/O6wZJ1B.png",
}

def _get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# --- Carga Dinámica de Palabras Clave ---
def _load_gazettes_from_db() -> Dict[str, List[str]]:
    gazettes = {
        "notas_sabor": [],
        "maridajes": [],
        "caracteristicas": [],
        "vinas": []
    }
    
    conn = None
    try:
        print("Cargando palabras clave (gazettes) desde la base de datos...")
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT nombre FROM notas_sabor")
        for row in cursor.fetchall():
            gazettes["notas_sabor"].append(row[0].lower())
            
        cursor.execute("SELECT nombre FROM maridajes")
        for row in cursor.fetchall():
            gazettes["maridajes"].append(row[0].lower())

        cursor.execute("SELECT nombre FROM caracteristicas")
        for row in cursor.fetchall():
            gazettes["caracteristicas"].append(row[0].lower())

        cursor.execute("SELECT nombre FROM vinas")
        for row in cursor.fetchall():
            gazettes["vinas"].append(row[0].lower())
            
        cursor.close()
        print(f"Carga exitosa: {len(gazettes['notas_sabor'])} sabores, {len(gazettes['maridajes'])} maridajes, {len(gazettes['caracteristicas'])} características, {len(gazettes['vinas'])} viñas.")
        
    except mysql.connector.Error as err:
        print(f"Error al cargar gazettes desde DB: {err}")
    finally:
        if conn: conn.close()

    return gazettes

GAZETTE = _load_gazettes_from_db()

# === ACCIONES DE PERFIL Y LOGIN ===
class ActionRegistrarUsuario(Action):
    def name(self) -> Text: return "action_registrar_usuario"
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # ... (Tu código de registro va aquí, no necesita cambios) ...
        email = next(tracker.get_latest_entity_values("email"), None)
        password_plana = "12345" 
        if not email:
            dispatcher.utter_message(text="Para registrarte, por favor di 'quiero registrarme con miemail@ejemplo.com'")
            return []
        password_hash = generate_password_hash(password_plana)
        username = email.split('@')[0] 
        conn = _get_db_connection()
        try:
            cursor = conn.cursor()
            query = "INSERT INTO usuarios (username, email, password_hash) VALUES (%s, %s, %s)"
            cursor.execute(query, (username, email, password_hash))
            conn.commit()
            dispatcher.utter_message(text=f"¡Registro exitoso! Tu cuenta para '{email}' ha sido creada. Ahora puedes iniciar sesión.")
        except mysql.connector.Error as err:
            if err.errno == 1062: 
                dispatcher.utter_message(text="Ese email ya está registrado. ¿Quieres 'iniciar sesión'?")
            else:
                print(f"Error en ActionRegistrarUsuario: {err}")
                dispatcher.utter_message(text="Tuvimos un problema al intentar registrar tu cuenta.")
        finally:
            if conn: conn.close()
        return []

class ActionIniciarSesion(Action):
    def name(self) -> Text: return "action_iniciar_sesion"
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # ... (Tu código de login va aquí, no necesita cambios) ...
        email = next(tracker.get_latest_entity_values("email"), None)
        if not email:
            dispatcher.utter_message(text="No detecté un email. Por favor, di 'quiero iniciar sesión con miemail@ejemplo.com'")
            return []
        conn = _get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, username, password_hash FROM usuarios WHERE email = %s", (email,))
            user = cursor.fetchone()
            if user:
                user_id_str = f"user_{user['id']}" 
                custom_payload = {"user_id": user_id_str} 
                dispatcher.utter_message(text=f"¡Hola de nuevo, {user['username']}! Sesión iniciada.", json_message=custom_payload)
                return [SlotSet("slot_user_id", user_id_str)]
            else:
                dispatcher.utter_message(text=f"No encontramos una cuenta con ese email. ¿Quieres 'registrarte'?")
                return []
        except mysql.connector.Error as err:
            print(f"Error en ActionIniciarSesion: {err}")
            dispatcher.utter_message(text="Tuvimos un problema al intentar iniciar sesión.")
        finally:
            if conn: conn.close()
        return []

class ActionGuardarPreferencia(Action):
    def name(self) -> Text: return "action_guardar_preferencia"
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # ... (Tu código de guardar preferencia va aquí, no necesita cambios) ...
        user_id_str = tracker.sender_id
        if not user_id_str or not user_id_str.startswith("user_"):
            dispatcher.utter_message(text="Debes 'iniciar sesión' para poder guardar tus gustos.")
            return []
        try:
            usuario_id = int(user_id_str.split("_")[1])
        except (IndexError, ValueError):
            dispatcher.utter_message(text="Hubo un problema al identificar tu sesión. Intenta 'iniciar sesión' de nuevo.")
            return []
        cepa = next(tracker.get_latest_entity_values("cepa"), None)
        valle = next(tracker.get_latest_entity_values("valle"), None)
        tipo_vino = next(tracker.get_latest_entity_values("tipo_vino"), None)
        maridaje = next(tracker.get_latest_entity_values("maridaje"), None)
        tipo_pref = None
        valor_pref = None
        if cepa:
            tipo_pref, valor_pref = "cepa", cepa.capitalize()
        elif valle:
            tipo_pref, valor_pref = "valle", valle.capitalize()
        elif tipo_vino:
            tipo_pref, valor_pref = "tipo_vino", tipo_vino.capitalize()
        elif maridaje:
            tipo_pref, valor_pref = "maridaje", maridaje.capitalize()
        if not (tipo_pref and valor_pref):
            dispatcher.utter_message(text="No entendí qué preferencia quieres guardar. Prueba 'me gusta el Carmenere'.")
            return []
        conn = _get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM preferencias_usuario WHERE usuario_id = %s AND tipo_preferencia = %s", (usuario_id, tipo_pref))
            query = "INSERT INTO preferencias_usuario (usuario_id, tipo_preferencia, valor_preferencia) VALUES (%s, %s, %s)"
            cursor.execute(query, (usuario_id, tipo_pref, valor_pref))
            conn.commit()
            dispatcher.utter_message(text=f"¡Perfecto! He guardado que tu preferencia de '{tipo_pref}' es '{valor_pref}'.")
        except mysql.connector.Error as err:
            print(f"Error en ActionGuardarPreferencia: {err}")
            dispatcher.utter_message(text="Error al guardar tu preferencia.")
        finally:
            if conn: conn.close()
        return []


# === Formulario de Valoración (Simplificado) ===
class ValidateValorarTourForm(FormValidationAction):
    """Valida los slots del formulario (YA NO GUARDA)."""
    def name(self) -> Text:
        return "validate_valorar_tour_form"

    async def validate_slot_vina_a_valorar(
        self,
        value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Valida el nombre de la viña."""
        logger = logging.getLogger(__name__)
        conn = None 
        
        try:
            user_id_str = tracker.sender_id
            if not user_id_str or not user_id_str.startswith("user_"):
                dispatcher.utter_message(text="Debes 'iniciar sesión' para poder valorar un tour.")
                return {"slot_vina_a_valorar": None, "requested_slot": None} 

            vina_nombre = str(value)

            conn = _get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM vinas WHERE nombre LIKE %s LIMIT 1", (f"%{vina_nombre}%",))
            vina = cursor.fetchone()
            
            if not vina:
                logger.debug(f"validate_vina: Viña '{vina_nombre}' no encontrada en DB. Pidiendo de nuevo.")
                dispatcher.utter_message(text=f"No encontré una viña con el nombre '{vina_nombre}' en mi base de datos. ¿Puedes verificar el nombre?")
                return {"slot_vina_a_valorar": None}
            
            logger.debug(f"validate_vina: Viña '{vina_nombre}' validada con éxito.")
            # Corregido: Capitalizar el nombre de la viña
            return {"slot_vina_a_valorar": vina_nombre.capitalize()}

        except Exception as e:
            logger.error(f"ERROR INESPERADO en validate_slot_vina_a_valorar: {e}", exc_info=True) 
            dispatcher.utter_message(text="Tuvimos un problema inesperado al validar la viña. El equipo técnico ha sido notificado.")
            return {"slot_vina_a_valorar": None, "requested_slot": None}
            
        finally:
            if conn: 
                conn.close()

    async def validate_slot_rating(
        self,
        value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Valida el rating (puntaje)."""
        logger = logging.getLogger(__name__)
        latest_message = tracker.latest_message.get('text', '')
        
        match = re.search(r'\b([1-5])\b', latest_message)
        
        if match:
            rating = match.group(1)
            logger.debug(f"validate_rating: Rating '{rating}' validado (por regex).")
            return {"slot_rating": rating}
        
        # Corregido: 'value' es el texto, no la entidad.
        if latest_message in ["1", "2", "3", "4", "5"]:
             logger.debug(f"validate_rating: Rating '{latest_message}' validado.")
             return {"slot_rating": latest_message}
            
        logger.debug(f"validate_rating: Rating '{latest_message}' inválido. Pidiendo de nuevo.")
        dispatcher.utter_message(text="No entendí ese puntaje. Por favor, dime un número del 1 al 5.")
        return {"slot_rating": None}

    async def validate_slot_comentario(
        self,
        value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Valida el comentario."""
        logger = logging.getLogger(__name__)
        # 'value' es el texto real que escribió el usuario, gracias al mapeo 'from_text'
        comentario_texto = str(value)
        
        if comentario_texto.lower() in ["no", "no gracias", "sin comentario", "ninguno"]:
            logger.debug("validate_comentario: Usuario no quiso comentar. Guardando 'Sin comentario'.")
            return {"slot_comentario": "Sin comentario"}
        
        logger.debug(f"validate_comentario: Comentario '{comentario_texto}' validado.")
        return {"slot_comentario": comentario_texto}

    # === ¡FUNCIÓN 'submit' ELIMINADA DE AQUÍ! ===
    # La lógica de guardado se moverá a su propia acción.


# === ¡NUEVA ACCIÓN PARA GUARDAR EN LA BASE DE DATOS! ===
class ActionGuardarValoracionDb(Action):
    """
    Toma los slots llenados por el formulario y los guarda en la DB.
    Esta acción se llama DESPUÉS de que el formulario se completa.
    """
    def name(self) -> Text:
        return "action_guardar_valoracion_db"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        logger = logging.getLogger(__name__)
        logger.debug("ActionGuardarValoracionDb: Iniciando acción de guardado.") 
        
        conn = None 
        
        try:
            user_id_str = tracker.sender_id
            if not user_id_str or not user_id_str.startswith("user_"):
                 logger.warning(f"GuardarDB: Usuario no logueado (sender_id: {user_id_str}). Cancelando.")
                 dispatcher.utter_message(text="Error de sesión. Por favor, 'inicia sesión' de nuevo para valorar.")
                 return [] 

            usuario_id = int(user_id_str.split("_")[1])
            vina_nombre = tracker.get_slot("slot_vina_a_valorar")
            rating = tracker.get_slot("slot_rating")
            comentario = tracker.get_slot("slot_comentario")
            
            if not (vina_nombre and rating and comentario):
                logger.error(f"GuardarDB: Faltan slots. Viña: {vina_nombre}, Rating: {rating}, Comentario: {comentario}")
                dispatcher.utter_message(text="Lo siento, parece que faltaron datos en el formulario. Por favor, intenta 'valorar' de nuevo.")
                return []

            logger.debug(f"GuardarDB: Datos a guardar: UserID={usuario_id}, Viña={vina_nombre}, Rating={rating}, Comentario={comentario}")

            conn = _get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT id FROM vinas WHERE nombre LIKE %s LIMIT 1", (f"%{vina_nombre}%",))
            vina = cursor.fetchone()
            
            if not vina:
                logger.warning(f"GuardarDB: No se encontró la viña '{vina_nombre}' en la DB.")
                dispatcher.utter_message(text=f"Error fatal: No pude encontrar {vina_nombre} en la base de datos al guardar.")
                return []

            vina_id = vina['id']
            logger.debug(f"GuardarDB: Viña ID encontrada: {vina_id}")

            cursor.execute("DELETE FROM valoraciones_tour WHERE usuario_id = %s AND vina_id = %s", (usuario_id, vina_id))
            logger.debug("GuardarDB: DELETE de valoración anterior (si existía) completado.")
            
            query = "INSERT INTO valoraciones_tour (usuario_id, vina_id, rating, comentario) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (usuario_id, vina_id, rating, comentario))
            logger.debug("GuardarDB: INSERT de nueva valoración completado.")
            
            conn.commit()
            logger.debug("GuardarDB: conn.commit() exitoso.")
            
            # ¡Enviamos el mensaje de éxito aquí!
            dispatcher.utter_message(response="utter_valoracion_guardada")
        
        except Exception as e:
            logger.error(f"ERROR INESPERADO en ActionGuardarValoracionDb: {e}", exc_info=True) 
            dispatcher.utter_message(text="Tuvimos un problema inesperado al guardar tu valoración. El equipo técnico ha sido notificado.")
            
        finally:
            if conn: 
                conn.close()
                logger.debug("GuardarDB: Conexión a DB cerrada.")
            
        # Limpiamos los slots al final
        return [
            SlotSet("slot_vina_a_valorar", None),
            SlotSet("slot_rating", None),
            SlotSet("slot_comentario", None),
        ]
        
# === ACCIONES DE RECOMENDACIÓN (Sin cambios) ===
class ActionRecomendarVinoDb(Action):
    def name(self) -> Text: 
        return "action_recomendar_vino_db"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # ... (Tu código de recomendar vino va aquí, no necesita cambios) ...
        user_id_str = tracker.sender_id
        preferencias_guardadas = {}
        if user_id_str and user_id_str.startswith("user_"):
            try:
                usuario_id = int(user_id_str.split("_")[1])
                conn_prefs = _get_db_connection()
                cursor_prefs = conn_prefs.cursor(dictionary=True)
                cursor_prefs.execute("SELECT tipo_preferencia, valor_preferencia FROM preferencias_usuario WHERE usuario_id = %s", (usuario_id,))
                for pref in cursor_prefs.fetchall():
                    preferencias_guardadas[pref['tipo_preferencia']] = pref['valor_preferencia']
                cursor_prefs.close()
                conn_prefs.close()
                if preferencias_guardadas:
                    dispatcher.utter_message(text="*(Usando tus preferencias guardadas para esta búsqueda...)*")
            except Exception as e:
                print(f"Error al cargar preferencias de usuario: {e}")
        cepa_slot = tracker.get_slot("slot_cepa")
        tipo_slot = tracker.get_slot("slot_tipo_vino")
        valle_slot = tracker.get_slot("slot_valle")
        caracteristica_slot = tracker.get_slot("slot_caracteristica")
        maridaje_slot = tracker.get_slot("slot_maridaje")
        ano_slot = tracker.get_slot("slot_ano")
        latest_message = tracker.latest_message.get('text', '').lower()
        def find_keyword(text: str, keywords: List[str]) -> Optional[str]:
            for keyword in keywords:
                if keyword in text:
                    return keyword.capitalize()
            return None
        nota_sabor_txt = find_keyword(latest_message, GAZETTE["notas_sabor"])
        caracteristica_txt = find_keyword(latest_message, GAZETTE["caracteristicas"])
        maridaje_txt = find_keyword(latest_message, GAZETTE["maridajes"])
        cepa = cepa_slot or preferencias_guardadas.get("cepa")
        tipo = tipo_slot or preferencias_guardadas.get("tipo_vino")
        valle = valle_slot or preferencias_guardadas.get("valle")
        ano = ano_slot
        caracteristica = caracteristica_slot or caracteristica_txt or preferencias_guardadas.get("caracteristica")
        maridaje = maridaje_slot or maridaje_txt or preferencias_guardadas.get("maridaje")
        nota_sabor = nota_sabor_txt
        if not any([cepa, tipo, valle, caracteristica, maridaje, nota_sabor, ano]):
            dispatcher.utter_message(response="utter_pedir_gusto")
            return []
        conn = None
        try:
            conn = _get_db_connection()
            cursor = conn.cursor()
            query = "SELECT DISTINCT v.id, v.nombre, v.cepa, v.ano, v.tipo, va.nombre, va.valle, v.link_compra FROM vinos v JOIN vinas va ON v.vina_id = va.id "
            valores = []
            if nota_sabor:
                query += " JOIN vino_nota vn ON v.id = vn.vino_id JOIN notas_sabor ns ON vn.nota_id = ns.id"
                query += " AND ns.nombre = %s"
                valores.append(nota_sabor)
            if caracteristica:
                query += " JOIN vino_caracteristica vc ON v.id = vc.vino_id JOIN caracteristicas c ON vc.caracteristica_id = c.id"
                query += " AND c.nombre = %s"
                valores.append(caracteristica.capitalize())
            if maridaje:
                query += " JOIN vino_maridaje vm ON v.id = vm.vino_id JOIN maridajes m ON vm.maridaje_id = m.id"
                query += " AND m.nombre = %s"
                valores.append(maridaje.capitalize())
            query += " WHERE 1=1" 
            if cepa:
                query += " AND v.cepa = %s"
                valores.append(cepa.capitalize())
            if tipo:
                query += " AND v.tipo = %s"
                valores.append(tipo.capitalize())
            if valle:
                query += " AND va.valle LIKE %s"
                valores.append(f"%{valle}%")
            if ano:
                query += " AND v.ano = %s"
                valores.append(ano)
            query += " ORDER BY RAND() LIMIT 1;"
            cursor.execute(query, tuple(valores))
            resultado = cursor.fetchone()
            if resultado:
                vino_id, vino_nombre, cepa, ano, tipo, vina_nombre, valle_nombre, link = resultado
                respuesta_texto = f"¡Perfecto! Te recomiendo el vino **{vino_nombre}** ({cepa} {tipo}) del año **{ano}**, de Viña {vina_nombre} ({valle_nombre})."
                custom_payload = {"link": link, "link_text": f"Comprar {vino_nombre}"}
                dispatcher.utter_message(text=respuesta_texto, json_message=custom_payload)
            else:
                dispatcher.utter_message(text="Lo siento, no encontré un vino que cumpla con *todos* esos criterios tan específicos. Prueba con menos restricciones.")
        except mysql.connector.Error as err:
            print(f"Error de base de datos en ActionRecomendarVinoDb: {err}")
            dispatcher.utter_message(text="Tuvimos un problema al buscar en nuestra bodega virtual. ¿Podrías intentarlo de nuevo?")
        finally:
            if conn:
                conn.close()
        slots_to_reset = []
        if cepa_slot: slots_to_reset.append(SlotSet("slot_cepa", None))
        if tipo_slot: slots_to_reset.append(SlotSet("slot_tipo_vino", None))
        if valle_slot: slots_to_reset.append(SlotSet("slot_valle", None))
        if caracteristica_slot: slots_to_reset.append(SlotSet("slot_caracteristica", None))
        if maridaje_slot: slots_to_reset.append(SlotSet("slot_maridaje", None))
        if ano_slot: slots_to_reset.append(SlotSet("slot_ano", None))
        return slots_to_reset

class ActionBuscarTour(Action):
    def name(self) -> Text: 
        return "action_buscar_tour"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # ... (Tu código de buscar tour va aquí, no necesita cambios) ...
        vina_solicitada_entidad = tracker.get_slot("slot_vina")
        latest_message = tracker.latest_message.get('text', '').lower()
        vina_solicitada = None
        if vina_solicitada_entidad:
            vina_solicitada = vina_solicitada_entidad
        else:
            for vina_db in GAZETTE["vinas"]:
                if vina_db in latest_message:
                    vina_solicitada = vina_db.capitalize()
                    break
        if not vina_solicitada:
            dispatcher.utter_message(text="¿Qué viña específica te gustaría visitar para un tour?")
            return [] 
        conn = None
        try:
            conn = _get_db_connection()
            cursor = conn.cursor(dictionary=True) 
            query = "SELECT nombre, descripcion_tour, horario_tour, link_web, latitud, longitud FROM vinas WHERE nombre LIKE %s AND descripcion_tour IS NOT NULL LIMIT 1;"
            cursor.execute(query, (f"%{vina_solicitada}%",))
            resultado = cursor.fetchone()
            cursor.close()
            if resultado:
                nombre_vina = resultado.get("nombre")
                desc_tour = resultado.get("descripcion_tour")
                horario = resultado.get("horario_tour")
                link = resultado.get("link_web")
                lat = resultado.get("latitud")
                lon = resultado.get("longitud")
                respuesta_texto = f"¡Encontré información sobre el tour en **{nombre_vina}**! Detalles: {desc_tour}. Horario: {horario}."
                custom_payload = {"link": link, "link_text": f"Web de {nombre_vina}"}
                if lat and lon and GOOGLE_MAPS_API_KEY != "PEGA_TU_GOOGLE_MAPS_API_KEY_AQUÍ":
                    map_url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom=14&size=400x300&markers=color:red%7C{lat},{lon}&key={GOOGLE_MAPS_API_KEY}"
                    dispatcher.utter_message(image=map_url)
                else:
                    respuesta_texto += " Puedes encontrar más detalles en su sitio web."
                dispatcher.utter_message(text=respuesta_texto, json_message=custom_payload)
            else:
                dispatcher.utter_message(text=f"Lo siento, no encontré tours disponibles para la viña '{vina_solicitada}' o no tenemos información al respecto.")
        except mysql.connector.Error as err:
            print(f"Error de base de datos en ActionBuscarTour: {err}")
            dispatcher.utter_message(text="Tuvimos un problema al consultar la base de datos de tours. Por favor, inténtalo más tarde.")
        finally:
            if conn:
                conn.close()
        return [SlotSet("slot_vina", None)] 

class ActionRecomendarTourDb(Action):
    def name(self) -> Text: 
        return "action_recomendar_tour_db"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # ... (Tu código de recomendar tour va aquí, no necesita cambios) ...
        valle_deseado = tracker.get_slot("slot_valle")
        conn = None
        try:
            conn = _get_db_connection()
            cursor = conn.cursor(dictionary=True)
            base_query = "SELECT nombre, descripcion_tour, horario_tour, valle, link_web FROM vinas WHERE descripcion_tour IS NOT NULL"
            valores = []
            if valle_deseado:
                base_query += " AND valle LIKE %s"
                valores.append(f"%{valle_deseado}%")
            base_query += " ORDER BY RAND() LIMIT 1;"
            cursor.execute(base_query, tuple(valores))
            resultado = cursor.fetchone()
            cursor.close()
            if resultado:
                nombre_vina = resultado.get("nombre")
                desc_tour = resultado.get("descripcion_tour")
                horario = resultado.get("horario")
                valle = resultado.get("valle")
                link = resultado.get("link_web")
                mapa_url = VALLEY_MAPS.get(valle)
                if mapa_url:
                    dispatcher.utter_message(image=mapa_url)
                respuesta_texto = f"¡Tengo una excelente recomendación de tour! Puedes visitar la viña **{nombre_vina}** en el {valle}. El tour es: {desc_tour} (Horario: {horario})."
                custom_payload = {"link": link, "link_text": f"Ver más sobre {nombre_vina}"}
                dispatcher.utter_message(text=respuesta_texto, json_message=custom_payload)
            else:
                dispatcher.utter_message(text=f"Lo siento, no encontré tours disponibles en el **{valle_deseado if valle_deseado else 'país'}**. Prueba con un valle más amplio.")
        except mysql.connector.Error as err:
            print(f"Error de base de datos en ActionRecomendarTourDb: {err}")
            dispatcher.utter_message(text="Tuvimos un problema al consultar la base de datos de tours. Por favor, inténtalo más tarde.")
        finally:
            if conn:
                conn.close()
        return [SlotSet("slot_valle", None)]