# Gestor de Decomisos

## Descripción del Proyecto

"Gestor de Decomisos" es una aplicación web diseñada para la administración y registro eficiente de decomisos. Permite a los usuarios crear, visualizar, editar y eliminar registros de decomisos, incluyendo detalles sobre la fecha, placa de camión, tipo de decomiso, descripción, observaciones e ítems asociados (código, centro, almacén, lote, kilos, valor). Además, la aplicación soporta la adjunción de imágenes a cada decomiso, la generación de informes en formato PDF, análisis visual de datos mediante gráficos y la exportación de información a CSV.

## Características Principales

* **Gestión Completa de Decomisos (CRUD):**
    * **Crear:** Añadir nuevos registros de decomisos con toda la información relevante e ítems.
    * **Visualizar:** Listar y ver los detalles de cada decomiso.
    * **Editar:** Modificar la información existente de los decomisos, incluyendo los ítems y archivos adjuntos.
    * **Eliminar:** Borrar registros de decomisos y sus archivos asociados.
* **Adjuntos de Archivos:** Permite adjuntar múltiples imágenes a cada decomiso para una documentación visual completa.
* **Generación de PDF:** Crea informes detallados en formato PDF para cada decomiso, incluyendo imágenes adjuntas.
* **Análisis de Datos:** Ofrece una sección de análisis con gráficos interactivos para visualizar tendencias de decomisos por tipo, valor, kilos y fecha, con filtros dinámicos. Los gráficos se pueden exportar a PDF.
* **Exportación de Datos:** Exporta el listado completo de decomisos a un archivo CSV.
* **Búsqueda:** Funcionalidad de búsqueda para encontrar decomisos específicos.
* **Interfaz Intuitiva:** Desarrollada con Bootstrap para una experiencia de usuario responsiva y amigable.

## Tecnologías Utilizadas

* **Backend:**
    * **Python 3.x:** Lenguaje de programación principal.
    * **Flask:** Microframework web para el desarrollo de la API y la lógica del servidor.
    * **ReportLab:** Librería Python para la generación de documentos PDF.
    * **UUID:** Para la generación de identificadores únicos para archivos.
* **Frontend:**
    * **HTML5 / CSS3:** Estructura y estilos de la interfaz de usuario.
    * **JavaScript:** Lógica interactiva del lado del cliente.
    * **Bootstrap 5:** Framework CSS para el diseño responsivo y componentes de la UI.
    * **Font Awesome:** Biblioteca de iconos.
    * **Chart.js:** Librería JavaScript para la creación de gráficos dinámicos.
    * **html2canvas:** Para capturar gráficos y otros elementos HTML en el lado del cliente.
    * **jsPDF:** Librería JavaScript para la generación de PDFs en el cliente (usada para la exportación de análisis).
* **Base de Datos/Almacenamiento:**
    * **JSON:** Los datos de los decomisos se almacenan en un archivo `decomisos.json`.
    * **Sistema de Archivos:** Los archivos adjuntos se guardan en la carpeta `uploads`.

## Estructura del Proyecto
```bash
├── app.py                      # Lógica principal del servidor Flask y rutas.
├── decomisos.json              # Base de datos de los decomisos en formato JSON.
├── templates/                  # Archivos HTML (Jinja2) para la interfaz de usuario.
│   ├── index.html              # Página principal que lista los decomisos.
│   ├── add_decomiso.html       # Formulario para añadir un nuevo decomiso.
│   ├── edit_decomiso.html      # Formulario para editar un decomiso existente.
│   └── analysis.html           # Página para el análisis y visualización de datos.
├── uploads/                    # Carpeta para almacenar los archivos adjuntos (imágenes).
└── static/                     # Carpeta para archivos estáticos (CSS, JS personalizados, imágenes, etc.).
```

## Instalación y Configuración

Sigue estos pasos para configurar y ejecutar el proyecto en tu entorno local:

1.  **Clonar el Repositorio:**
    ```bash
    git clone [https://github.com/TuUsuario/TuRepositorio.git](https://github.com/TuUsuario/TuRepositorio.git)
    cd TuRepositorio
    ```
    (Reemplaza `https://github.com/TuUsuario/TuRepositorio.git` con la URL real de tu repositorio.)

2.  **Crear un Entorno Virtual (Recomendado):**
    ```bash
    python -m venv venv
    ```
    # En Windows:
```bash
    .\venv\Scripts\activate
```
   # En macOS/Linux:
```bash
    source venv/bin/activate
```

3.  **Instalar Dependencias de Python:**
    Asegúrate de tener `Flask`, `ReportLab` y otras librerías necesarias. Puedes instalarlas manualmente o si generas un `requirements.txt`:
    ```bash
    pip install Flask reportlab Pillow # Pillow es útil para manejar imágenes en ReportLab
    ```
    (Si tienes un `requirements.txt`, ejecuta `pip install -r requirements.txt`).

4.  **Crear Carpetas Necesarias:**
    Asegúrate de que existan las carpetas `uploads` y `static` en el directorio raíz del proyecto:
    ```bash
    mkdir uploads
    mkdir static
    ```
    (Si no existen, Flask no podrá guardar los archivos adjuntos ni servir los estáticos correctamente).

5.  **Configurar `app.py`:**
    Abre `app.py` y cambia `app.secret_key = 'TU_CLAVE_SECRETA_AQUI_CAMBIAME_POR_UNA_MAS_SEGURA'` por una clave secreta fuerte de tu elección.

## Uso

Para iniciar la aplicación, ejecuta el archivo `app.py`:

```bash
python app.py
```
La aplicación estará disponible en http://127.0.0.1:5000/ (o el puerto que Flask configure).

**Autor:** [Luis David Espinoza @perreohipertenso]


**USO LIBRE**
