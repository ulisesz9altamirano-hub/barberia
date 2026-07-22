from datetime import datetime, timedelta
from functools import wraps
import os
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# Configuración de Clave Secreta para Manejo de Sesiones (Login)
app.secret_key = os.getenv("SECRET_KEY", "fadedshop_secret_key_2026")

# Credenciales de Administrador (se leen de variables de entorno o valores por defecto)
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "123456")

# Configuración de Base de Datos usando Variables de Entorno (Seguridad)
db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "Ulises_46326980"),
    "database": os.getenv("DB_NAME", "fadedshop"),
    "port": int(os.getenv("DB_PORT", 3306)),
}


def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        connection.autocommit = True
        return connection
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        return None


# Decorador para Proteger Rutas de Administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


# ==========================================================
# RUTAS DE AUTENTICACIÓN (LOGIN Y LOGOUT)
# ==========================================================


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        password = request.form.get("password")

        if usuario == ADMIN_USER and password == ADMIN_PASS:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_page"))
        else:
            flash("Usuario o contraseña incorrectos", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("login"))


# ==========================================================
# RUTAS DE VISTA
# ==========================================================


@app.route("/")
def home():
    conn = get_db_connection()
    if conn is None:
        return "Error al conectar a la base de datos", 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM servicios")
    servicios = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("index.html", servicios=servicios)


@app.route("/admin")
@admin_required
def admin_page():
    return render_template("admin.html")


# ==========================================================
# APIS PÚBLICAS Y DE CLIENTES
# ==========================================================


@app.route("/api/servicios", methods=["GET"])
def obtener_servicios():
    conn = get_db_connection()
    if conn is None:
        return (
            jsonify({"error": "Error de conexión con la base de datos"}),
            500,
        )
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, nombre, descripcion, duracion_minutos, precio FROM"
            " servicios"
        )
        servicios = cursor.fetchall()
        return jsonify(servicios), 200
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if "cursor" in locals() and cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/horarios", methods=["GET"])
def obtener_horarios():
    conn = get_db_connection()
    if conn is None:
        return (
            jsonify({"error": "Error de conexión con la base de datos"}),
            500,
        )

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT dia_semana, hora_apertura, hora_cierre, activo FROM"
            " horarios_laborales WHERE activo=True"
        )
        horarios = cursor.fetchall()
        for h in horarios:
            h["hora_apertura"] = str(h["hora_apertura"])
            h["hora_cierre"] = str(h["hora_cierre"])
        return jsonify(horarios), 200
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if "cursor" in locals() and cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/disponibilidad", methods=["GET"])
def ver_disponibilidad():
    fecha_str = request.args.get("fecha", datetime.now().strftime("%Y-%m-%d"))
    duracion_minutos = int(request.args.get("duracion", 30))

    conn = get_db_connection()
    if conn is None:
        return (
            jsonify({"error": "Error de conexión con la base de datos"}),
            500,
        )

    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT fecha_hora_inicio, fecha_hora_fin 
        FROM turnos 
        WHERE estado != 'cancelado' 
            AND fecha_hora_inicio >= %s 
            AND fecha_hora_fin <= %s
        """
        cursor.execute(
            query, (f"{fecha_str} 00:00:00", f"{fecha_str} 23:59:59")
        )
        turnos_ocupados = cursor.fetchall()

    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if "cursor" in locals() and cursor:
            cursor.close()
        if conn:
            conn.close()

    inicio_jornada = datetime.strptime(
        f"{fecha_str} 09:00:00", "%Y-%m-%d %H:%M:%S"
    )
    fin_jornada = datetime.strptime(
        f"{fecha_str} 20:00:00", "%Y-%m-%d %H:%M:%S"
    )

    horarios_disponibles = []
    bloque_actual = inicio_jornada

    while bloque_actual + timedelta(minutes=duracion_minutos) <= fin_jornada:
        bloque_fin = bloque_actual + timedelta(minutes=duracion_minutos)
        ocupado = False

        for t in turnos_ocupados:
            t_inicio = t["fecha_hora_inicio"]
            t_fin = t["fecha_hora_fin"]

            if bloque_actual < t_fin and bloque_fin > t_inicio:
                ocupado = True
                break

        if not ocupado:
            horarios_disponibles.append(bloque_actual.strftime("%H:%M"))

        bloque_actual += timedelta(minutes=30)

    return (
        jsonify({
            "fecha": fecha_str,
            "horarios_disponibles": horarios_disponibles,
        }),
        200,
    )


@app.route("/api/turnos", methods=["POST"])
def registrar_turno():
    datos = request.get_json(silent=True) or request.form

    if not datos or not all(
        k in datos
        for k in ("nombre", "telefono", "servicio_id", "fecha_hora_inicio")
    ):
        return (
            jsonify({"error": "Faltan datos obligatorios para la reserva"}),
            400,
        )

    nombre = str(datos["nombre"]).strip()
    telefono = str(datos["telefono"]).strip()

    try:
        servicio_id = int(datos["servicio_id"])
    except (ValueError, TypeError):
        return jsonify({"error": "El ID del servicio no es válido"}), 400

    fecha_str = str(datos["fecha_hora_inicio"]).replace("T", " ")
    if len(fecha_str) == 16:
        fecha_str += ":00"

    try:
        inicio_turno = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return (
            jsonify({
                "error": "Formato de fecha inválido. Usar YYYY-MM-DD HH:MM:SS"
            }),
            400,
        )

    conn = get_db_connection()
    if conn is None:
        return (
            jsonify({"error": "Error de conexión con la base de datos"}),
            500,
        )

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT duracion_minutos FROM servicios WHERE id=%s", (servicio_id,)
        )
        servicio = cursor.fetchone()
        if not servicio:
            return jsonify({"error": "El servicio seleccionado no existe"}), 404

        duracion = servicio["duracion_minutos"]
        fin_turno = inicio_turno + timedelta(minutes=duracion)

        query_conflicto = """
            SELECT id FROM turnos 
            WHERE estado != 'cancelado' 
                AND (fecha_hora_inicio < %s AND fecha_hora_fin > %s)
        """
        cursor.execute(query_conflicto, (fin_turno, inicio_turno))
        conflicto = cursor.fetchone()

        if conflicto:
            return (
                jsonify({
                    "error": (
                        "El horario seleccionado ya está ocupado por otro"
                        " turno"
                    )
                }),
                409,
            )

        cursor.execute(
            "SELECT id FROM usuarios WHERE telefono=%s", (telefono,)
        )
        usuario = cursor.fetchone()

        if usuario:
            usuario_id = usuario["id"]
        else:
            cursor.execute(
                "INSERT INTO usuarios (nombre, telefono) VALUES (%s, %s)",
                (nombre, telefono),
            )
            usuario_id = cursor.lastrowid

        query_insertar_turno = """
            INSERT INTO turnos (usuario_id, servicio_id, fecha_hora_inicio, fecha_hora_fin, estado) 
            VALUES (%s, %s, %s, %s, 'confirmado')
        """
        cursor.execute(
            query_insertar_turno,
            (usuario_id, servicio_id, inicio_turno, fin_turno),
        )
        conn.commit()

        return (
            jsonify({
                "mensaje": "¡Turno reservado con éxito!",
                "cliente": nombre,
                "inicio": inicio_turno.strftime("%Y-%m-%d %H:%M:%S"),
                "fin": fin_turno.strftime("%Y-%m-%d %H:%M:%S"),
            }),
            201,
        )

    except Error as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/mis-turnos", methods=["GET"])
def mis_turnos():
    telefono = request.args.get("telefono")

    if not telefono:
        return (
            jsonify({"error": "Se requiere el número de teléfono"}),
            400,
        )

    conn = get_db_connection()
    if conn is None:
        return (
            jsonify({"error": "Error de conexión con la base de datos"}),
            500,
        )

    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT 
                t.id,
                COALESCE(s.nombre, 'Servicio no encontrado') AS servicio,
                COALESCE(s.precio, 0) AS precio,
                t.fecha_hora_inicio,
                t.fecha_hora_fin,
                t.estado
            FROM turnos t
            LEFT JOIN usuarios u ON t.usuario_id = u.id
            LEFT JOIN servicios s ON t.servicio_id = s.id
            WHERE u.telefono = %s AND t.estado != 'cancelado'
            ORDER BY t.fecha_hora_inicio ASC
        """
        cursor.execute(query, (telefono,))
        turnos = cursor.fetchall()

        for t in turnos:
            if isinstance(t["fecha_hora_inicio"], datetime):
                t["fecha_hora_inicio"] = t["fecha_hora_inicio"].strftime(
                    "%Y-%m-%d %H:%M"
                )
            if isinstance(t["fecha_hora_fin"], datetime):
                t["fecha_hora_fin"] = t["fecha_hora_fin"].strftime(
                    "%Y-%m-%d %H:%M"
                )

        return jsonify(turnos), 200

    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if "cursor" in locals() and cursor:
            cursor.close()
        if conn:
            conn.close()




