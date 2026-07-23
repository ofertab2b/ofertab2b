import io
import os
import socket
import ssl
import oracledb
from flask import Flask, Response, render_template, request, redirect, url_for, flash
from openpyxl import Workbook
from dotenv import load_dotenv

# Carga credenciales locales desde .env. El archivo no debe versionarse.
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'cambiame_por_una_llave_secreta')

ORACLE_USER = os.environ.get('ORACLE_USER')
ORACLE_PASSWORD = os.environ.get('ORACLE_PASSWORD')
ORACLE_DSN = os.environ.get('ORACLE_DSN')
DEFAULT_QUERY = os.environ.get('DEFAULT_QUERY', 'SELECT SYSDATE FROM dual')


def normalize_dsn(dsn: str) -> str:
    """Normaliza un DSN Oracle y elimina esquemas HTTP incorrectos.

    Acepta formatos como:
    - host:port/service_name
    - host/service_name  -> se convierte en host:1521/service_name
    - http://host/service_name
    - https://host:port/service_name
    """
    dsn = dsn.strip()
    for prefix in ('http://', 'https://'):
        if dsn.lower().startswith(prefix):
            dsn = dsn[len(prefix):]
            break

    if '/' not in dsn:
        raise ValueError("ORACLE_DSN debe contener un servicio, por ejemplo 'host:1521/service_name'.")

    host_part, service_part = dsn.split('/', 1)
    if not host_part or not service_part:
        raise ValueError("ORACLE_DSN inválido. Usa 'host:port/service_name' o 'host/service_name'.")

    if ':' not in host_part:
        host_part = f'{host_part}:1521'

    return f'{host_part}/{service_part}'


def parse_dsn(dsn: str) -> tuple[str, int, str]:
    """Devuelve host, puerto y servicio desde un DSN normalizado."""
    normalized = normalize_dsn(dsn)
    host_part, service = normalized.split('/', 1)
    host, port = host_part.split(':', 1)
    return host, int(port), service


