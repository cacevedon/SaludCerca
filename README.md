# SaludCerca

Toma tu ubicación y te muestra el centro de salud más cercano que esté **abierto ahora**,
usando el catastro público de establecimientos del Ministerio de Salud de Chile.

## Dos versiones del prototipo

| Versión | Archivo | Qué aporta |
|---|---|---|
| Web (recomendada) | `docs/index.html` | Geolocalización del navegador, mapa y ficha con teléfono y ruta. Se publica con GitHub Pages. |
| Streamlit | `app.py` | Misma lógica en Python; búsqueda por comuna o pegando coordenadas. |

## Cómo funciona

1. Se descarta lo que no está vigente o no tiene coordenadas utilizables.
2. Se calcula la distancia en línea recta (Haversine) desde tu punto.
3. Se considera **abierto** un recinto que declara urgencia (funciona día y noche)
   o uno de atención primaria en horario hábil (lunes a viernes, 08:00 a 17:00).
4. Se ordena por distancia y se muestra primero el más cercano.

## Datos

Catastro de establecimientos de salud, portal de Datos Abiertos del Gobierno de Chile
(recurso `2c44d782-3365-44e3-aefb-2c8b8363a1bc`).

- `app.py` lo descarga en vivo por API (caché de 12 horas).
- La web usa una instantánea en `docs/datos/establecimientos.json` (5.284 recintos con
  coordenadas utilizables) para cargar rápido y no depender de la API en cada visita.

## Correr en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

Para la versión web, en la carpeta `docs/`:

```bash
python3 -m http.server 8000
```

## Límites conocidos

El catastro declara si un recinto **tiene** servicio de urgencia, pero no publica horarios,
feriados ni disponibilidad de camas. Por eso se habla de «urgencia declarada» y la app
recomienda llamar antes de salir. No reemplaza al SAMU (131) ni la evaluación de un
profesional de la salud. No se recopilan datos personales.