@app.route("/api/turnos", methods=["GET"])
@admin_required
def obtener_turnos():
    conn = get_db_connection()
    if conn is None:
        return (
            jsonify({"error": "Error de conexión con la base de datos"}),
            500,
        )

    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT 
            t.id,
            COALESCE(u.nombre, 'Sin nombre') AS cliente,
            COALESCE(u.telefono, 'Sin teléfono') AS telefono,
            COALESCE(s.nombre, 'Servicio no encontrado') AS servicio,
            COALESCE(s.precio, 0) AS precio,
            t.fecha_hora_inicio,
            t.fecha_hora_fin,
            t.estado
        FROM turnos t
        LEFT JOIN usuarios u ON t.usuario_id = u.id
        LEFT JOIN servicios s ON t.servicio_id = s.id
        ORDER BY t.fecha_hora_inicio ASC
        """

        cursor.execute(query)
        turnos = cursor.fetchall()

        for t in turnos:
            if isinstance(t["fecha_hora_inicio"], datetime):
                t["fecha_hora_inicio"] = t["fecha_hora_inicio"].strftime(
                    "%Y-%m-%d %H:%M"
                )
            if isinstance(t["fecha_hora_fin"], datetime):
                t["fecha_hora_fin"] = t["fecha_hora_fin"].strftime(
                    "%Y-%m-%d %H:%M"
                )
        return jsonify(turnos), 200

    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if "cursor" in locals() and cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/turnos/<int:turno_id>", methods=["DELETE"])
@admin_required
def cancelar_turno(turno_id):
    conn = get_db_connection()
    if conn is None:
        return (
            jsonify({"error": "Error de conexión con la base de datos"}),
            500,
        )

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM turnos WHERE id=%s", (turno_id,))
        turno = cursor.fetchone()

        if not turno:
            return jsonify({"error": "El turno especificado no existe"}), 404

        cursor.execute("DELETE FROM turnos WHERE id=%s", (turno_id,))
        conn.commit()

        return (
            jsonify({
                "mensaje": (
                    f"Turno #{turno_id} eliminado con éxito de la base de datos"
                )
            }),
            200,
        )

    except Error as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if "cursor" in locals() and cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    app.run(debug=True, port=5000)