# Aplicación web de consultas a Oracle

Esta aplicación usa Flask para permitir consultas SQL `SELECT` contra una base de datos Oracle.

## Requisitos

- Python 3.13
- Conexión Oracle disponible
- Variables de entorno configuradas:
  - `ORACLE_USER`
  - `ORACLE_PASSWORD`
  - `ORACLE_DSN` (por ejemplo `host:1521/service_name` o `localhost:1521/orclpdb1`)
  - `FLASK_SECRET_KEY` (opcional)

> Si recibes `DPY-6005` o conexión denegada, verifica:
> - Oracle está levantado y escuchando en el puerto correcto.
> - `ORACLE_DSN` es el listener Oracle, no una URL web.
> - El formato debe ser `host:port/service_name` o `host/service_name`.
> - El servicio y el usuario/contraseña son correctos.
>
> Ejemplos válidos:
> - `127.0.0.1:1521/orclpdb1`
> - `localhost/orclpdb1` (se convierte a `localhost:1521/orclpdb1` automáticamente)
>
> La aplicación ahora comprueba primero si el puerto TCP está accesible antes de intentar la conexión Oracle. Si el puerto está cerrado, verás un mensaje más claro en la web.

## Instalación

```powershell
cd c:\Users\jperezr\Downloads\Web1
.venv\Scripts\pip install -r requirements.txt
```

## Ejecución

1. Crea el archivo `.env` a partir de la plantilla:

```powershell
Copy-Item .env.example .env
```

2. Abre `.env` y reemplaza `REEMPLAZA_CON_TU_PASSWORD` con la contraseña de Oracle. Este archivo está excluido de Git.

3. Inicia la aplicación:

```powershell
.venv\Scripts\python app.py
```

Después abre `http://127.0.0.1:5001` en el navegador. Para usar otro puerto, define la variable `PORT`; por ejemplo: `$env:PORT='5000'`. La aplicación local usa únicamente HTTP.

> Importante: `ORACLE_DSN` es la cadena de conexión Oracle, no la URL de la página web.

## Despliegue en Vercel

Vercel no lee el archivo `.env` de tu equipo ni los secretos guardados en GitHub. En el proyecto de Vercel, abre **Settings > Environment Variables** y crea estas variables para los entornos **Production**, **Preview** y **Development**:

- `ORACLE_USER`
- `ORACLE_PASSWORD`
- `ORACLE_DSN` (formato: `host:1521/service_name`)
- `FLASK_SECRET_KEY` (un valor aleatorio y privado)

Guarda los cambios y ejecuta **Deployments > Redeploy**. No publiques estas variables en el repositorio ni en `.env.example`.

> La base de datos Oracle debe ser accesible desde internet para que Vercel pueda conectarse. Si solo está disponible en una red privada, usa un backend desplegado dentro de esa red o habilita una conexión de red segura; Vercel no puede acceder a direcciones internas.

## Publicar en GitHub Pages

Esta aplicación contiene ahora una versión estática diseñada para GitHub Pages:

- `index.html`
- `value_search.html`
- `starlink_phase.html`

Estas páginas se pueden publicar directamente en GitHub Pages desde la rama principal, ya que son estáticas y no requieren el backend Flask.

Para habilitar GitHub Pages:

1. Sube el repositorio a GitHub.
2. En la configuración del repositorio, ve a **Pages**.
3. Selecciona la rama `main` (o `master`) y la carpeta `/root` como fuente.
4. Guarda los cambios.

Después de unos minutos, la web estará disponible en `https://<tu_usuario>.github.io/<tu_repositorio>/`.

> Nota: Las páginas estáticas sirven solo para mostrar la interfaz. Las consultas SQL reales solo funcionan con el backend Flask y la conexión Oracle.

## Uso

- Inserta consultas SQL `SELECT` en el formulario.
- La aplicación muestra hasta 200 filas de resultado.
- La ruta `/status` permite verificar la conexión.
