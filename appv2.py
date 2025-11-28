import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import folium
import os
from datetime import datetime
import matplotlib.pyplot as plt  # Para el gráfico de torta

# -------------------------------------------------
# Config general de la página
# -------------------------------------------------
st.set_page_config(
    page_title="Directorio de Entidades - Santiago de Tolú",
    layout="wide"
)

st.title("Tolú Conecta")
st.markdown(
    "Plataforma web para ubicar y consultar entidades municipales y servicios públicos "
    "en **Santiago de Tolú**, usando datos abiertos."
)

# -------------------------------------------------
# Funciones de carga
# -------------------------------------------------
@st.cache_data
def cargar_catalogos_y_barrios():
    ruta_original = "data/catalogo.csv"
    ruta_enriquecido = "data/catalogo_enriquecido.csv"
    ruta_barrios = "data/barrios.csv"

    catalogo_original = pd.read_csv(ruta_original)

    if os.path.exists(ruta_enriquecido):
        catalogo_enriquecido = pd.read_csv(ruta_enriquecido)
    else:
        catalogo_enriquecido = None

    barrios = pd.read_csv(ruta_barrios)

    dfs = [catalogo_original]
    if catalogo_enriquecido is not None:
        dfs.append(catalogo_enriquecido)

    for df in dfs:
        df["LATITUD"] = pd.to_numeric(df["LATITUD"], errors="coerce")
        df["LONGITUD"] = pd.to_numeric(df["LONGITUD"], errors="coerce")
        df.dropna(subset=["LATITUD", "LONGITUD"], inplace=True)

    return catalogo_original, catalogo_enriquecido, barrios


@st.cache_data
def cargar_detalles_simulados():
    ruta_detalles = "data/detalles_simulados.csv"
    if os.path.exists(ruta_detalles):
        return pd.read_csv(ruta_detalles)
    else:
        columnas = ["INFRAESTRUCTURA", "DESCRIPCION", "SERVICIOS", "HORARIO", "CONTACTO", "IMAGEN_URL"]
        return pd.DataFrame(columns=columnas)


def cargar_estadisticas():
    ruta_stats = "data/estadisticas_busquedas.csv"
    if os.path.exists(ruta_stats):
        return pd.read_csv(ruta_stats)
    else:
        columnas = [
            "timestamp", "tipo_accion", "zona", "categoria",
            "infraestructura", "texto_busqueda", "resultados"
        ]
        return pd.DataFrame(columns=columnas)


def registrar_busqueda(tipo_accion, zona, categoria, infraestructura, texto_busqueda, resultados):
    ruta_stats = "data/estadisticas_busquedas.csv"
    nuevo_registro = pd.DataFrame([{
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "tipo_accion": tipo_accion,  # "boton" o "enter" o "boton_filtro"
        "zona": zona,
        "categoria": categoria,
        "infraestructura": infraestructura,
        "texto_busqueda": texto_busqueda.strip() if texto_busqueda else "",
        "resultados": int(resultados)
    }])

    if os.path.exists(ruta_stats):
        existente = pd.read_csv(ruta_stats)
        df_out = pd.concat([existente, nuevo_registro], ignore_index=True)
    else:
        df_out = nuevo_registro

    os.makedirs("data", exist_ok=True)
    df_out.to_csv(ruta_stats, index=False)


catalogo_original, catalogo_enriquecido, barrios = cargar_catalogos_y_barrios()
detalles_simulados = cargar_detalles_simulados()

# -------------------------------------------------
# Menú principal: modo
# -------------------------------------------------
st.sidebar.title("Menú")
modo = st.sidebar.radio("Selecciona modo de trabajo", ["Explorar directorio", "Ver estadísticas"])

