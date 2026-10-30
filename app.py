"""
SaludCerca · versión Streamlit Optimizada para Móviles
======================================================
Encuentra el centro de salud más cercano que está abierto ahora.
Diseñado para ser intuitivo, con alto contraste y botones grandes.
"""

from __future__ import annotations

import datetime as dt
import math
import re

import pandas as pd
import requests
import streamlit as st

try:
    from streamlit_geolocation import streamlit_geolocation
    GEO_DISPONIBLE = True
except Exception:
    GEO_DISPONIBLE = False

# --------------------------------------------------------------------------
# Configuración general
# --------------------------------------------------------------------------
RESOURCE_ID = "2c44d782-3365-44e3-aefb-2c8b8363a1bc"
API_URL = "https://datos.gob.cl/api/3/action/datastore_search"

AZUL = "#1B3A5C"
TINTA = "#132A42"
ORO = "#C6A15B"
PAPEL = "#F7F5F0"
GRIS = "#5B6B7A"

TIPOS_CORTOS = {
    "Servicio de Atención Primaria de Urgencia (SAPU)": "SAPU",
    "Servicio de Atención Primaria de Urgencia de Alta Resolutividad (SAR)": "SAR",
    "Servicio de Urgencia Rural (SUR)": "SUR",
    "Centro de Salud Familiar (CESFAM)": "CESFAM",
    "Centro Comunitario de Salud Familiar (CECOSF)": "CECOSF",
    "Posta de Salud Rural (PSR)": "Posta rural",
    "Centro de Salud Privado": "Centro privado",
    "Centro  Diagnóstico y Tratamiento Privado": "Centro diagnóstico",
    "Centro Comunitario de Salud Mental  (COSAM)": "COSAM",
    "Sala  Externa de Toma de Muestras (SETM)": "Toma de muestras",
    "Unidad de Procedimientos Móvil": "Unidad móvil",
    "Unidad de Salud Funcionarios": "Unidad de salud",
    "Dirección Servicio de Salud": "Dirección SS",
    "Programa de Reparación y Atención Integral de Salud (PRAIS)": "PRAIS",
    "Centro de Diálisis": "Centro de diálisis",
    "Laboratorio Clínico": "Laboratorio",
    "Clínica Dental": "Clínica dental",
    "Centro de Especialidades": "Especialidades",
    "Centro de Especialidades de Atención Primaria (CEAP)": "Especialidades APS",
    "Centro Corporación para la Nutrición Infantil (CONIN)": "CONIN",
    "Centro de Rehabilitación": "Rehabilitación",
    "Centro de Salud Comunitario para Personas con Demencia": "Demencia",
    "Centro de Regulación Médica de las Urgencias (SAMU)": "Regulador SAMU",
    "Consultorio General Rural (CGR)": "Consultorio rural",
    "Consultorio General Urbano (CGU)": "Consultorio urbano",
    "Centro de Salud Comunitario": "Centro comunitario",
    "Centro de Regulación Médica de las Urgencias": "Regulador SAMU",
}

REGIONES = {
    1: "Tarapacá", 2: "Antofagasta", 3: "Atacama", 4: "Coquimbo",
    5: "Valparaíso", 6: "O'Higgins", 7: "Maule", 8: "Biobío",
    9: "La Araucanía", 10: "Los Lagos", 11: "Aysén", 12: "Magallanes",
    13: "Metropolitana", 14: "Los Ríos", 15: "Arica y Parinacota", 16: "Ñuble",
}

st.set_page_config(
    page_title="SaludCerca",
    page_icon="📍",
    layout="centered", # Centrado es mejor para móviles
    initial_sidebar_state="collapsed", # Eliminamos la barra lateral
)

