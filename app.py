import json
import os
from datetime import datetime, timedelta
import uuid
from io import BytesIO, StringIO
import locale
import csv
import traceback
import logging

# Configurar el logging básico
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Importar librerías para PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Image, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.units import inch
from reportlab.lib import colors

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, jsonify, send_file
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.secret_key = 'TU_CLAVE_SECRETA_AQUI_CAMBIAME_POR_UNA_MAS_SEGURA'

DECOMISOS_FILE = 'decomisos.json'
UPLOAD_FOLDER = 'uploads'
STATIC_FOLDER = 'static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES')
    except locale.Error:
        logging.warning("No se pudo configurar el locale a 'es_ES.UTF-8' o 'es_ES'. La fecha se mostrará en el idioma predeterminado.")

# Asegurarse de que la carpeta de subida exista
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def load_decomisos():
    """Carga los decomisos desde el archivo JSON."""
    if os.path.exists(DECOMISOS_FILE):
        with open(DECOMISOS_FILE, 'r', encoding='utf-8') as f:
            try:
                decomisos = json.load(f)
                for decomiso in decomisos:
                    # Convertir la cadena de fecha a objeto datetime
                    if 'fecha_decomiso' in decomiso and isinstance(decomiso['fecha_decomiso'], str):
                        try:
                            decomiso['fecha_decomiso'] = datetime.strptime(decomiso['fecha_decomiso'], '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            logging.error(f"Error al parsear la fecha para el decomiso {decomiso.get('id')}: {decomiso['fecha_decomiso']}. Asignando fecha actual.")
                            decomiso['fecha_decomiso'] = datetime.now() # Asignar fecha actual en caso de error
                    else:
                        # Si no hay fecha o no es string, asignar fecha actual
                        decomiso['fecha_decomiso'] = datetime.now()

                    # Asegurar que 'items' sea una lista iterable
                    current_items = decomiso.get('items', [])
                    if not isinstance(current_items, list):
                        logging.warning(f"Decomiso ID {decomiso.get('id', 'N/A')}: 'items' no era una lista. Tipo detectado: {type(current_items)}. Convirtiendo a lista vacía.")
                        decomiso['items'] = []
                    else:
                        decomiso['items'] = current_items

                    # Asegurar que 'archivos_adjuntos' exista y sea una lista
                    if 'archivos_adjuntos' not in decomiso or not isinstance(decomiso['archivos_adjuntos'], list):
                        decomiso['archivos_adjuntos'] = []
                return decomisos
            except json.JSONDecodeError as e:
                logging.error(f"Error al decodificar JSON de {DECOMISOS_FILE}: {e}")
                return []
    return []

def save_decomisos(decomisos):
    """Guarda los decomisos en el archivo JSON."""
    # Crear una copia profunda para evitar modificar los objetos datetime originales
    decomisos_to_save = []
    for decomiso in decomisos:
        decomiso_copy = decomiso.copy()
        if 'fecha_decomiso' in decomiso_copy and isinstance(decomiso_copy['fecha_decomiso'], datetime):
            decomiso_copy['fecha_decomiso'] = decomiso_copy['fecha_decomiso'].strftime('%Y-%m-%d %H:%M:%S')
        decomisos_to_save.append(decomiso_copy)

    with open(DECOMISOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(decomisos_to_save, f, indent=4, ensure_ascii=False)

# Función para formatear valores de moneda (puedes ajustar el símbolo y el separador decimal/miles)
@app.template_filter('format_currency')
def format_currency_filter(value):
    """Filtro de Jinja para formatear valores como moneda."""
    try:
        # Formatear el número a dos decimales y añadir el separador de miles
        # Puedes ajustar el símbolo de moneda '$' y la coma ',' o punto '.' según tu región
        return f"${value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return value # Retorna el valor original si no es un número válido
    
@app.route('/')
def index():
    """Muestra la página principal con la lista de decomisos."""
    decomisos = load_decomisos()
    # Ordenar los decomisos por fecha de forma descendente (más recientes primero)
    decomisos.sort(key=lambda x: x.get('fecha_decomiso', datetime.min), reverse=True)
    return render_template('index.html', decomisos=decomisos)

@app.route('/add_decomiso', methods=['GET', 'POST'])
def add_decomiso():
    """Maneja la adición de un nuevo decomiso."""
    if request.method == 'POST':
        try:
            decomisos = load_decomisos()
            
            # Generar un ID único para el nuevo decomiso
            new_id = 1
            if decomisos:
                new_id = max([d['id'] for d in decomisos]) + 1

            fecha_decomiso_str = request.form['fecha_decomiso']
            # Convertir de formato HTML datetime-local (YYYY-MM-DDTHH:MM) a objeto datetime
            fecha_decomiso_dt = datetime.strptime(fecha_decomiso_str, '%Y-%m-%dT%H:%M')

            items = []
            codigos = request.form.getlist('codigo[]')
            centros = request.form.getlist('centro[]')
            almacenes = request.form.getlist('almacen[]')
            lotes = request.form.getlist('lote[]')
            kilos = request.form.getlist('kilos[]')
            valores = request.form.getlist('valor[]')

            for i in range(len(codigos)):
                # Solo agregar el ítem si al menos uno de sus campos principales no está vacío
                if any([codigos[i], centros[i], almacenes[i], lotes[i], kilos[i], valores[i]]):
                    try:
                        k = float(kilos[i]) if kilos[i] else 0.0
                        v = float(valores[i]) if valores[i] else 0.0
                        items.append({
                            'codigo': codigos[i],
                            'centro': centros[i],
                            'almacen': almacenes[i],
                            'lote': lotes[i],
                            'kilos': k,
                            'valor': v
                        })
                    except ValueError:
                        flash(f"Error en los datos numéricos del ítem {i+1}. Asegúrate de que kilos y valor sean números.", 'danger')
                        # Puedes optar por omitir el ítem o asignar 0
                        items.append({
                            'codigo': codigos[i],
                            'centro': centros[i],
                            'almacen': almacenes[i],
                            'lote': lotes[i],
                            'kilos': 0.0,
                            'valor': 0.0
                        })
                        
            # Manejo de archivos adjuntos
            archivos_adjuntos = []
            if 'archivos' in request.files: # El campo de archivo se llama 'archivos' en add_decomiso.html
                for file in request.files.getlist('archivos'):
                    if file and file.filename:
                        # Generar un nombre de archivo único para evitar colisiones
                        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        archivos_adjuntos.append(filename)

            new_decomiso = {
                'id': new_id,
                'fecha_decomiso': fecha_decomiso_dt,
                'placa_camion': request.form['placa_camion'],
                'tipo_decomiso': request.form['tipo_decomiso'],
                'descripcion': request.form['descripcion'],
                'observaciones': request.form.get('observaciones', ''),
                'items': items,
                'archivos_adjuntos': archivos_adjuntos
            }
            
            decomisos.append(new_decomiso)
            save_decomisos(decomisos)
            flash('Decomiso agregado exitosamente!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            logging.error(f"Error al agregar decomiso: {traceback.format_exc()}")
            flash(f'Error al agregar el decomiso: {e}', 'danger')
            return redirect(url_for('add_decomiso')) # Mantener al usuario en la página de añadir
    return render_template('add_decomiso.html')

@app.route('/edit_decomiso/<string:decomiso_id>', methods=['GET', 'POST'])
def edit_decomiso(decomiso_id):
    """Maneja la edición de un decomiso existente."""
    decomisos = load_decomisos()
    decomiso_found = next((d for d in decomisos if d['id'] == int(decomiso_id)), None)

    if decomiso_found is None:
        flash('Decomiso no encontrado.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            fecha_decomiso_str = request.form['fecha_decomiso']
            # Convertir de formato HTML datetime-local (YYYY-MM-DDTHH:MM) a objeto datetime
            decomiso_found['fecha_decomiso'] = datetime.strptime(fecha_decomiso_str, '%Y-%m-%dT%H:%M')
            decomiso_found['placa_camion'] = request.form['placa_camion']
            decomiso_found['tipo_decomiso'] = request.form['tipo_decomiso']
            decomiso_found['descripcion'] = request.form['descripcion']
            decomiso_found['observaciones'] = request.form.get('observaciones', '')

            # Actualizar ítems
            items = []
            codigos = request.form.getlist('codigo[]')
            centros = request.form.getlist('centro[]')
            almacenes = request.form.getlist('almacen[]')
            lotes = request.form.getlist('lote[]')
            kilos = request.form.getlist('kilos[]')
            valores = request.form.getlist('valor[]')

            for i in range(len(codigos)):
                # Solo agregar el ítem si al menos uno de sus campos principales no está vacío
                if any([codigos[i], centros[i], almacenes[i], lotes[i], kilos[i], valores[i]]):
                    try:
                        k = float(kilos[i]) if kilos[i] else 0.0
                        v = float(valores[i]) if valores[i] else 0.0
                        items.append({
                            'codigo': codigos[i],
                            'centro': centros[i],
                            'almacen': almacenes[i],
                            'lote': lotes[i],
                            'kilos': k,
                            'valor': v
                        })
                    except ValueError:
                        flash(f"Error en los datos numéricos del ítem {i+1}. Asegúrate de que kilos y valor sean números.", 'warning')
                        items.append({
                            'codigo': codigos[i],
                            'centro': centros[i],
                            'almacen': almacenes[i],
                            'lote': lotes[i],
                            'kilos': 0.0,
                            'valor': 0.0
                        })
            decomiso_found['items'] = items

            # Manejo de archivos adjuntos existentes (eliminar si se desmarcan)
            archivos_a_mantener = request.form.getlist('existing_attachments')
            archivos_eliminados = [f for f in decomiso_found['archivos_adjuntos'] if f not in archivos_a_mantener]
            
            for filename in archivos_eliminados:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logging.info(f"Archivo eliminado: {file_path}")
            
            decomiso_found['archivos_adjuntos'] = archivos_a_mantener

            # Añadir nuevos archivos adjuntos
            if 'new_archivos_adjuntos' in request.files:
                for file in request.files.getlist('new_archivos_adjuntos'):
                    if file and file.filename:
                        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        decomiso_found['archivos_adjuntos'].append(filename)

            save_decomisos(decomisos)
            flash('Decomiso actualizado exitosamente!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            logging.error(f"Error al editar decomiso {decomiso_id}: {traceback.format_exc()}")
            flash(f'Error al actualizar el decomiso: {e}', 'danger')
            # Si hay un error, vuelve a cargar la página de edición con los datos actuales
            return render_template('edit_decomiso.html', decomiso=decomiso_found)

    logging.debug(f"Decomiso para editar: {decomiso_found}")
    return render_template('edit_decomiso.html', decomiso=decomiso_found)

@app.route('/delete_decomiso/<int:decomiso_id>') # Cambiado a int para coincidir con el ID
def delete_decomiso(decomiso_id):
    """Maneja la eliminación de un decomiso y sus archivos asociados."""
    decomisos = load_decomisos()
    initial_len = len(decomisos)
    
    decomiso_to_delete_files = next((d for d in decomisos if d['id'] == decomiso_id), None)

    # Filtrar el decomiso a eliminar
    decomisos = [d for d in decomisos if d['id'] != decomiso_id]
    
    if len(decomisos) < initial_len:
        # Si se eliminó un decomiso, eliminar sus archivos adjuntos
        if decomiso_to_delete_files and 'archivos_adjuntos' in decomiso_to_delete_files:
            for filename in decomiso_to_delete_files['archivos_adjuntos']:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logging.info(f"Archivo adjunto eliminado: {filename}")
                    except OSError as e:
                        logging.error(f"Error al eliminar archivo {file_path}: {e}")
        
        save_decomisos(decomisos)
        flash('Decomiso y archivos asociados eliminados exitosamente!', 'success')
    else:
        flash('Decomiso no encontrado.', 'danger')
    
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Sirve los archivos subidos."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.errorhandler(413)
def request_entity_too_large(error):
    """Maneja errores cuando el archivo subido es demasiado grande."""
    flash('El archivo es demasiado grande. Tamaño máximo permitido es 16MB.', 'danger')
    return redirect(request.url)

@app.errorhandler(HTTPException)
def handle_exception(e):
    """Retorna JSON en lugar de HTML para errores HTTP."""
    # start with the correct headers and status code from the error
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    flash(f"Un error ha ocurrido: {e.description}", 'danger')
    return response

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    """Maneja la carga de archivos CSV y procesa sus datos."""
    if 'file' not in request.files:
        return jsonify({'message': 'No se encontró el archivo'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No se seleccionó ningún archivo'}), 400
    
    if file and file.filename.endswith('.csv'):
        try:
            # Leer el archivo CSV en memoria
            stream = StringIO(file.read().decode('utf-8'))
            reader = csv.reader(stream) # Usar csv.reader para CSV sin encabezados
            
            items = []
            for i, row in enumerate(reader):
                # Asumiendo el orden de las columnas: codigo, centro, almacen, lote, kilos, valor
                # Asegúrate de que cada fila tenga al menos 6 columnas
                if len(row) < 6:
                    logging.warning(f"Fila {i+1} en CSV tiene menos columnas de las esperadas. Saltando fila.")
                    continue # Saltar filas incompletas

                # Acceder a las columnas por índice
                codigo = row[0].strip()
                centro = row[1].strip() # CORREGIDO: Acceder directamente desde 'row'
                almacen = row[2].strip() # CORREGIDO: Acceder directamente desde 'row'
                lote = row[3].strip()    # CORREGIDO: Acceder directamente desde 'row'
                
                # Reemplazar ',' por '.' para que float() lo interprete correctamente
                kilos_str = row[4].strip().replace('.', '').replace(',', '.') 
                valor_str = row[5].strip().replace('.', '').replace(',', '.') 

                try:
                    kilos = float(kilos_str)
                except ValueError:
                    kilos = 0.0
                    logging.warning(f"CSV: Kilos no válido '{kilos_str}' en fila {i+1}. Usando 0.0.")

                try:
                    valor = float(valor_str)
                except ValueError:
                    valor = 0.0
                    logging.warning(f"CSV: Valor no válido '{valor_str}' en fila {i+1}. Usando 0.0.")

                items.append({
                    'codigo': codigo,
                    'centro': centro,
                    'almacen': almacen,
                    'lote': lote,
                    'kilos': kilos,
                    'valor': valor
                })
            
            if not items:
                return jsonify({'message': 'El archivo CSV no contiene ítems válidos o está vacío.', 'items': []}), 200

            return jsonify({'message': 'CSV cargado exitosamente', 'items': items}), 200
        except Exception as e:
            logging.error(f"Error al procesar el archivo CSV: {traceback.format_exc()}")
            return jsonify({'message': f'Error al procesar el archivo CSV: {e}'}), 500
    else:
        return jsonify({'message': 'Tipo de archivo no permitido. Por favor, sube un archivo CSV.'}), 400

@app.route('/analysis')
def analysis():
    """Muestra la página de análisis y gráficos de decomisos."""
    decomisos = load_decomisos()
    total_kilos = 0.0
    total_valor_decomisado = 0.0 # Variable para el valor total decomisado

    # Procesar datos para gráficos
    data_for_charts = {
        'tipo_decomiso_valor': {}, # Tipo de decomiso vs. Valor total
        'tipo_decomiso_kilos': {}, # Tipo de decomiso vs. Kilos totales
        'decomisos_por_fecha': {} # Cantidad de decomisos por fecha
    }

    for decomiso in decomisos:
        tipo = decomiso.get('tipo_decomiso', 'Desconocido')
        fecha = decomiso.get('fecha_decomiso', datetime.now()) # Asegurar que es un datetime
        fecha_str = fecha.strftime('%Y-%m-%d') # Formato para agrupar por día

        # Asegúrate de que 'items' exista y sea iterable
        if 'items' in decomiso and isinstance(decomiso['items'], list):
            for item in decomiso['items']:
                try:
                    item_kilos = float(item.get('kilos', 0))
                    item_valor = float(item.get('valor', 0))

                    total_kilos += item_kilos
                    total_valor_decomisado += item_valor # Acumular el valor total

                    # Acumular por tipo de decomiso (valor)
                    data_for_charts['tipo_decomiso_valor'][tipo] = data_for_charts['tipo_decomiso_valor'].get(tipo, 0) + item_valor
                    # Acumular por tipo de decomiso (kilos)
                    data_for_charts['tipo_decomiso_kilos'][tipo] = data_for_charts['tipo_decomiso_kilos'].get(tipo, 0) + item_kilos

                except (ValueError, TypeError) as e:
                    logging.warning(f"Ítem con datos numéricos inválidos encontrado en decomiso {decomiso.get('id')}: {item}. Error: {e}")
                    pass # O manejar de otra manera, por ejemplo, ignorar el ítem
        
        # Acumular decomisos por fecha
        data_for_charts['decomisos_por_fecha'][fecha_str] = data_for_charts['decomisos_por_fecha'].get(fecha_str, 0) + 1

    # Convertir a listas de objetos para Chart.js
    chart_data = {
        'tipo_decomiso_valor': [{'label': k, 'value': v} for k, v in data_for_charts['tipo_decomiso_valor'].items()],
        'tipo_decomiso_kilos': [{'label': k, 'value': v} for k, v in data_for_charts['tipo_decomiso_kilos'].items()],
        'decomisos_por_fecha': [{'date': k, 'count': v} for k, v in sorted(data_for_charts['decomisos_por_fecha'].items())]
    }
    
    # Añadir estas líneas de print para depurar
    print("\n--- DEPURACIÓN DE DATOS PARA ANALYSIS ---")
    print(f"Decomisos cargados ({len(decomisos)}): {decomisos[:2]}...") # Muestra los primeros 2
    print(f"Total Kilos Decomisados: {total_kilos}")
    print(f"Total Valor Decomisado: {total_valor_decomisado}")
    print(f"Chart Data (tipo_decomiso_valor): {chart_data['tipo_decomiso_valor']}")
    print(f"Chart Data (tipo_decomiso_kilos): {chart_data['tipo_decomiso_kilos']}")
    print(f"Chart Data (decomisos_por_fecha): {chart_data['decomisos_por_fecha']}")
    print("-------------------------------------------\n")

    return render_template('analysis.html', 
                           chart_data=chart_data,
                           total_kilos=total_kilos,
                           total_valor_decomisado=total_valor_decomisado, 
                           total_decomisos_count=len(decomisos), 
                           all_decomisos=decomisos)
                           


@app.route('/download_pdf/<int:decomiso_id>') # Cambiado a int para coincidir con el ID
def download_pdf(decomiso_id):
    """Genera y descarga un informe PDF para un decomiso específico."""
    decomisos = load_decomisos()
    decomiso = next((d for d in decomisos if d['id'] == decomiso_id), None)

    if not decomiso:
        flash('Decomiso no encontrado para generar PDF.', 'danger')
        return redirect(url_for('index'))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=inch/2, leftMargin=inch/2,
                            topMargin=inch/2, bottomMargin=inch/2)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleStyle', fontSize=18, alignment=TA_CENTER, spaceAfter=14, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SubtitleStyle', fontSize=14, alignment=TA_CENTER, spaceAfter=8, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='HeadingStyle', fontSize=12, alignment=TA_LEFT, spaceAfter=6, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='NormalStyle', fontSize=10, alignment=TA_LEFT, spaceAfter=4))
    styles.add(ParagraphStyle(name='TableCaptionStyle', fontSize=10, alignment=TA_CENTER, spaceAfter=6, fontName='Helvetica-Bold'))

    elements = []

    elements.append(Paragraph("Informe de Decomiso", styles['TitleStyle']))
    elements.append(Spacer(1, 0.2 * inch))

    # Información general del decomiso
    elements.append(Paragraph("Detalles Generales", styles['HeadingStyle']))
    
    fecha_decomiso_formatted = decomiso['fecha_decomiso'].strftime('%d de %B de %Y a las %H:%M') if isinstance(decomiso['fecha_decomiso'], datetime) else "Fecha no disponible"
    elements.append(Paragraph(f"<b>ID de Decomiso:</b> {decomiso['id']}", styles['NormalStyle']))
    elements.append(Paragraph(f"<b>Fecha de Decomiso:</b> {fecha_decomiso_formatted}", styles['NormalStyle']))
    elements.append(Paragraph(f"<b>Placa de Camión:</b> {decomiso.get('placa_camion', 'N/A')}", styles['NormalStyle']))
    elements.append(Paragraph(f"<b>Tipo de Decomiso:</b> {decomiso.get('tipo_decomiso', 'N/A')}", styles['NormalStyle']))
    elements.append(Paragraph(f"<b>Descripción:</b> {decomiso.get('descripcion', 'N/A')}", styles['NormalStyle']))
    elements.append(Paragraph(f"<b>Observaciones:</b> {decomiso.get('observaciones', 'N/A')}", styles['NormalStyle']))
    elements.append(Spacer(1, 0.2 * inch))

    # Tabla de ítems
    if decomiso.get('items'):
        elements.append(Paragraph("Ítems Decomisados", styles['HeadingStyle']))
        data = [['Código', 'Centro', 'Almacén', 'Lote', 'Kilos (kg)', 'Valor ($)']]
        total_kilos_items = 0
        total_valor_items = 0
        for item in decomiso['items']:
            kilos = item.get('kilos', 0.0)
            valor = item.get('valor', 0.0)
            data.append([
                item.get('codigo', ''),
                item.get('centro', ''),
                item.get('almacen', ''),
                item.get('lote', ''),
                f"{kilos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), # Formato CLP
                f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") # Formato CLP
            ])
            total_kilos_items += kilos
            total_valor_items += valor
        
        # Fila de totales
        data.append(['', '', '', 'TOTAL', f"{total_kilos_items:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), f"{total_valor_items:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")])

        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')), # Encabezado azul
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#f8f9fa')), # Filas de datos
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')), # Borde de la tabla
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'), # Fila de totales en negrita
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e9ecef')), # Fondo para totales
            ('ALIGN', (-2, -1), (-1, -1), 'RIGHT'), # Alinear totales a la derecha
            ('RIGHTPADDING', (-2, -1), (-1, -1), 10), # Espacio para totales
        ])
        
        # Calcular anchos de columna (ajustar según necesidad)
        col_widths = [1.2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch, 1*inch]
        
        table = Table(data, colWidths=col_widths)
        table.setStyle(table_style)
        elements.append(table)
        elements.append(Spacer(1, 0.2 * inch))
    else:
        elements.append(Paragraph("No hay ítems decomisados registrados.", styles['NormalStyle']))
        elements.append(Spacer(1, 0.2 * inch))

    # Archivos adjuntos
    elements.append(Paragraph("Archivos Adjuntos", styles['HeadingStyle']))
    if decomiso.get('archivos_adjuntos'):
        for filename in decomiso['archivos_adjuntos']:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                try:
                    # Determinar si es una imagen
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                        # Obtener las dimensiones de la imagen
                        img = ImageReader(file_path)
                        original_width, original_height = img.getSize()

                        # Ancho máximo y alto máximo para la imagen en el PDF (aproximadamente, ajusta si es necesario)
                        max_width_pdf = A4[0] - inch # Ancho de página - márgenes
                        max_height_pdf = A4[1] / 4 # Un cuarto de la altura de la página

                        width_scale = max_width_pdf / original_width
                        height_scale = max_height_pdf / original_height
                        
                        # Usar el factor de escala más pequeño para asegurar que la imagen quepa en ambos sentidos
                        scale_factor = min(width_scale, height_scale)

                        # Redimensionar la imagen para el PDF
                        scaled_width = original_width * scale_factor
                        scaled_height = original_height * scale_factor

                        image_element = Image(file_path, width=scaled_width, height=scaled_height)
                        image_element.hAlign = 'CENTER' # Centrar la imagen
                        elements.append(image_element)
                        elements.append(Spacer(1, 0.1 * inch)) # Pequeño espacio después de la imagen
                    else:
                        elements.append(Paragraph(f"• {filename}", styles['NormalStyle']))
                except Exception as e:
                    logging.error(f"Error al cargar o redimensionar la imagen '{filename}': {e}")
                    elements.append(Paragraph(f"• {filename} (Error al mostrar la imagen)", styles['NormalStyle']))
            else:
                elements.append(Paragraph(f"• {filename} (Archivo no encontrado)", styles['NormalStyle']))
    else:
        elements.append(Paragraph("No hay archivos adjuntos.", styles['NormalStyle']))

    doc.build(elements)
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f"decomiso_{decomiso['id']}.pdf", mimetype='application/pdf')


if __name__ == '__main__':
    app.run(debug=True)