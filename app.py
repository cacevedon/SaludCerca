"""
SaludCerca · versión Streamlit
================================
Encuentra el centro de salud más cercano que está abierto ahora.

Los datos se descargan en vivo desde la API de Datos Abiertos del Gobierno de
Chile (catastro de establecimientos de salud) y se limpian en memoria. No hay
base de datos ni almacenamiento de datos personales.

Autoría: Cristian Acevedo, Rodrigo Gómez, Marcelo Araya, Nathaly Donoso
"""

from __future__ import annotations

import datetime as dt
import math
import re

import pandas as pd
import requests
import streamlit as st

try:  # componente de geolocalización del navegador
    from streamlit_geolocation import streamlit_geolocation

    GEO_DISPONIBLE = True
except Exception:  # si no está instalado, la app sigue funcionando por comuna
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
    page_title="SaludCerca · ¿a dónde la llevo ahora?",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
    <style>
      .stApp {{ background: {PAPEL}; }}
      h1, h2, h3 {{ font-family: Georgia, 'Times New Roman', serif; color: {TINTA}; }}
      .cabecera {{ border-bottom: 4px solid {ORO}; padding-bottom: .8rem; margin-bottom: 1.6rem; }}
      .cabecera .marca {{ font-size: .72rem; letter-spacing: .18em; text-transform: uppercase;
                          color: {GRIS}; margin: 0; }}
      .cabecera h1 {{ font-size: 2.4rem; margin: .2rem 0 .1rem; font-weight: 400; }}
      .cabecera h1 em {{ color: {AZUL}; }}
      .tarjeta {{ background: #FFFDF8; border: 1px solid #E4E1D9; border-radius: 4px;
                  padding: 1.3rem 1.4rem; box-shadow: 0 8px 20px -18px rgba(19,42,66,.5); }}
      .tarjeta .cinta {{ background: {ORO}; color: #251B06; font-size: .68rem; font-weight: 700;
                         letter-spacing: .16em; text-transform: uppercase; padding: .3rem .8rem;
                         border-radius: 3px; display: inline-block; }}
      .tarjeta h3 {{ font-size: 1.6rem; margin: .7rem 0 .3rem; }}
      .tarjeta .dir {{ color: #3B4E62; margin: 0 0 .5rem; }}
      .tarjeta .estado {{ font-size: .9rem; color: {GRIS}; }}
      .dato {{ font-family: Georgia, serif; font-size: 1.5rem; color: {AZUL}; }}
      .nota {{ font-size: .8rem; color: {GRIS}; }}
      div[data-testid="stMetricValue"] {{ font-family: Georgia, serif; color: {AZUL}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# Datos
# --------------------------------------------------------------------------

@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def cargar_catastro() -> tuple[pd.DataFrame, str]:
    """Descarga el catastro completo paginando la API y lo deja limpio."""
    registros: list[dict] = []
    offset = 0
    total = None

    while True:
        respuesta = requests.get(
            API_URL,
            params={"resource_id": RESOURCE_ID, "limit": 1000, "offset": offset},
            timeout=40,
        )
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
    """Nombre del tipo de recinto en versión corta, para que la tabla no se estire."""
    texto = TIPOS_CORTOS.get(tipo, tipo)
    return texto if len(texto) <= 22 else texto[:21].rstrip(" ,.") + "…"


def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """Deja el catastro utilizable: vigentes, con coordenadas y datos legibles."""
    if df.empty:
        return df

    df = df.copy()
    df["EstadoFuncionamiento"] = df["EstadoFuncionamiento"].fillna("").str.lower()
    df = df[df["EstadoFuncionamiento"].str.contains("vigente")]

    # regiones: se resuelven por código para no duplicar por variantes de escritura
    df["RegionCodigo"] = pd.to_numeric(df["RegionCodigo"], errors="coerce")
    df["region"] = df["RegionCodigo"].map(REGIONES)

    # urgencia
    df["urgencia"] = (
        df["TieneServicioUrgencia"].fillna("").str.strip().str.upper().eq("SI")
    )

    # complejidad en palabras simples
    df["complejidad"] = (
        df["NivelComplejidadEstabGlosa"].fillna("")
        .replace({
            "Baja Complejidad": "Baja",
            "Mediana Complejidad": "Media",
            "Alta Complejidad": "Alta",
            "No Aplica": "",
            "Pendiente": "",
        })
    )

    # coordenadas
    df["lat"] = pd.to_numeric(df["Latitud"], errors="coerce")
    df["lon"] = pd.to_numeric(df["Longitud"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])
    df = df[
        df["lat"].between(-56.9, -17.0) & df["lon"].between(-76.9, -66.0)
    ]

    # dirección legible
    partes = (
        df["TipoViaGlosa"].fillna("").str.strip()
        + " " + df["NombreVia"].fillna("").str.strip()
        + " " + df["Numero"].fillna("").astype(str).str.strip()
    )
    df["direccion"] = partes.str.replace(r"\s+", " ", regex=True).str.strip()

    # teléfono solo con dígitos
    df["fono"] = (
        df["TelefonoMovil_TelefonoFijo"].fillna("")
        .astype(str)
        .str.replace(r"[^0-9]", "", regex=True)
    )

    df["comuna"] = df["ComunaGlosa"].fillna("").str.strip()
    df["nombre"] = df["EstablecimientoGlosa"].fillna("").str.strip()
    df["tipo"] = df["TipoEstablecimientoGlosa"].fillna("").str.strip()
    df["dependencia"] = df["DependenciaAdministrativa"].fillna("").str.strip()
    df["tipo_corto"] = df["tipo"].map(_acortar_tipo)

    return df[df["nombre"].ne("")].reset_index(drop=True)


def ahora_en_chile() -> dt.datetime:
    """Hora local de Chile, con o sin zoneinfo disponible."""
    try:
        from zoneinfo import ZoneInfo

        return dt.datetime.now(ZoneInfo("America/Santiago"))
    except Exception:  # entornos sin tzdata: aproximación de invierno
        return dt.datetime.utcnow() - dt.timedelta(hours=4)


def esta_abierto(urgencia: bool, ahora: dt.datetime) -> tuple[bool, str, str]:
    """Regla explícita: urgencia = día y noche; resto = horario hábil.

    Devuelve (abierto, texto_largo_para_la_ficha, texto_corto_para_la_tabla).
    """
    if urgencia:
        return True, "Urgencia declarada · atiende día y noche", "Urgencia 24/7"
    habil = ahora.weekday() < 5 and 8 <= ahora.hour < 17
    if habil:
        return True, "Horario hábil estimado (lun a vie, 08:00–17:00)", "Horario hábil"
    return False, "Fuera de horario hábil", "Cerrado"


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en línea recta entre dos coordenadas (Haversine)."""
    radio = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return 2 * radio * math.asin(math.sqrt(a))


def formato_km(km: float) -> str:
    if km < 1:
        return f"{round(km * 1000)} m"
    return f"{km:.1f} km".replace(".", ",")


def tiempo_auto(km: float) -> str:
    minutos = round(km / 45 * 60) + 2
    if minutos < 60:
        return f"≈ {minutos} min"
    return f"≈ {minutos // 60} h {minutos % 60} min"


# --------------------------------------------------------------------------
# Barra lateral
# --------------------------------------------------------------------------

def ubicacion_desde_parametros() -> tuple[float, float] | None:
    """Permite abrir la app con ?lat=..&lon=.. (útil para probar o compartir)."""
    try:
        params = st.query_params
    except Exception:  # versiones antiguas de Streamlit
        params = st.experimental_get_query_params()
        params = {k: v[0] for k, v in params.items()}

    try:
        return float(params["lat"]), float(params["lon"])
    except Exception:
        return None


def ubicacion_geolocalizada() -> tuple[float, float, str] | None:
    """Pide la ubicación al navegador con un botón. Devuelve None si no hay permiso."""
    if not GEO_DISPONIBLE:
        return None

    st.sidebar.caption(
        "Pulsa el botón de ubicación y acepta el permiso del navegador. "
        "Si aparece en inglés, es «Get Location». La ubicación se usa solo en tu sesión."
    )
    try:
        dato = streamlit_geolocation()
    except Exception:
        return None

    if not dato or dato.get("latitude") is None:
        return None

    precision = dato.get("accuracy")
    if precision:
        st.sidebar.caption(f"Ubicación obtenida (precisión ±{int(precision)} m).")
    return float(dato["latitude"]), float(dato["longitude"]), "Tu ubicación actual"


def panel_ubicacion(df: pd.DataFrame) -> tuple[float, float, str] | None:
    """Alternativa manual: comuna o coordenadas pegadas."""
    metodo = st.sidebar.radio(
        "Método",
        ["Elegir comuna", "Pegar coordenadas"],
        label_visibility="collapsed",
        horizontal=True,
    )

    if metodo == "Elegir comuna":
        comunas = sorted(df["comuna"].unique())
        comuna = st.sidebar.selectbox("Comuna", comunas, index=comunas.index("Santiago") if "Santiago" in comunas else 0)
        del_lugar = df[df["comuna"] == comuna]
        if del_lugar.empty:
            return None
        return (
            float(del_lugar["lat"].mean()),
            float(del_lugar["lon"].mean()),
            f"Centro de {comuna}",
        )

    texto = st.sidebar.text_input(
        "Coordenadas",
        placeholder="-33.45, -70.66",
        help="Pégalas desde Google Maps: primero latitud, luego longitud.",
    )
    numeros = re.findall(r"-?\d+(?:[.,]\d+)?", texto or "")
    if len(numeros) >= 2:
        try:
            lat = float(numeros[0].replace(",", "."))
            lon = float(numeros[1].replace(",", "."))
            if -56.9 <= lat <= -17.0 and -76.9 <= lon <= -66.0:
                return lat, lon, "Coordenadas ingresadas"
            st.sidebar.error("Esas coordenadas no están en Chile continental.")
        except ValueError:
            st.sidebar.error("No pude leer las coordenadas.")
    return None


# --------------------------------------------------------------------------
# Interfaz
# --------------------------------------------------------------------------

st.markdown(
    """
    <div class="cabecera">
      <p class="marca">Datos abiertos de salud · Chile</p>
      <h1>¿A dónde la llevo <em>ahora</em>?</h1>
      <p class="nota">El centro de salud abierto más cercano, según tu ubicación y el catastro público del MINSAL.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    with st.spinner("Descargando el catastro de establecimientos…"):
        df, sello = cargar_catastro()
except Exception as error:  # noqa: BLE001
    st.error(f"No pude descargar el catastro: {error}")
    st.stop()

if df.empty:
    st.warning("El catastro llegó vacío. Intenta recargar en unos minutos.")
    st.stop()

ahora = ahora_en_chile()
df["abierto"], df["estado_texto"], df["estado_corto"] = zip(
    *[esta_abierto(u, ahora) for u in df["urgencia"]]
)

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    enlace = ubicacion_desde_parametros()
    if enlace:
        origen = (enlace[0], enlace[1], "Coordenadas del enlace")
        st.caption("Ubicación tomada del enlace compartido.")
    else:
        if GEO_DISPONIBLE:
            st.sidebar.markdown("### ¿Desde dónde buscas?")
            origen = ubicacion_geolocalizada()
        else:
            st.sidebar.markdown("### ¿Desde dónde buscas?")
            origen = None
            st.sidebar.caption("Elige una comuna o pega tus coordenadas.")

        if origen is None:
            if GEO_DISPONIBLE:
                st.sidebar.markdown("---")
                st.sidebar.caption("Si prefieres no compartir tu ubicación:")
            origen = panel_ubicacion(df)

    st.markdown("---")
    radio = st.slider("Radio de búsqueda (km)", 5, 200, 40, step=5)
    solo_urgencia = st.checkbox("Solo urgencia 24/7", value=False)
    if st.button("Actualizar catastro", use_container_width=True):
        st.cache_data.clear()
        try:
            st.rerun()
        except AttributeError:
            st.experimental_rerun()
    st.markdown("---")
    n_txt = f"{len(df):,}".replace(",", ".")
    st.caption(
        f"Datos: {n_txt} recintos vigentes con coordenadas, descargados el {sello}. "
        "Fuente: Datos Abiertos del Gobierno de Chile."
    )

# ------------------------------------------------------------------ métricas
abiertos_ahora = int(df["abierto"].sum())
c1, c2, c3, c4 = st.columns(4)
c1.metric("Recintos vigentes", f"{len(df):,}".replace(",", "."))
c2.metric("Abiertos ahora", f"{abiertos_ahora:,}".replace(",", "."))
c3.metric("Urgencias 24/7", f"{int(df['urgencia'].sum()):,}".replace(",", "."))
c4.metric("Comunas", f"{df['comuna'].nunique():,}".replace(",", "."))
st.caption(
    f"Son las {ahora:%H:%M} del {ahora:%d-%m-%Y} en Chile. "
    + ("Horario hábil: también cuentan los recintos de atención primaria."
       if ahora.weekday() < 5 and 8 <= ahora.hour < 17
       else "Fuera del horario hábil solo cuentan las urgencias.")
)

if origen is None:
    st.info("Elige una comuna o pega tus coordenadas en la barra lateral para ver resultados.")
    st.stop()

lat0, lon0, etiqueta = origen
base = df[df["urgencia"]] if solo_urgencia else df

candidatos = base[base["abierto"]].copy()
candidatos["km"] = [
    distancia_km(lat0, lon0, la, lo)
    for la, lo in zip(candidatos["lat"], candidatos["lon"])
]
candidatos = candidatos[candidatos["km"] <= radio].sort_values("km")

n_cand = f"{len(candidatos):,}".replace(",", ".")
st.markdown(f"#### {n_cand} {'recinto abierto' if len(candidatos) == 1 else 'recintos abiertos'} en {radio} km")
st.caption(f"Origen del cálculo: {etiqueta}.")

if candidatos.empty:
    urgencias = df[df["urgencia"]].copy()
    urgencias["km"] = [
        distancia_km(lat0, lon0, la, lo)
        for la, lo in zip(urgencias["lat"], urgencias["lon"])
    ]
    urgencias = urgencias.sort_values("km")
    if not urgencias.empty:
        fila = urgencias.iloc[0]
        st.warning(
            f"No hay recintos abiertos en {radio} km. La urgencia declarada más cercana es "
            f"{fila['nombre']} ({fila['comuna']}), a {formato_km(fila['km'])}."
        )
    else:
        st.error("No encontré urgencias con coordenadas para ese punto.")
    st.stop()

# ------------------------------------------------------------------ destacado
primero = candidatos.iloc[0]
resto = candidatos.iloc[1:9]

col_a, col_b = st.columns([2.1, 1])
with col_a:
    st.markdown(
        f"""
        <div class="tarjeta">
          <span class="cinta">El más cercano abierto</span>
          <h3>{primero['nombre']}</h3>
          <p class="dir">{primero['direccion'] or 'Sin dirección publicada'} · {primero['comuna']}</p>
          <p class="estado">{primero['estado_texto']}</p>
          <p class="nota">{primero['tipo_corto']}{' · ' + primero['dependencia'] if primero['dependencia'] else ''}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_b:
    st.markdown(f"<p class='nota'>DISTANCIA</p><p class='dato'>{formato_km(primero['km'])}</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='nota'>EN AUTO</p><p class='dato'>{tiempo_auto(primero['km'])}</p>", unsafe_allow_html=True)
    if primero["fono"]:
        st.link_button("Llamar al " + primero["fono"], f"tel:+56{primero['fono']}", use_container_width=True)
    st.link_button(
        "Cómo llegar",
        f"https://www.google.com/maps/dir/?api=1&destination={primero['lat']},{primero['lon']}",
        use_container_width=True,
    )

st.markdown("---")

# ------------------------------------------------------------------ lista
tabla = resto[["km", "nombre", "tipo_corto", "comuna", "estado_corto", "fono", "lat", "lon"]].copy()
tabla.insert(0, "distancia", [formato_km(k) for k in tabla["km"]])
tabla["mapa"] = [
    f"https://www.google.com/maps/dir/?api=1&destination={la},{lo}"
    for la, lo in zip(tabla["lat"], tabla["lon"])
]
tabla["tel"] = [("tel:+56" + f) if f else None for f in tabla["fono"]]

st.dataframe(
    tabla[["distancia", "nombre", "tipo_corto", "comuna", "estado_corto", "tel", "mapa"]],
    hide_index=True,
    use_container_width=True,
    column_config={
        "distancia": st.column_config.TextColumn("Dist.", width="small"),
        "nombre": st.column_config.TextColumn("Recinto", width="large"),
        "tipo_corto": st.column_config.TextColumn("Tipo", width="small"),
        "comuna": st.column_config.TextColumn("Comuna", width="small"),
        "estado_corto": st.column_config.TextColumn("Estado", width="small"),
        "tel": st.column_config.LinkColumn("Llamar", display_text="Llamar", width="small"),
        "mapa": st.column_config.LinkColumn("Ruta", display_text="Ver ruta", width="small"),
    },
)

st.download_button(
    "Descargar estos resultados (CSV)",
    tabla[["distancia", "nombre", "tipo_corto", "comuna", "estado_corto", "fono"]].to_csv(index=False).encode("utf-8-sig"),
    file_name="saludcerca_resultados.csv",
    mime="text/csv",
)

# ------------------------------------------------------------------ mapa
st.markdown("#### Mapa")
mapa = pd.DataFrame({"lat": [lat0] + list(candidatos["lat"].head(20)),
                     "lon": [lon0] + list(candidatos["lon"].head(20))})
st.map(mapa, zoom=9, use_container_width=True)


# ------------------------------------------------------------------ notas
with st.expander("Cómo se decide qué está abierto"):
    st.markdown(
        """
        1. Se descarta todo recinto que no esté vigente o que no tenga coordenadas utilizables.
        2. Se calcula la distancia en línea recta desde tu punto hasta cada recinto.
        3. Se considera **abierto** un recinto que declara urgencia (funciona día y noche)
           o uno de atención primaria dentro del horario hábil (lunes a viernes, 08:00 a 17:00).
        4. Se ordena por distancia y se muestran los más cercanos dentro del radio elegido.
        """
    )

with st.expander("Qué no puede prometer este prototipo"):
    st.markdown(
        """
        El catastro declara si un recinto **tiene** servicio de urgencia, pero no publica
        horarios, días festivos, dotación ni disponibilidad de camas. Por eso hablamos de
        «urgencia declarada» y no de «abierto con certeza».

        **Llama antes de salir.** El teléfono está en cada ficha. Esta aplicación no
        reemplaza la orientación del SAMU (131) ni la evaluación de un profesional.
        """
    )

st.caption(
    "Prototipo · Cristian Acevedo, Rodrigo Gómez, Marcelo Araya, Nathaly Donoso. "
    "Los datos son públicos y no se almacena información personal."
)