# Forzamos colores para evitar que el "modo oscuro" del celular arruine el contraste
st.markdown(
    f"""
    <style>
      /* Forzar fondo y color de texto global */
      .stApp {{ background-color: {PAPEL} !important; color: {TINTA} !important; }}
      
      /* Tipografía clara y legible */
      h1, h2, h3 {{ font-family: system-ui, -apple-system, sans-serif !important; color: {TINTA} !important; font-weight: 700; }}
      p, span, div {{ font-family: system-ui, -apple-system, sans-serif !important; color: {TINTA} !important; }}
      
      /* Cabecera */
      .cabecera {{ border-bottom: 4px solid {ORO}; padding-bottom: 1rem; margin-bottom: 1.5rem; text-align: center; }}
      .cabecera .marca {{ font-size: 0.8rem; letter-spacing: 0.1em; text-transform: uppercase; color: {GRIS} !important; margin: 0; }}
      .cabecera h1 {{ font-size: 2rem; margin: 0.5rem 0; line-height: 1.1; }}
      
      /* Tarjetas de resultados */
      .tarjeta-cercana {{ background: #FFFFFF; border: 2px solid {AZUL}; border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(19,42,66,0.1); }}
      .tarjeta-cercana h3 {{ font-size: 1.4rem; margin: 0 0 0.5rem 0; color: {AZUL} !important; }}
      .tarjeta-cercana .dir {{ font-size: 1.1rem; color: #3B4E62 !important; margin-bottom: 0.5rem; }}
      .tarjeta-cercana .estado {{ font-size: 1rem; color: {GRIS} !important; font-weight: bold; }}
      .cinta {{ background: {ORO}; color: #251B06 !important; font-size: 0.8rem; font-weight: bold; padding: 0.3rem 0.8rem; border-radius: 6px; display: inline-block; margin-bottom: 0.8rem; }}
      
      /* Tarjetas secundarias */
      .tarjeta-secundaria {{ background: #FFFFFF; border: 1px solid #E4E1D9; border-radius: 8px; padding: 1rem; margin-bottom: 0.8rem; display: flex; flex-direction: column; }}
      .tarjeta-secundaria h4 {{ font-size: 1.1rem; margin: 0 0 0.3rem 0; color: {TINTA} !important; }}
      .tarjeta-secundaria p {{ font-size: 0.9rem; margin: 0; color: {GRIS} !important; }}
      
      /* Botones más grandes */
      .stButton > button, .stLinkButton > a {{ width: 100%; border-radius: 8px; font-size: 1.1rem !important; padding: 0.8rem !important; font-weight: bold !important; }}
      .stLinkButton > a {{ background-color: {AZUL} !important; color: white !important; }}
      
      /* Ocultar cosas innecesarias de Streamlit */
      #MainMenu {{visibility: hidden;}}
      footer {{visibility: hidden;}}
      header {{visibility: hidden;}}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# Datos
# --------------------------------------------------------------------------
@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def cargar_catastro() -> tuple[pd.DataFrame, str]:
    registros: list[dict] = []
    offset = 0
    total = None
    while True:
        respuesta = requests.get(API_URL, params={"resource_id": RESOURCE_ID, "limit": 1000, "offset": offset}, timeout=40)
        respuesta.raise_for_status()
        resultado = respuesta.json()["result"]
        if total is None:
            total = resultado["total"]
        lote = resultado["records"]
        if not lote:
            break
        registros.extend(lote)
        offset += len(lote)
        if offset >= total:
            break
    df = pd.DataFrame(registros)
    df = _normalizar(df)
    sello = ahora_en_chile().strftime("%d-%m-%Y %H:%M")
    return df, sello

def _acortar_tipo(tipo: str) -> str:
    texto = TIPOS_CORTOS.get(tipo, tipo)
    return texto if len(texto) <= 22 else texto[:21].rstrip(" ,.") + "…"

def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["EstadoFuncionamiento"] = df["EstadoFuncionamiento"].fillna("").str.lower()
    df = df[df["EstadoFuncionamiento"].str.contains("vigente")]
    df["RegionCodigo"] = pd.to_numeric(df["RegionCodigo"], errors="coerce")
    df["region"] = df["RegionCodigo"].map(REGIONES)
    df["urgencia"] = df["TieneServicioUrgencia"].fillna("").str.strip().str.upper().eq("SI")
    df["complejidad"] = df["NivelComplejidadEstabGlosa"].fillna("").replace({"Baja Complejidad": "Baja", "Mediana Complejidad": "Media", "Alta Complejidad": "Alta", "No Aplica": "", "Pendiente": ""})
    df["lat"] = pd.to_numeric(df["Latitud"], errors="coerce")
    df["lon"] = pd.to_numeric(df["Longitud"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])
    df = df[df["lat"].between(-56.9, -17.0) & df["lon"].between(-76.9, -66.0)]
    partes = df["TipoViaGlosa"].fillna("").str.strip() + " " + df["NombreVia"].fillna("").str.strip() + " " + df["Numero"].fillna("").astype(str).str.strip()
    df["direccion"] = partes.str.replace(r"\s+", " ", regex=True).str.strip()
    df["fono"] = df["TelefonoMovil_TelefonoFijo"].fillna("").astype(str).str.replace(r"[^0-9]", "", regex=True)
    df["comuna"] = df["ComunaGlosa"].fillna("").str.strip()
    df["nombre"] = df["EstablecimientoGlosa"].fillna("").str.strip()
    df["tipo"] = df["TipoEstablecimientoGlosa"].fillna("").str.strip()
    df["dependencia"] = df["DependenciaAdministrativa"].fillna("").str.strip()
    df["tipo_corto"] = df["tipo"].map(_acortar_tipo)
    return df[df["nombre"].ne("")].reset_index(drop=True)

def ahora_en_chile() -> dt.datetime:
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/Santiago"))
    except Exception:
        return dt.datetime.utcnow() - dt.timedelta(hours=4)

def esta_abierto(urgencia: bool, ahora: dt.datetime) -> tuple[bool, str, str]:
    if urgencia:
        return True, "Atiende día y noche (Urgencia)", "Urgencia 24/7"
    habil = ahora.weekday() < 5 and 8 <= ahora.hour < 17
    if habil:
        return True, "Abierto ahora (Horario hábil)", "Abierto"
    return False, "Cerrado ahora", "Cerrado"

def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radio = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    return 2 * radio * math.asin(math.sqrt(a))

def formato_km(km: float) -> str:
    if km < 1:
        return f"{round(km * 1000)} metros"
    return f"{km:.1f} km".replace(".", ",")

def tiempo_auto(km: float) -> str:
    minutos = round(km / 45 * 60) + 2
    if minutos < 60:
        return f"≈ {minutos} min en auto"
    return f"≈ {minutos // 60} h {minutos % 60} min en auto"

# --------------------------------------------------------------------------
# Interfaz Principal
# --------------------------------------------------------------------------
st.markdown(
    """
    <div class="cabecera">
      <p class="marca">Datos abiertos de salud · Chile</p>
      <h1>¿A dónde la llevo <em>ahora</em>?</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    with st.spinner("Buscando centros de salud..."):
        df, sello = cargar_catastro()
except Exception as error:
    st.error(f"Error al descargar datos: {error}")
    st.stop()

if df.empty:
    st.warning("No hay datos disponibles. Intenta más tarde.")
    st.stop()

ahora = ahora_en_chile()
df["abierto"], df["estado_texto"], df["estado_corto"] = zip(*[esta_abierto(u, ahora) for u in df["urgencia"]])

# --- UBICACIÓN (Todo en pantalla principal, sin menús ocultos) ---
st.markdown("### 📍 Paso 1: ¿Desde dónde buscas?")

# Botón de geolocalización gigante
origen = None
if GEO_DISPONIBLE:
    st.caption("Toca el botón azul para usar tu ubicación actual. Acepta el permiso.")
    dato = streamlit_geolocation()
    if dato and dato.get("latitude") is not None:
        origen = (float(dato["latitude"]), float(dato["longitude"]), "Tu ubicación actual")
        st.success("¡Ubicación obtenida!")

if origen is None:
    # Alternativa manual si no hay GPS o no quiere dar permiso
    st.markdown("O si prefieres, elige tu comuna:")
    comunas = sorted(df["comuna"].unique())
    comuna_sel = st.selectbox("Comuna", comunas, index=comunas.index("Santiago") if "Santiago" in comunas else 0, label_visibility="collapsed")
    
    del_lugar = df[df["comuna"] == comuna_sel]
    if not del_lugar.empty:
        origen = (float(del_lugar["lat"].mean()), float(del_lugar["lon"].mean()), f"Centro de {comuna_sel}")

st.markdown("---")
st.markdown("### 🔍 Paso 2: Filtros")

col1, col2 = st.columns(2)
with col1:
    radio = st.slider("Distancia máxima", 5, 100, 30, step=5, format="%d km")
with col2:
    solo_urgencia = st.checkbox("Solo Urgencias 24/7", value=True)

# --- RESULTADOS ---
if origen is not None:
    lat0, lon0, etiqueta = origen
    base = df[df["urgencia"]] if solo_urgencia else df
    candidatos = base[base["abierto"]].copy()
    
    if not candidatos.empty:
        candidatos["km"] = [distancia_km(lat0, lon0, la, lo) for la, lo in zip(candidatos["lat"], candidatos["lon"])]
        candidatos = candidatos[candidatos["km"] <= radio].sort_values("km")

    if candidatos.empty:
        st.warning(f"No encontramos centros abiertos a menos de {radio} km. Prueba aumentando la distancia.")
    else:
        st.markdown(f"### 🏥 {len(candidatos)} centros abiertos cerca")
        
        # El más cercano (Tarjeta Grande)
        primero = candidatos.iloc[0]
        st.markdown(
            f"""
            <div class="tarjeta-cercana">
              <span class="cinta">EL MÁS CERCANO ABIERTO</span>
              <h3>{primero['nombre']}</h3>
              <p class="dir">📍 {primero['direccion'] or 'Sin dirección'} · {primero['comuna']}</p>
              <p class="estado">🟢 {primero['estado_texto']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        # Botones de acción gigantes
        st.markdown(f"**A {formato_km(primero['km'])}** ({tiempo_auto(primero['km'])})")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if primero["fono"]:
                st.link_button("📞 LLAMAR", f"tel:+56{primero['fono']}", use_container_width=True)
            else:
                st.button("📞 Sin teléfono", disabled=True, use_container_width=True)
        with col_btn2:
            st.link_button("🗺️ CÓMO LLEGAR", f"https://www.google.com/maps/dir/?api=1&destination={primero['lat']},{primero['lon']}", use_container_width=True)

        st.markdown("---")
        
        # Lista de siguientes opciones (Tarjetas pequeñas, sin tablas)
        if len(candidatos) > 1:
            st.markdown("#### Otras opciones cercanas")
            for _, fila in candidatos.iloc[1:6].iterrows(): # Mostramos máximo 5 más para no saturar
                st.markdown(
                    f"""
                    <div class="tarjeta-secundaria">
                      <h4>{fila['nombre']}</h4>
                      <p>📍 {fila['comuna']} · {formato_km(fila['km'])}</p>
                      <p>🟢 {fila['estado_corto']} | {fila['tipo_corto']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                col_a, col_b = st.columns(2)
                with col_a:
                    if fila["fono"]:
                        st.link_button("Llamar", f"tel:+56{fila['fono']}", key=f"tel_{fila['lat']}_{fila['lon']}", use_container_width=True)
                with col_b:
                    st.link_button("Ruta", f"https://www.google.com/maps/dir/?api=1&destination={fila['lat']},{fila['lon']}", key=f"map_{fila['lat']}_{fila['lon']}", use_container_width=True)
                st.write("") # Espaciador

        # Mapa (oculto en un menú desplegable para no ocupar toda la pantalla)
        with st.expander("🗺️ Ver mapa de resultados"):
            mapa = pd.DataFrame({"lat": [lat0] + list(candidatos["lat"].head(10)), "lon": [lon0] + list(candidatos["lon"].head(10))})
            st.map(mapa, zoom=11, use_container_width=True)

        # Botón de descarga al final
        st.download_button(
            "⬇️ Descargar lista (CSV)",
            candidatos[["nombre", "comuna", "direccion", "fono", "km"]].to_csv(index=False).encode("utf-8-sig"),
            file_name="saludcerca.csv",
            mime="text/csv",
            use_container_width=True
        )

st.markdown("---")
st.caption(f"Datos actualizados el {sello}. Fuente: Datos Abiertos MINSAL. No reemplaza la evaluación médica. Llama al 131 en emergencias.")