def check_tcp_port(host: str, port: int, timeout: float = 3.0) -> None:
    """Verifica que el puerto TCP esté abierto antes de intentar conectar a Oracle."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((host, port))


def get_connection():
    if not ORACLE_USER or not ORACLE_PASSWORD or not ORACLE_DSN:
        raise ConnectionError(
            'Falta la configuración de Oracle. Define ORACLE_USER, ORACLE_PASSWORD y ORACLE_DSN. '
            'En Vercel, agrégalas en Settings > Environment Variables y vuelve a desplegar.'
        )

    """Devuelve una conexión a Oracle usando variables de entorno."""
    normalized = normalize_dsn(ORACLE_DSN)
    host, port, service = parse_dsn(ORACLE_DSN)

    try:
        check_tcp_port(host, port)
    except Exception as exc:
        raise ConnectionError(
            f"No se pudo conectar al host {host} en el puerto {port}. "
            f"Asegúrate de que el listener Oracle está activo y el puerto está accesible. "
            f"Error TCP original: {exc}"
        ) from exc

    try:
        return oracledb.connect(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=normalized,
        )
    except Exception as exc:
        raise ConnectionError(
            f"No se pudo conectar a Oracle con DSN '{normalized}'. "
            f"Verifica host, puerto y servicio. Error original: {exc}"
        ) from exc


def generate_xlsx_response(columns, rows, filename='reporte.xlsx'):
    wb = Workbook()
    ws = wb.active
    ws.append(columns)
    for row in rows:
        ws.append([item if item is not None else '' for item in row])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = Response(output.getvalue(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response


@app.route('/', methods=['GET', 'POST'])
def index():
    query = DEFAULT_QUERY
    results = None
    columns = []
    error = None
    status_message = 'Escribe una consulta SQL SELECT y presiona Ejecutar.'

    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if not query:
            flash('Escribe una consulta SQL válida.', 'warning')
            return redirect(url_for('index'))

        # Limpiar la consulta: remover punto y coma al final y espacios extras
        clean_query = query.rstrip(';').strip()

        normalized = clean_query.lower().lstrip()
        if not normalized.startswith('select'):
            flash('Sólo se permiten consultas SELECT por seguridad.', 'danger')
            return redirect(url_for('index'))

        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(clean_query)
                    columns = [col[0] for col in cursor.description] if cursor.description else []
                    results = cursor.fetchmany(200)
                    if cursor.rowcount == 200:
                        flash('Se muestran las primeras 200 filas.', 'info')
        except Exception as exc:
            error = str(exc)
            flash(f'Error al ejecutar la consulta: {error}', 'danger')

    return render_template(
        'index.html',
        query=query,
        columns=columns,
        results=results,
        error=error,
        status_message=status_message,
        oracle_user=ORACLE_USER,
        oracle_dsn=ORACLE_DSN,
    )


@app.route('/value-search', methods=['GET', 'POST'])
def value_search():
    query = 'SELECT * FROM my_table WHERE id = :value'
    value = ''
    results = None
    columns = []
    error = None
    status_message = 'Ingresa una consulta SELECT con el placeholder :value y el valor a buscar.'

    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        value = request.form.get('value', '').strip()
        action = request.form.get('action', 'execute')
        if not query or not value:
            flash('Ingresa la consulta y el valor a buscar.', 'warning')
            return redirect(url_for('value_search'))

        clean_query = query.rstrip(';').strip()
        normalized = clean_query.lower().lstrip()
        if not normalized.startswith('select'):
            flash('Sólo se permiten consultas SELECT por seguridad.', 'danger')
            return redirect(url_for('value_search'))

        if ':value' not in normalized:
            flash('La consulta debe incluir el placeholder :value.', 'danger')
            return redirect(url_for('value_search'))

        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(clean_query, {'value': value})
                    columns = [col[0] for col in cursor.description] if cursor.description else []
                    rows = cursor.fetchall()
                    if action == 'download':
                        return generate_xlsx_response(columns, rows, filename='reporte_consulta.xlsx')
                    results = rows[:200]
                    if len(rows) >= 200:
                        flash('Se muestran las primeras 200 filas.', 'info')
        except Exception as exc:
            error = str(exc)
            flash(f'Error al ejecutar la consulta: {error}', 'danger')

    return render_template(
        'value_search.html',
        query=query,
        value=value,
        columns=columns,
        results=results,
        error=error,
        status_message=status_message,
        oracle_user=ORACLE_USER,
        oracle_dsn=ORACLE_DSN,
    )


@app.route('/starlink-phase', methods=['GET', 'POST'])
def starlink_phase():
    query = 'SELECT * FROM my_table WHERE phone = :value'
    value = ''
    results = None
    columns = []
    error = None
    status_message = 'Ingresa una consulta SELECT con el placeholder :value y el valor a buscar.'

    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        value = request.form.get('value', '').strip()
        action = request.form.get('action', 'execute')
        if not query or not value:
            flash('Ingresa la consulta y el teléfono a buscar.', 'warning')
            return redirect(url_for('starlink_phase'))

        clean_query = query.rstrip(';').strip()
        normalized = clean_query.lower().lstrip()
        if not normalized.startswith('select'):
            flash('Sólo se permiten consultas SELECT por seguridad.', 'danger')
            return redirect(url_for('starlink_phase'))

        if ':value' not in normalized:
            flash('La consulta debe incluir el placeholder :value.', 'danger')
            return redirect(url_for('starlink_phase'))

        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(clean_query, {'value': value})
                    columns = [col[0] for col in cursor.description] if cursor.description else []
                    rows = cursor.fetchall()
                    if action == 'download':
                        return generate_xlsx_response(columns, rows, filename='reporte_starlink.xlsx')
                    results = rows[:200]
                    if len(rows) >= 200:
                        flash('Se muestran las primeras 200 filas.', 'info')
        except Exception as exc:
            error = str(exc)
            flash(f'Error al ejecutar la consulta: {error}', 'danger')

    return render_template(
        'starlink_phase.html',
        query=query,
        value=value,
        columns=columns,
        results=results,
        error=error,
        status_message=status_message,
        oracle_user=ORACLE_USER,
        oracle_dsn=ORACLE_DSN,
    )


@app.route('/status')
def status():
    normalized = normalize_dsn(ORACLE_DSN)
    host, port, service = parse_dsn(ORACLE_DSN)
    try:
        with get_connection() as connection:
            version = connection.version
            return (
                f'Conectado a Oracle {version} como {ORACLE_USER}@{normalized}. '
                f'Host: {host}, puerto: {port}, servicio: {service}'
            )
    except Exception as exc:
        return (
            f'Error de conexión al intentar conectar con DSN {normalized}: {exc} '
            f'Comprueba que el listener Oracle está activo en {host}:{port} y que el servicio {service} existe.'
        ), 500


if __name__ == '__main__':
    # HTTP es el modo local predeterminado y funciona con el reenvío de puertos.
    # Para probar HTTPS con certificados auto-firmados, usa FLASK_HTTPS=1.
    if os.environ.get('FLASK_HTTPS') != '1':
        print('Iniciando aplicación en http://localhost:5000/')
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=os.environ.get('FLASK_DEBUG') == '1',
        )
        raise SystemExit(0)

    # Configurar HTTPS con certificados auto-firmados
    cert_file = os.path.join(os.path.dirname(__file__), 'cert.pem')
    key_file = os.path.join(os.path.dirname(__file__), 'key.pem')
    
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print(f"Error: Certificados no encontrados")
        print(f"  Certificado: {cert_file}")
        print(f"  Clave: {key_file}")
        print("\nGenera los certificados con: python generate_certs.py")
        exit(1)
    
    try:
        # Crear contexto SSL
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(cert_file, key_file)
        
        print(f"Iniciando aplicación con HTTPS")
        print(f"  Accede en: https://pel5cd229bqsm:5000/")
        print(f"  O en: https://localhost:5000/")
        print(f"  Nota: El navegador mostrará una advertencia de seguridad.")
        print(f"  Asegúrate de que el puerto 5000 está abierto en el firewall.")
        
        app.run(
            host='0.0.0.0',
            port=5000,
            ssl_context=ssl_context,
            debug=os.environ.get('FLASK_DEBUG') == '1',
        )
    except Exception as e:
        print(f"Error al iniciar HTTPS: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