# =================================================
# MODO: EXPLORAR DIRECTORIO
# =================================================
if modo == "Explorar directorio":

    # -------- Selección de fuente de datos --------
    st.sidebar.header("Configuración de datos")

    opciones_fuente = ["Catálogo original (datos abiertos)"]
    if catalogo_enriquecido is not None:
        opciones_fuente.append("Catálogo enriquecido (OpenStreetMap)")
    opciones_fuente.append("Catálogo + detalles simulados")

    fuente_sel = st.sidebar.radio("Fuente de datos a utilizar", opciones_fuente)

    usa_detalles = False

    if fuente_sel == "Catálogo original (datos abiertos)":
        catalogo = catalogo_original.copy()
        st.info("Estás usando el **catálogo original** publicado en datos abiertos.")

    elif fuente_sel == "Catálogo enriquecido (OpenStreetMap)" and catalogo_enriquecido is not None:
        catalogo = catalogo_enriquecido.copy()
        st.success("Estás usando el **catálogo enriquecido** con columnas de OpenStreetMap.")

    else:
        base = catalogo_enriquecido.copy() if catalogo_enriquecido is not None else catalogo_original.copy()
        catalogo = base.merge(detalles_simulados, on="INFRAESTRUCTURA", how="left")
        usa_detalles = True
        if detalles_simulados.empty:
            st.warning(
                "Seleccionaste **Catálogo + detalles simulados**, pero no se encontró "
                "`data/detalles_simulados.csv`. Solo se mostrarán los datos del catálogo."
            )
        else:
            st.success(
                "Estás usando el **catálogo** combinado con **detalles simulados** "
                "(fichas descriptivas por infraestructura)."
            )

    # -------- Filtros en barra lateral + botón --------
    st.sidebar.header("Filtros")

    # Para registrar cambios de texto (ENTER)
    if "ultimo_texto_busqueda" not in st.session_state:
        st.session_state["ultimo_texto_busqueda"] = ""

    # Filtro por zona
    if "ZONA" in catalogo.columns:
        zonas = ["Todas"] + sorted(catalogo["ZONA"].dropna().unique().tolist())
    else:
        zonas = ["Todas"]
    zona_sel = st.sidebar.selectbox("Zona", zonas)

    # Filtro por categoría
    if "CATEGORIA" in catalogo.columns:
        categorias = ["Todas"] + sorted(catalogo["CATEGORIA"].dropna().unique().tolist())
    else:
        categorias = ["Todas"]
    cat_sel = st.sidebar.selectbox("Categoría de infraestructura", categorias)

    # Filtro por tipo de infraestructura
    if "INFRAESTRUCTURA" in catalogo.columns:
        infra_list = ["Todas"] + sorted(catalogo["INFRAESTRUCTURA"].dropna().unique().tolist())
    else:
        infra_list = ["Todas"]
    infra_sel = st.sidebar.selectbox("Tipo de infraestructura", infra_list)

    # Búsqueda por texto libre
    texto_busqueda = st.sidebar.text_input(
        "Buscar por nombre o tipo de infraestructura",
        placeholder="Ej. salud, educación, turismo...",
        key="texto_busqueda"
    )

    # Botón para aplicar filtros (también registra estadística)
    btn_filtrar = st.sidebar.button("Aplicar filtros")

    # -------- Aplicar filtros a los datos --------
    df_filtrado = catalogo.copy()

    if zona_sel != "Todas" and "ZONA" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["ZONA"] == zona_sel]

    if cat_sel != "Todas" and "CATEGORIA" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["CATEGORIA"] == cat_sel]

    if infra_sel != "Todas" and "INFRAESTRUCTURA" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["INFRAESTRUCTURA"] == infra_sel]

    if texto_busqueda.strip():
        txt = texto_busqueda.strip().lower()
        condiciones = []
        if "INFRAESTRUCTURA" in df_filtrado.columns:
            condiciones.append(df_filtrado["INFRAESTRUCTURA"].str.lower().str.contains(txt, na=False))
        if "CATEGORIA" in df_filtrado.columns:
            condiciones.append(df_filtrado["CATEGORIA"].str.lower().str.contains(txt, na=False))

        if condiciones:
            from functools import reduce
            import operator
            df_filtrado = df_filtrado[reduce(operator.or_, condiciones)]

    resultados = len(df_filtrado)

    # -------- Registro automático cuando cambia el texto (ENTER) --------
    if texto_busqueda.strip():
        if texto_busqueda.strip() != st.session_state["ultimo_texto_busqueda"]:
            registrar_busqueda(
                tipo_accion="enter",
                zona=zona_sel,
                categoria=cat_sel,
                infraestructura=infra_sel,
                texto_busqueda=texto_busqueda,
                resultados=resultados
            )
            st.session_state["ultimo_texto_busqueda"] = texto_busqueda.strip()

    # -------- Registro al hacer clic en "Aplicar filtros" --------
    if btn_filtrar:
        registrar_busqueda(
            tipo_accion="boton_filtro",
            zona=zona_sel,
            categoria=cat_sel,
            infraestructura=infra_sel,
            texto_busqueda=texto_busqueda,
            resultados=resultados
        )
        st.sidebar.success("✅ Búsqueda registrada con el botón *Aplicar filtros*.")

    # -------------------------------------------------
    # Tabla de resultados
    # -------------------------------------------------
    st.subheader("Resultados filtrados")
    st.write(f"Entidades encontradas: {resultados}")

    columnas_mostrar = []
    for col in ["CATEGORIA", "INFRAESTRUCTURA", "ZONA", "LATITUD", "LONGITUD"]:
        if col in df_filtrado.columns:
            columnas_mostrar.append(col)

    for col in ["barrio_osm", "municipio_osm", "departamento_osm"]:
        if col in df_filtrado.columns:
            columnas_mostrar.append(col)

    for col in ["DESCRIPCION", "SERVICIOS", "HORARIO"]:
        if col in df_filtrado.columns:
            columnas_mostrar.append(col)

    if columnas_mostrar:
        st.dataframe(df_filtrado[columnas_mostrar])
    else:
        st.info("No se encontraron columnas esperadas para mostrar en la tabla.")

    # -------------------------------------------------
    # Botón adicional para registrar manualmente la búsqueda
    # -------------------------------------------------
    st.markdown("### Registro manual de esta consulta")
    st.caption("Además del Enter y del botón de filtros, puedes registrar esta búsqueda aquí.")

    if st.button("Registrar esta búsqueda"):
        registrar_busqueda(
            tipo_accion="boton",
            zona=zona_sel,
            categoria=cat_sel,
            infraestructura=infra_sel,
            texto_busqueda=texto_busqueda,
            resultados=resultados
        )
        st.success("✅ Búsqueda registrada en las estadísticas.")

    # -------------------------------------------------
    # Mapa con Folium + tarjeta de detalles
    # -------------------------------------------------
    st.subheader("Mapa de entidades municipales")

    if not df_filtrado.empty:
        centro_lat = df_filtrado["LATITUD"].mean()
        centro_lon = df_filtrado["LONGITUD"].mean()
    else:
        centro_lat = catalogo["LATITUD"].mean()
        centro_lon = catalogo["LONGITUD"].mean()

    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=13)

    if not df_filtrado.empty:
        for _, fila in df_filtrado.iterrows():
            nombre = fila.get("INFRAESTRUCTURA", "Entidad sin nombre")

            tarjeta = f"""
            <div style="font-size:12px; width: 260px;">
                <h4 style="margin-bottom:4px;">{nombre}</h4>
            """

            if "CATEGORIA" in fila:
                tarjeta += f"<b>Categoría:</b> {fila['CATEGORIA']}<br>"
            if "ZONA" in fila:
                tarjeta += f"<b>Zona:</b> {fila['ZONA']}<br>"

            tarjeta += f"<b>Coordenadas:</b> {fila['LATITUD']:.5f}, {fila['LONGITUD']:.5f}<br>"

            if "barrio_osm" in fila and pd.notna(fila["barrio_osm"]):
                tarjeta += f"<b>Barrio (OSM):</b> {fila['barrio_osm']}<br>"
            if "municipio_osm" in fila and pd.notna(fila["municipio_osm"]):
                tarjeta += f"<b>Municipio (OSM):</b> {fila['municipio_osm']}<br>"
            if "departamento_osm" in fila and pd.notna(fila["departamento_osm"]):
                tarjeta += f"<b>Departamento (OSM):</b> {fila['departamento_osm']}<br>"

            if "DESCRIPCION" in fila and pd.notna(fila["DESCRIPCION"]):
                tarjeta += f"<hr style='margin:4px 0;'><b>Descripción:</b> {fila['DESCRIPCION']}<br>"
            if "SERVICIOS" in fila and pd.notna(fila["SERVICIOS"]):
                tarjeta += f"<b>Servicios:</b> {fila['SERVICIOS']}<br>"
            if "HORARIO" in fila and pd.notna(fila["HORARIO"]):
                tarjeta += f"<b>Horario:</b> {fila['HORARIO']}<br>"
            if "CONTACTO" in fila and pd.notna(fila["CONTACTO"]):
                tarjeta += f"<b>Contacto:</b> {fila['CONTACTO']}<br>"

            if "IMAGEN_URL" in fila and pd.notna(fila["IMAGEN_URL"]) and str(fila["IMAGEN_URL"]).strip():
                tarjeta += f"<br><img src='{fila['IMAGEN_URL']}' width='240'>"
            else:
                tarjeta += "<br><i>Imagen pendiente por agregar.</i>"

            tarjeta += "</div>"

            folium.Marker(
                location=[fila["LATITUD"], fila["LONGITUD"]],
                popup=folium.Popup(tarjeta, max_width=300),
                icon=folium.Icon(icon="info-sign")
            ).add_to(m)

    st_folium(m, width=900, height=500)

