import streamlit as st
from openai import OpenAI
import sqlite3
from fpdf import FPDF
import base64
from io import BytesIO
import re
import os

# Configuración inicial de la página
st.set_page_config(
    page_title="Taller de Bienes Raíces",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Configuración del cliente de OpenAI
client = None
if 'OPENAI_API_KEY' in st.secrets:
    try:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        st.session_state['openai_configured'] = True
    except Exception as e:
        st.error(f"Error al configurar OpenAI: {str(e)}")
        st.session_state['openai_configured'] = False
else:
    st.warning("Funcionalidad de IA limitada - No se configuró OPENAI_API_KEY")
    st.session_state['openai_configured'] = False

# Estilos CSS personalizados
def load_css():
    st.markdown("""
    <style>
        :root {
            --azul-oscuro: #1E3A8A;
            --gris: #6B7280;
            --blanco: #FFFFFF;
            --verde: #10B981;
            --rojo: #EF4444;
        }
        
        .stApp {
            max-width: 900px;
            margin: auto;
            font-family: 'Arial', sans-serif;
            background-color: #F9FAFB;
        }
        
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .logo {
            height: 80px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .calculator-container {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            border: 1px solid #E5E7EB;
        }
        
        .stButton>button {
            background-color: var(--azul-oscuro);
            color: white;
            border-radius: 8px;
            padding: 10px 24px;
            font-weight: bold;
            width: 100%;
            transition: all 0.3s ease;
        }
        
        .stButton>button:hover {
            background-color: #1E40AF;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(30, 58, 138, 0.2);
        }
        
        .stTextInput>div>div>input, 
        .stNumberInput>div>div>input,
        .stSelectbox>div>div>select,
        .stMultiselect>div>div>div {
            border-radius: 8px;
            border: 1px solid var(--gris);
            padding: 10px;
        }
        
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: var(--azul-oscuro);
        }
        
        .positive-value {
            color: var(--verde);
            font-weight: bold;
        }
        
        .negative-value {
            color: var(--rojo);
            font-weight: bold;
        }
        
        .help-icon {
            display: inline-flex;
            align-items: center;
            cursor: pointer;
            margin-left: 5px;
        }
        
        .help-text {
            display: none;
            position: absolute;
            background-color: white;
            border: 1px solid var(--gris);
            padding: 10px;
            border-radius: 5px;
            z-index: 100;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            width: 250px;
            left: 20px;
            top: 0;
        }
        
        .help-icon:hover .help-text {
            display: block;
        }
        
        @media (max-width: 768px) {
            .header-container {
                flex-direction: column;
                text-align: center;
            }
            
            .logo {
                margin-bottom: 15px;
            }
        }
        
        /* Estilos para la tabla de ejemplo */
        .example-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-size: 0.9em;
        }
        
        .example-table th, .example-table td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        .example-table th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        
        .example-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        .example-table tr:hover {
            background-color: #f1f1f1;
        }
    </style>
    """, unsafe_allow_html=True)

# Funciones utilitarias
def format_currency(value):
    return f"${value:,.2f}" if value else "$0.00"

def parse_currency(currency_str):
    if not currency_str:
        return 0.0
    num_str = re.sub(r'[^\d.]', '', currency_str)
    return float(num_str) if num_str else 0.0

def emoji_help_tooltip(text, emoji="🧠"):
    st.markdown(f"""
    <span class="help-icon">
        {emoji}
        <span class="help-text">{text}</span>
    </span>
    """, unsafe_allow_html=True)

# Funciones de base de datos
def crear_base_datos():
    conn = sqlite3.connect('usuarios.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            edad INTEGER,
            email TEXT,
            telefono TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS finanzas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            ingresos_mensuales REAL,
            gastos_mensuales REAL,
            activos_totales REAL,
            pasivos_totales REAL,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')
    conn.commit()
    conn.close()

def registrar_usuario(nombre, edad, email, telefono):
    if edad < 18:
        st.warning("Debes ser mayor de 18 años para usar este programa.")
        return None
    conn = sqlite3.connect('usuarios.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO usuarios (nombre, edad, email, telefono)
        VALUES (?, ?, ?, ?)
    ''', (nombre, edad, email, telefono))
    usuario_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return usuario_id

# Funciones de análisis financiero
def analizar_proyeccion_retiro(edad_actual, edad_retiro, ingresos_retiro, gastos_retiro, ahorros_retiro, patrimonio_neto, flujo_caja):
    años_ahorro = edad_retiro - edad_actual
    necesidad_total = (ingresos_retiro - gastos_retiro) * (100 - edad_retiro)
    ahorro_necesario_anual = (necesidad_total - ahorros_retiro) / años_ahorro if años_ahorro > 0 else 0
    
    if patrimonio_neto > 50000 and flujo_caja > 1000:
        nivel = "Alto"
        recomendaciones = [
            "Tienes un excelente perfil para comenzar a invertir en bienes raíces de inmediato.",
            "Considera propiedades generadoras de ingresos pasivos como apartamentos en arriendo o locales comerciales."
        ]
        cursos_recomendados = ["Curso Avanzado de Inversión en Bienes Raíces"]
    elif patrimonio_neto > 20000 and flujo_caja > 500:
        nivel = "Medio"
        recomendaciones = [
            "Tienes potencial para inversión en bienes raíces, pero necesitas mejorar tu flujo de caja.",
            "Considera comenzar con propiedades pequeñas o co-inversiones."
        ]
        cursos_recomendados = ["Curso Intermedio de Bienes Raíces"]
    else:
        nivel = "Bajo"
        recomendaciones = [
            "Necesitas fortalecer tu situación financiera antes de invertir en bienes raíces.",
            "Enfócate en aumentar tus ingresos y reducir deudas."
        ]
        cursos_recomendados = ["Curso Básico de Educación Financiera para Bienes Raíces"]
    
    return {
        "años_ahorro": años_ahorro,
        "necesidad_total": necesidad_total,
        "ahorro_necesario_anual": ahorro_necesario_anual,
        "nivel_inversion": nivel,
        "analisis": f"""
        Proyección de Retiro con Enfoque en Bienes Raíces:
        - Años hasta el retiro: {años_ahorro}
        - Necesidad total estimada: {format_currency(necesidad_total)}
        - Ahorros actuales: {format_currency(ahorros_retiro)}
        - Necesitas ahorrar aproximadamente {format_currency(ahorro_necesario_anual)} anuales para alcanzar tu meta.
        
        Perfil de Inversión: {nivel}
        
        Recomendaciones Específicas:
        {"\n".join(recomendaciones)}
        
        Cursos Recomendados:
        {"\n".join(cursos_recomendados)}
        """
    }

def analizar_situacion_financiera(ingresos, gastos, activos, pasivos):
    flujo_caja_mensual = ingresos - gastos
    patrimonio_neto = activos - pasivos
    
    if patrimonio_neto > 50000 and flujo_caja_mensual > 1000:
        perfil = "Alto (70-100%)"
        descripcion = "Excelente perfil para inversión en bienes raíces. Tienes la capacidad financiera para comenzar a invertir en propiedades generadoras de ingresos pasivos."
        recomendaciones = mostrar_recomendacion_curso(
            "🚀 Recomendación para tu Perfil Alto",
            "Mentoría Avanzada en Tiendas Online",
            "https://landing.carlosdevis.com/mentoria-tienda-online",
            [
                "Estrategias avanzadas de escalamiento",
                "Automatización de procesos",
                "Fuentes alternativas de ingreso"
            ]
        )
    elif patrimonio_neto > 20000 and flujo_caja_mensual > 500:
        perfil = "Medio (40-69%)"
        descripcion = "Buen potencial para inversión en bienes raíces. Considera comenzar con propiedades pequeñas o co-inversiones mientras mejoras tu flujo de caja."
        recomendaciones = mostrar_recomendacion_curso(
            "📈 Recomendación para tu Perfil Medio",
            "Programa Avanzado en Tiendas Online",
            "https://landing.carlosdevis.com/cv-avanzado-tienda-online",
            [
                "Modelos de negocio probados",
                "Tácticas de conversión",
                "Fuentes de tráfico escalables"
            ]
        )
    else:
        perfil = "Bajo (0-39%)"
        descripcion = "Necesitas fortalecer tu situación financiera antes de invertir en bienes raíces. Enfócate en aumentar ingresos, reducir deudas y ahorrar."
        recomendaciones = mostrar_recomendacion_curso(
            "📚 Recomendación para tu Perfil Bajo",
            "Programa Avanzado en Tiendas Online",
            "https://landing.carlosdevis.com/cv-avanzado-tienda-online",
            [
                "Fundamentos sólidos",
                "Gestión financiera básica",
                "Primeros pasos en digital"
            ]
        )
    
    # Mostrar métricas
    st.subheader("📊 Análisis Resumen de tu Situación Financiera")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Ingresos Mensuales", format_currency(ingresos))
        st.metric("Gastos Mensuales", format_currency(gastos))
        st.metric("Flujo de Caja Mensual", format_currency(flujo_caja_mensual), 
                 delta="Positivo" if flujo_caja_mensual > 0 else "Negativo",
                 delta_color="normal" if flujo_caja_mensual > 0 else "inverse")
    
    with col2:
        st.metric("Activos Totales", format_currency(activos))
        st.metric("Pasivos Totales", format_currency(pasivos))
        st.metric("Patrimonio Neto", format_currency(patrimonio_neto), 
                 delta="Positivo" if patrimonio_neto > 0 else "Negativo",
                 delta_color="normal" if patrimonio_neto > 0 else "inverse")
    
    # Mostrar perfil y recomendaciones
    st.subheader("🏡 Perfil de Inversión en Bienes Raíces")
    st.markdown(f"**Nivel:** {perfil}")
    st.markdown(descripcion)
    
    st.markdown(recomendaciones)
    
    # Análisis específico
    st.subheader("🔍 Análisis Específico para Bienes Raíces")
    if flujo_caja_mensual > 0:
        st.success(f"Flujo de caja positivo de {format_currency(flujo_caja_mensual)}/mes. Podrías destinar parte de este excedente a inversión en propiedades.")
    else:
        st.error(f"Flujo de caja negativo de {format_currency(abs(flujo_caja_mensual))}/mes. Necesitas equilibrar tus finanzas antes de considerar inversiones.")
    
    if patrimonio_neto > 50000:
        st.success("Patrimonio neto sólido. Podrías usar parte como garantía para financiamiento de propiedades.")
    elif patrimonio_neto > 0:
        st.warning("Patrimonio neto positivo pero modesto. Considera estrategias de bajo riesgo como alquiler de habitaciones.")
    else:
        st.error("Patrimonio neto negativo. Enfócate en reducir deudas antes de invertir.")
    
    return {
        "flujo_caja": flujo_caja_mensual,
        "patrimonio": patrimonio_neto,
        "perfil_inversion": {"nivel": perfil, "descripcion": descripcion},
        "resumen": f"""
        Situación Financiera Actual:
        - Ingresos Mensuales: {format_currency(ingresos)}
        - Gastos Mensuales: {format_currency(gastos)}
        - Flujo de Caja: {format_currency(flujo_caja_mensual)} ({'Positivo' if flujo_caja_mensual > 0 else 'Negativo'})
        - Activos Totales: {format_currency(activos)}
        - Pasivos Totales: {format_currency(pasivos)}
        - Patrimonio Neto: {format_currency(patrimonio_neto)} ({'Positivo' if patrimonio_neto > 0 else 'Negativo'})
        
        Perfil de Inversión en Bienes Raíces: {perfil}
        {descripcion}
        """
    }

def mostrar_recomendacion_curso(titulo, curso, enlace, tips):
    return f"""
    **{titulo}**  
    **Curso recomendado:** {curso}  
    [Enlace al curso]({enlace})
    
    **3 Tips importantes:**
    1. **{tips[0]}**
    2. **{tips[1]}**
    3. **{tips[2]}**
    """

def generar_pdf(usuario_data, finanzas_data, analisis_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Encabezado
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Informe Financiero - Taller de Bienes Raíces", ln=1, align='C')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Análisis de Inversión en Bienes Raíces", ln=1, align='C')
    pdf.ln(10)
    
    # Datos personales
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Datos Personales:", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Nombre: {usuario_data.get('nombre', '')}", ln=1)
    pdf.cell(200, 10, txt=f"Edad: {usuario_data.get('edad', '')}", ln=1)
    pdf.cell(200, 10, txt=f"Email: {usuario_data.get('email', '')}", ln=1)
    pdf.ln(5)
    
    # Datos financieros
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Situación Financiera:", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Ingresos Mensuales: {format_currency(finanzas_data.get('ingresos', 0))}", ln=1)
    pdf.cell(200, 10, txt=f"Gastos Mensuales: {format_currency(finanzas_data.get('gastos', 0))}", ln=1)
    pdf.cell(200, 10, txt=f"Activos Totales: {format_currency(finanzas_data.get('activos', 0))}", ln=1)
    pdf.cell(200, 10, txt=f"Pasivos Totales: {format_currency(finanzas_data.get('pasivos', 0))}", ln=1)
    pdf.ln(5)
    
    # Perfil de inversión
    if 'perfil_inversion' in analisis_data:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt=f"Perfil de Inversión en Bienes Raíces: {analisis_data['perfil_inversion']['nivel']}", ln=1)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, txt=analisis_data['perfil_inversion']['descripcion'])
        pdf.ln(5)
    
    # Análisis
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Análisis y Recomendaciones:", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=analisis_data.get('resumen', ''))
    pdf.ln(5)
    
    # Plan de trabajo
    if 'plan_trabajo' in analisis_data:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="Plan de Trabajo Personalizado:", ln=1)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, txt=analisis_data['plan_trabajo'])
    
    # Generar el PDF en memoria
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_bytes = pdf_output.getvalue()
    pdf_output.close()
    
    return pdf_bytes

def generar_plan_trabajo(ingresos, gastos, activos, pasivos):
    if not st.session_state.get('openai_configured', False):
        return "Servicio de IA no disponible. Configura tu clave de OpenAI API para habilitar esta función."
    
    prompt = f"""
    Como experto en bienes raíces y finanzas personales, analiza esta situación:
    - Ingresos: {format_currency(ingresos)}/mes
    - Gastos: {format_currency(gastos)}/mes
    - Activos: {format_currency(activos)}
    - Pasivos: {format_currency(pasivos)}
    
    Crea un plan detallado para inversión en bienes raíces que incluya:
    1. Diagnóstico de la situación actual
    2. Estrategias para mejorar flujo de caja
    3. Plan de reducción de deudas
    4. Recomendaciones de inversión personalizadas
    5. Metas a corto, mediano y largo plazo
    6. Ejercicios prácticos
    7. Recomendaciones de cursos
    
    Usa lenguaje claro y motivador, con ejemplos concretos.
    Respuesta en español.
    """
    
    try:
        with st.spinner('Generando tu plan personalizado...'):
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un asesor experto en inversión en bienes raíces. Responde en español con enfoque práctico."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error al generar el plan: {str(e)}")
        return "No se pudo generar el plan en este momento."

# Interfaz principal
def main():
    load_css()
    crear_base_datos()
    
    # Encabezado
    st.markdown("""
    <div class="header-container">
        <div>
            <h1 style="margin:0;color:#1E3A8A;">Taller de Bienes Raíces</h1>
            <h3 style="margin:0;color:#6B7280;">Calculadora Financiera para Inversión Inmobiliaria</h3>
        </div>
        <img src="https://raw.githubusercontent.com/Santospe2000/Calculator_IA/main/WhatsApp%20Image%202025-05-19%20at%2012.57.14%20PM.jpeg" class="logo" alt="Logo">
    </div>
    
    <div class="calculator-container">
        Esta herramienta te ayudará a analizar tu capacidad para invertir en bienes raíces, 
        crear un plan de acción y establecer metas claras para construir patrimonio inmobiliario.
    </div>
    """, unsafe_allow_html=True)
    
    # Inicializar variables de sesión
    if 'reporte_data' not in st.session_state:
        st.session_state['reporte_data'] = {'usuario': {}, 'finanzas': {}, 'analisis': {}}
    
    # Paso 1: Registro de usuario
    with st.container():
        st.subheader("📝 Información Personal")
        nombre = st.text_input("Nombre completo")
        edad = st.number_input("Edad", min_value=18, max_value=100, value=30)
        email = st.text_input("Email")
        telefono = st.text_input("Teléfono")
        
        if st.button("Guardar información personal"):
            if nombre and email:
                usuario_id = registrar_usuario(nombre, edad, email, telefono)
                st.session_state['usuario_id'] = usuario_id
                st.session_state['reporte_data']['usuario'] = {
                    'nombre': nombre, 'edad': edad, 'email': email, 'telefono': telefono
                }
                st.success("Información guardada correctamente")
            else:
                st.warning("Por favor completa todos los campos obligatorios")
    
    # Paso 2: Datos financieros
    if 'usuario_id' in st.session_state:
        with st.container():
            st.subheader("📊 Elaborar mi presupuesto")
            st.markdown("""
            **Ejercicio:** Haz un presupuesto detallado de tus gastos. 
            Revisa extractos y anota todo lo que gastas en efectivo. 
            Identifica oportunidades para destinar recursos a inversión en bienes raíces.
            """)
            
            st.subheader("💰 Activos y Pasivos")
            
            # Tabla de ejemplo como expander
            with st.expander("📋 Ver tabla de ejemplo para guiarte"):
                st.markdown("""
                <table class="example-table">
                    <thead>
                        <tr>
                            <th>Descripción</th>
                            <th>Valor</th>
                            <th>Deuda</th>
                            <th>Neto</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Inmueble 1</td>
                            <td>$80,000.00</td>
                            <td>$30,000.00</td>
                            <td>$50,000.00</td>
                        </tr>
                        <tr>
                            <td>Inmueble 2</td>
                            <td></td>
                            <td></td>
                            <td>$0.00</td>
                        </tr>
                        <tr>
                            <td>Automóvil 1</td>
                            <td>$15,000.00</td>
                            <td>$18,000.00</td>
                            <td>$(3,000.00)</td>
                        </tr>
                        <tr>
                            <td>Automóvil 2</td>
                            <td></td>
                            <td></td>
                            <td>$0.00</td>
                        </tr>
                        <tr>
                            <td>Muebles</td>
                            <td>$5,000.00</td>
                            <td>$1,500.00</td>
                            <td>$3,500.00</td>
                        </tr>
                        <tr>
                            <td>Joyas</td>
                            <td></td>
                            <td></td>
                            <td>$0.00</td>
                        </tr>
                        <tr>
                            <td>Arte</td>
                            <td></td>
                            <td></td>
                            <td>$0.00</td>
                        </tr>
                        <tr>
                            <td>Efectivo cuenta 1</td>
                            <td>$2,000.00</td>
                            <td></td>
                            <td>$2,000.00</td>
                        </tr>
                        <tr>
                            <td>Efectivo cuenta 2</td>
                            <td>$1,500.00</td>
                            <td></td>
                            <td>$1,500.00</td>
                        </tr>
                        <tr>
                            <td>Deudas por cobrar</td>
                            <td>$3,000.00</td>
                            <td></td>
                            <td>$3,000.00</td>
                        </tr>
                        <tr>
                            <td>Acciones</td>
                            <td></td>
                            <td></td>
                            <td>$0.00</td>
                        </tr>
                        <tr>
                            <td>Bonos o títulos valores</td>
                            <td></td>
                            <td></td>
                            <td>$0.00</td>
                        </tr>
                        <tr>
                            <td>Fondo de retiro</td>
                            <td>$30,000.00</td>
                            <td></td>
                            <td>$30,000.00</td>
                        </tr>
                        <tr>
                            <td>Bonos o derechos laborales</td>
                            <td></td>
                            <td></td>
                            <td>$0.00</td>
                        </tr>
                        <tr>
                            <td>Tarjeta de crédito 1</td>
                            <td></td>
                            <td>$6,500.00</td>
                            <td>$(6,500.00)</td>
                        </tr>
                        <tr>
                            <td>Tarjeta de crédito 2</td>
                            <td></td>
                            <td>$8,200.00</td>
                            <td>$(8,200.00)</td>
                        </tr>
                        <tr>
                            <td>Tarjeta de crédito 3</td>
                            <td></td>
                            <td></td>
                            <td>$0.00</td>
                        </tr>
                        <tr>
                            <td>Otra deuda 1</td>
                            <td></td>
                            <td>$4,700.00</td>
                            <td>$(4,700.00)</td>
                        </tr>
                        <tr>
                            <td>Otra deuda 2</td>
                            <td></td>
                            <td></td>
                            <td>$0.00</td>
                        </tr>
                        <tr>
                            <td>Otra deuda 3</td>
                            <td></td>
                            <td></td>
                            <td>$0.00</td>
                        </tr>
                        <tr>
                            <td>Otros</td>
                            <td></td>
                            <td></td>
                            <td>$0.00</td>
                        </tr>
                        <tr>
                            <td><strong>Total</strong></td>
                            <td><strong>$136,500.00</strong></td>
                            <td><strong>$68,900.00</strong></td>
                            <td><strong>$67,600.00</strong></td>
                        </tr>
                    </tbody>
                </table>
                """, unsafe_allow_html=True)
            
            st.markdown("""
            **Cómo diligenciar esta sección:**
            1. **Descripción**: Nombre del activo o pasivo
            2. **Valor**: Valor total del activo o monto total de la deuda
            3. **Deuda**: Para activos, la deuda asociada (ej: hipoteca)
            4. **Neto**: Diferencia entre Valor y Deuda (calculado automáticamente)
            
            Ejemplos:
            - Inmueble: Valor = precio de mercado, Deuda = saldo hipotecario
            - Automóvil: Valor = precio actual, Deuda = préstamo pendiente
            - Tarjetas: Valor = límite de crédito, Deuda = saldo adeudado
            """)
            
            # Definir items de activos y pasivos
            activos_items = [
                {"nombre": "Inmueble 1", "help": "Valor de mercado de tu primera propiedad"},
                {"nombre": "Inmueble 2", "help": "Valor de mercado de tu segunda propiedad"},
                {"nombre": "Automóvil 1", "help": "Valor actual de tu vehículo principal"},
                {"nombre": "Automóvil 2", "help": "Valor actual de tu segundo vehículo"},
                {"nombre": "Muebles", "help": "Valor estimado de muebles y enseres"},
                {"nombre": "Joyas", "help": "Valor estimado de joyas y artículos de valor"},
                {"nombre": "Arte", "help": "Valor estimado de obras de arte y colecciones"},
                {"nombre": "Efectivo cuenta 1", "help": "Saldo disponible en tu cuenta principal"},
                {"nombre": "Efectivo cuenta 2", "help": "Saldo disponible en cuentas secundarias"},
                {"nombre": "Deudas por cobrar", "help": "Dinero que te deben otras personas o empresas"},
                {"nombre": "Bonos o títulos valores", "help": "Valor de tus inversiones financieras"},
                {"nombre": "Fondo de retiro", "help": "Saldo acumulado en fondos de pensiones"},
                {"nombre": "Bonos o derechos laborales", "help": "Valor de prestaciones laborales"}
            ]
            
            pasivos_items = [
                {"nombre": "Tarjeta de crédito 1", "help": "Saldo pendiente en tu tarjeta principal"},
                {"nombre": "Tarjeta de crédito 2", "help": "Saldo pendiente en tarjetas secundarias"},
                {"nombre": "Tarjeta de crédito 3", "help": "Otras deudas con tarjetas de crédito"},
                {"nombre": "Otra deuda 1", "help": "Préstamos personales o de consumo"},
                {"nombre": "Otra deuda 2", "help": "Préstamos estudiantiles o educativos"},
                {"nombre": "Otra deuda 3", "help": "Otras obligaciones financieras"},
                {"nombre": "Otros", "help": "Cualquier otra deuda no clasificada"}
            ]
            
            # Inicializar valores
            if 'activos_values' not in st.session_state:
                st.session_state['activos_values'] = {item['nombre']: {"valor": 0.0, "deuda": 0.0} for item in activos_items}
            
            if 'pasivos_values' not in st.session_state:
                st.session_state['pasivos_values'] = {item['nombre']: {"valor": 0.0, "deuda": 0.0} for item in pasivos_items}
            
            # Tabla de activos con títulos de columna
            st.markdown("### Activos")
            
            # Encabezados de columna para activos
            cols = st.columns([3, 1, 1, 1])
            with cols[0]:
                st.markdown("**Descripción**")
            with cols[1]:
                st.markdown("**Valor ($)**")
            with cols[2]:
                st.markdown("**Deuda ($)**")
            with cols[3]:
                st.markdown("**Neto ($)**")
            
            activos_total = {"valor": 0.0, "deuda": 0.0, "neto": 0.0}
            
            for item in activos_items:
                cols = st.columns([3, 1, 1, 1])
                
                with cols[0]:
                    st.markdown(f"{item['nombre']}", unsafe_allow_html=True)
                    emoji_help_tooltip(item['help'])
                
                valor = cols[1].text_input(
                    f"Valor {item['nombre']}",
                    value=format_currency(st.session_state['activos_values'][item['nombre']]['valor']),
                    key=f"activo_valor_{item['nombre']}",
                    label_visibility="collapsed"
                )
                
                deuda = cols[2].text_input(
                    f"Deuda {item['nombre']}",
                    value=format_currency(st.session_state['activos_values'][item['nombre']]['deuda']),
                    key=f"activo_deuda_{item['nombre']}",
                    label_visibility="collapsed"
                )
                
                valor_parsed = parse_currency(valor)
                deuda_parsed = parse_currency(deuda)
                neto = valor_parsed - deuda_parsed
                
                cols[3].markdown(format_currency(neto))
                
                st.session_state['activos_values'][item['nombre']] = {
                    "valor": valor_parsed,
                    "deuda": deuda_parsed
                }
                
                activos_total["valor"] += valor_parsed
                activos_total["deuda"] += deuda_parsed
                activos_total["neto"] += neto
            
            # Tabla de pasivos con títulos de columna
            st.markdown("### Pasivos")
            
            # Encabezados de columna para pasivos
            cols = st.columns([3, 1, 1, 1])
            with cols[0]:
                st.markdown("**Descripción**")
            with cols[1]:
                st.markdown("**Valor ($)**")
            with cols[2]:
                st.markdown("**Deuda ($)**")
            with cols[3]:
                st.markdown("**Neto ($)**")
            
            pasivos_total = {"valor": 0.0, "deuda": 0.0, "neto": 0.0}
            
            for item in pasivos_items:
                cols = st.columns([3, 1, 1, 1])
                
                with cols[0]:
                    st.markdown(f"{item['nombre']}", unsafe_allow_html=True)
                    emoji_help_tooltip(item['help'])
                
                valor = cols[1].text_input(
                    f"Valor {item['nombre']}",
                    value=format_currency(st.session_state['pasivos_values'][item['nombre']]['valor']),
                    key=f"pasivo_valor_{item['nombre']}",
                    label_visibility="collapsed"
                )
                
                deuda = cols[2].text_input(
                    f"Deuda {item['nombre']}",
                    value=format_currency(st.session_state['pasivos_values'][item['nombre']]['deuda']),
                    key=f"pasivo_deuda_{item['nombre']}",
                    label_visibility="collapsed"
                )
                
                valor_parsed = parse_currency(valor)
                deuda_parsed = parse_currency(deuda)
                neto = -(valor_parsed - deuda_parsed)
                
                cols[3].markdown(format_currency(neto))
                
                st.session_state['pasivos_values'][item['nombre']] = {
                    "valor": valor_parsed,
                    "deuda": deuda_parsed
                }
                
                pasivos_total["valor"] += valor_parsed
                pasivos_total["deuda"] += deuda_parsed
                pasivos_total["neto"] += neto
            
            # Mostrar totales
            st.markdown("### Resumen Financiero")
            patrimonio_neto = activos_total['neto'] + pasivos_total['neto']
            
            st.markdown(f"""
            - **Total Valor Activos:** {format_currency(activos_total['valor'])}
            - **Total Deuda Activos:** {format_currency(activos_total['deuda'])}
            - **Total Activos Netos:** {format_currency(activos_total['neto'])}
            - **Total Pasivos:** {format_currency(pasivos_total['neto'])}
            - **Patrimonio Neto:** {format_currency(patrimonio_neto)}
            """)
            
            # Flujo de caja mensual
            st.subheader("💸 Flujo de Caja Mensual")
            
            # Inicializar valores
            if 'ingresos_values' not in st.session_state:
                st.session_state['ingresos_values'] = {
                    "Ingresos mensuales adulto 1": {"valor": 0.0},
                    "Ingresos mensuales adulto 2": {"valor": 0.0},
                    "Otros ingresos": {"valor": 0.0}
                }
            
            if 'gastos_values' not in st.session_state:
                st.session_state['gastos_values'] = {
                    "Gasto de Inmueble 1": {"valor": 0.0},
                    "Gasto de Inmueble 2": {"valor": 0.0},
                    "Alimentación": {"valor": 0.0},
                    "Educación": {"valor": 0.0},
                    "Transporte": {"valor": 0.0},
                    "Salud": {"valor": 0.0},
                    "Entretenimiento": {"valor": 0.0},
                    "Servicios públicos": {"valor": 0.0},
                    "Seguros": {"valor": 0.0},
                    "Otros gastos": {"valor": 0.0}
                }
            
            # Ingresos
            st.markdown("#### Ingresos")
            ingresos_total = 0.0
            
            for item, data in st.session_state['ingresos_values'].items():
                value = st.text_input(
                    item,
                    value=format_currency(data['valor']),
                    key=f"ingreso_{item}"
                )
                parsed_value = parse_currency(value)
                st.session_state['ingresos_values'][item]['valor'] = parsed_value
                ingresos_total += parsed_value
            
            # Gastos
            st.markdown("#### Gastos")
            gastos_total = 0.0
            
            for item, data in st.session_state['gastos_values'].items():
                value = st.text_input(
                    item,
                    value=format_currency(data['valor']),
                    key=f"gasto_{item}"
                )
                parsed_value = parse_currency(value)
                st.session_state['gastos_values'][item]['valor'] = parsed_value
                gastos_total += parsed_value
            
            # Calcular saldo mensual
            saldo_mensual = ingresos_total - gastos_total
            st.markdown(f"""
            **Resumen Flujo de Caja:**
            - **Total Ingresos:** {format_currency(ingresos_total)}
            - **Total Gastos:** {format_currency(gastos_total)}
            - **Saldo Mensual:** {format_currency(saldo_mensual)}
            """)
            
            if st.button("Analizar mi situación financiera para bienes raíces"):
                analisis = analizar_situacion_financiera(
                    ingresos_total, gastos_total, 
                    activos_total['neto'], abs(pasivos_total['neto'])
                )
                st.session_state['reporte_data']['finanzas'] = {
                    'ingresos': ingresos_total,
                    'gastos': gastos_total,
                    'activos': activos_total['neto'],
                    'pasivos': abs(pasivos_total['neto'])
                }
                st.session_state['reporte_data']['analisis'].update({
                    'resumen': analisis['resumen'],
                    'perfil_inversion': analisis['perfil_inversion']
                })
                
                plan = generar_plan_trabajo(
                    ingresos_total, gastos_total, 
                    activos_total['neto'], abs(pasivos_total['neto'])
                )
                st.subheader("📝 Plan de Trabajo para Inversión en Bienes Raíces")
                st.write(plan)
                st.session_state['reporte_data']['analisis']['plan_trabajo'] = plan
    
    # Paso 3: Plan de inversión
    if 'usuario_id' in st.session_state and 'reporte_data' in st.session_state and 'finanzas' in st.session_state['reporte_data']:
        with st.container():
            st.subheader("📈 Plan de Inversión en Bienes Raíces")
            
            with st.expander("💡 ESTRATEGIAS PARA INVERTIR EN BIENES RAÍCES"):
                st.markdown("""
                1. **Propiedades en Remate Bancario**  
                Los bancos venden propiedades embargadas por debajo del valor de mercado.
                
                2. **Compra con Opción de Compra**  
                Negocia el derecho a comprar la propiedad en el futuro mientras la alquilas.
                
                3. **Co-Inversiones**  
                Asóciate con otros inversionistas para adquirir propiedades.
                
                4. **Propiedades con Dueño Directo**  
                Encuentra mejores negocios tratando directamente con dueños.
                
                5. **Rehabilitación de Propiedades**  
                Compra propiedades que necesiten reparaciones, haz mejoras y véndelas con ganancia.
                """)
            
            objetivos = st.text_input("Objetivos específicos con bienes raíces", 
                                    "Generar ingresos pasivos a través de propiedades en alquiler")
            horizonte = st.selectbox("Horizonte de inversión", 
                                   ["Corto plazo (1-3 años)", "Mediano plazo (3-5 años)", "Largo plazo (5+ años)"])
            estrategias = st.multiselect("Estrategias de interés", 
                                       ["Alquiler residencial", "Alquiler comercial", "Rehabilitación y venta", 
                                        "Terrenos", "Remates bancarios", "Rentas vacacionales", "Co-inversiones"])
            
            if st.button("Generar estrategia personalizada"):
                st.session_state['plan_inversion'] = (objetivos, horizonte, ", ".join(estrategias))
                ingresos = st.session_state['reporte_data']['finanzas']['ingresos']
                gastos = st.session_state['reporte_data']['finanzas']['gastos']
                activos = st.session_state['reporte_data']['finanzas']['activos']
                pasivos = st.session_state['reporte_data']['finanzas']['pasivos']
                
                analisis_ia = generar_plan_trabajo(ingresos, gastos, activos, pasivos)
                st.write(analisis_ia)
                st.session_state['reporte_data']['analisis']['analisis_ia'] = analisis_ia
    
    # Paso 4: Plan de retiro
    if 'usuario_id' in st.session_state and 'reporte_data' in st.session_state and 'finanzas' in st.session_state['reporte_data']:
        with st.container():
            st.subheader("👴 Plan de Retiro con Bienes Raíces")
            
            col1, col2 = st.columns(2)
            edad_actual = col1.number_input("Tu edad actual", min_value=18, max_value=100, value=30)
            edad_retiro = col2.number_input("Edad de retiro deseada", min_value=edad_actual+1, max_value=100, value=65)
            
            ingresos_retiro = parse_currency(st.text_input("Ingresos anuales esperados durante el retiro ($)", value="$40,000"))
            gastos_retiro = parse_currency(st.text_input("Gastos anuales esperados durante el retiro ($)", value="$30,000"))
            ahorros_retiro = parse_currency(st.text_input("Ahorros actuales para el retiro ($)", value="$10,000"))
            
            if st.button("Calcular proyección de retiro con bienes raíces"):
                ingresos = st.session_state['reporte_data']['finanzas']['ingresos']
                gastos = st.session_state['reporte_data']['finanzas']['gastos']
                activos = st.session_state['reporte_data']['finanzas']['activos']
                pasivos = st.session_state['reporte_data']['finanzas']['pasivos']
                
                flujo_caja = ingresos - gastos
                patrimonio_neto = activos - pasivos
                
                analisis = analizar_proyeccion_retiro(
                    edad_actual, edad_retiro, 
                    ingresos_retiro, gastos_retiro, 
                    ahorros_retiro, patrimonio_neto, flujo_caja
                )
                st.session_state['reporte_data']['analisis']['proyeccion_retiro'] = analisis
                
                st.write(analisis['analisis'])
    
    # Descargar PDF
    if 'reporte_data' in st.session_state and st.session_state['reporte_data']['usuario']:
        if st.button("📄 Descargar Reporte Completo en PDF"):
            pdf_bytes = generar_pdf(
                st.session_state['reporte_data']['usuario'],
                st.session_state['reporte_data']['finanzas'],
                st.session_state['reporte_data']['analisis']
            )
            
            st.success("Reporte generado con éxito!")
            b64 = base64.b64encode(pdf_bytes).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="reporte_bienes_raices.pdf">Haz clic aquí para descargar</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    # Pie de página
    st.markdown("---")
    st.markdown("""
    **📌 Próximos Pasos**
    - Revisa nuestro [canal de YouTube](https://www.youtube.com/@carlosdevis)
    - Inscríbete en nuestro [ciclo educativo](https://landing.tallerdebienesraices.com/registro-ciclo-educativo/)
    - Asiste a nuestros eventos presenciales y online
    - Comienza con una propiedad pequeña y escala progresivamente
    """)

if __name__ == "__main__":
    main()