# =================================================
# MODO: VER ESTADÍSTICAS
# =================================================
elif modo == "Ver estadísticas":
    st.subheader("Estadísticas de uso de Tolú Conecta")

    stats = cargar_estadisticas()

    if stats.empty:
        st.info("Aún no hay búsquedas registradas. Usa el modo *Explorar directorio* para generar estadísticas.")
    else:
        # Asegurar tipos de fecha
        stats["timestamp_dt"] = pd.to_datetime(stats["timestamp"], errors="coerce")
        stats["fecha"] = stats["timestamp_dt"].dt.date

        st.markdown("### Resumen general")
        st.write(f"Total de eventos registrados: **{len(stats)}**")

        # ============================
        # 1. Top de infraestructuras más buscadas
        # ============================
        st.markdown("## Top de infraestructuras más consultadas")
        infra_validas = stats[
            stats["infraestructura"].notna()
            & (stats["infraestructura"] != "")
            & (stats["infraestructura"] != "Todas")
        ]

        if not infra_validas.empty:
            conteo_infra = (
                infra_validas.groupby("infraestructura")
                .size()
                .sort_values(ascending=False)
            )
            top_infra = conteo_infra.head(10)  # Top 10 (puedes cambiarlo a 5 si quieres)

            st.bar_chart(top_infra)
            st.caption("Top de infraestructuras según cantidad de veces que se consultan.")
        else:
            st.caption("Aún no hay suficientes datos de infraestructuras consultadas.")

        # ============================
        # 2. Barras: TODAS las categorías
        # ============================
        st.markdown("## Frecuencia de consulta por categoría (todas)")
        cat_validas = stats[
            stats["categoria"].notna()
            & (stats["categoria"] != "")
            & (stats["categoria"] != "Todas")
        ]

        if not cat_validas.empty:
            conteo_cat = (
                cat_validas.groupby("categoria")
                .size()
                .sort_values(ascending=False)
            )
            st.bar_chart(conteo_cat)
            st.caption("Cada barra representa cuántas veces se ha usado esa categoría en las búsquedas.")
        else:
            st.caption("Aún no hay suficientes datos de categorías consultadas.")

        # ============================
        # 3. Barras: TODAS las infraestructuras
        # ============================
        st.markdown("## Frecuencia de consulta por infraestructura (todas)")
        if not infra_validas.empty:
            st.bar_chart(conteo_infra)  # usamos conteo_infra completo (no solo top)
            st.caption("Frecuencia de consulta de cada infraestructura registrada.")
        else:
            st.caption("Aún no hay suficientes datos de infraestructuras para este gráfico.")

        # ============================
        # 4. Línea de tiempo: consultas por día
        # ============================
        st.markdown("## Consultas por día")
        por_dia = stats.groupby("fecha").size()
        st.line_chart(por_dia)
        st.caption("Número de eventos de búsqueda registrados por día.")

        # ============================
        # 5. Torta: distribución Rural vs Urbana (ZONA)
        # ============================
        st.markdown("## Distribución de consultas por zona (Rural vs Urbana)")

        zona_validas = stats[
            stats["zona"].notna()
            & (stats["zona"] != "")
            & (stats["zona"] != "Todas")
        ]

        if not zona_validas.empty:
            conteo_zonas = (
                zona_validas.groupby("zona")
                .size()
                .sort_values(ascending=False)
            )

            fig, ax = plt.subplots()
            ax.pie(
                conteo_zonas.values,
                labels=conteo_zonas.index,
                autopct='%1.1f%%'
            )
            ax.set_title("Porcentaje de consultas según la zona seleccionada (ej. urbana / rural)")
            st.pyplot(fig)
        else:
            st.caption("Aún no hay suficiente información sobre la zona para mostrar el gráfico de torta.")

        # ============================
        # 6. Últimas búsquedas
        # ============================
        st.markdown("## Últimas 20 búsquedas registradas")
        st.dataframe(
            stats.sort_values("timestamp_dt", ascending=False).head(20),
            use_container_width=True
        )
