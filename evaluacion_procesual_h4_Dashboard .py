# streamlit_app.py
"""
Dashboard interactivo para 'ColegiosFinal.csv'
- Mapea códigos a etiquetas (sexo, edad, grado, departamento)
- Une La Paz y El Alto en una sola entidad ("La Paz (incl. El Alto)")
- Presenta KPIs, gráficas (barras, pastel, apiladas, heatmap), comparativas
- Calcula promedios por estudiante (alumnos por unidad educativa) utilizando
  la cantidad de colegios por departamento que se provee en la descripción.
- Ofrece descargas de tablas agregadas.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide", page_title="Dashboard - Colegios", initial_sidebar_state="expanded")

# ----------------------
# Parámetros y mapeos
# ----------------------
PRINCIPAL_TOTAL = 10_027_254   # dataset principal (total personas)
SAMPLE_10P = 1_002_725         # 10% del dataset principal (muestra)

# Cantidad de unidades educativas por departamento (proporcionadas por el usuario)
school_counts_raw = {
    "El Alto (Municipio)": 524,
    "La Paz (Departamento)": 4230,
    "Cochabamba": 3700,
    "Santa Cruz": 3400,
    "Potosí": 1500,
    "Chuquisaca": 1050,  # Sucre / Chuquisaca
    "Oruro": 850,
    "Tarija": 800,
    "Beni": 700,
    "Pando": 250
}

# Combine El Alto into La Paz (usar "La Paz (incl. El Alto)")
la_paz_combined = school_counts_raw.get("La Paz (Departamento)", 0) + school_counts_raw.get("El Alto (Municipio)", 0)
school_counts_combined = {
    "La Paz (incl. El Alto)": la_paz_combined,
    "Cochabamba": school_counts_raw.get("Cochabamba", 0),
    "Santa Cruz": school_counts_raw.get("Santa Cruz", 0),
    "Potosí": school_counts_raw.get("Potosí", 0),
    "Chuquisaca": school_counts_raw.get("Chuquisaca", 0),
    "Oruro": school_counts_raw.get("Oruro", 0),
    "Tarija": school_counts_raw.get("Tarija", 0),
    "Beni": school_counts_raw.get("Beni", 0),
    "Pando": school_counts_raw.get("Pando", 0)
}

# Mapeos de columnas según la descripción
DEPT_MAP = {
    2.0: "La Paz (incl. El Alto)",  # 2.0 La Paz
    6.0: "La Paz (incl. El Alto)",  # 6.0 El Alto
    3.0: "Cochabamba",
    7.0: "Santa Cruz",
    5.0: "Potosí",
    1.0: "Chuquisaca",   # Sucre
    4.0: "Oruro",
    8.0: "Tarija",
    9.0: "Beni",
    10.0: "Pando"
}

SEX_MAP = {
    1.0: "Femenino",
    1: "Femenino",
    2.0: "Masculino",
    2: "Masculino"
}

EDLEV_MAP = {
    3.0: "Inicial (Pre-kínder / Kínder)",
    4.0: "Básico (1-5 años sistema anterior)",
    5.0: "Intermedio (6-8 años sistema anterior)",
    6.0: "Medio (9-12 años sistema anterior)",
    7.0: "Primaria (1-8 años sistema anterior)",
    8.0: "Secundaria (9-12 años sistema anterior)",
    9.0: "Primaria actual (1-6 años)",
    10.0: "Secundaria actual (7-12 años)"
}

AGE_GROUPS = [
    ("Primera infancia (0-5)", 0, 5),
    ("Niños y niñas (6-11)", 6, 11),
    ("Adolescentes (12-17)", 12, 17),
    ("Jóvenes (18)", 18, 18)
]

# ----------------------
# Lectura y preparación
# ----------------------
@st.cache_data(ttl=300)
def load_and_prepare(path="ColegiosFinal.csv"):
    df = pd.read_csv(path)
    # Normalizar nombres de columnas por si hay espacios
    df.columns = [c.strip() for c in df.columns]

    # Asegurarnos de que las columnas clave existan
    expected_cols = ["BO2012A_SCHOOL", "BO2012A_AGE", "BO2012A_SEX", "BO2012A_EDLEV", "BO2012A_RESDEPT"]
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise FileNotFoundError(
            f"Columnas faltantes en el CSV: {missing}. Asegúrate de que el CSV contiene estas columnas."
        )

    # Convertir a numérico cuando sea posible
    df["BO2012A_AGE"] = pd.to_numeric(df["BO2012A_AGE"], errors="coerce")
    df["BO2012A_SEX"] = pd.to_numeric(df["BO2012A_SEX"], errors="coerce")
    df["BO2012A_EDLEV"] = pd.to_numeric(df["BO2012A_EDLEV"], errors="coerce")
    df["BO2012A_RESDEPT"] = pd.to_numeric(df["BO2012A_RESDEPT"], errors="coerce")

    # Mapear departamento, sexo, grado
    df["department"] = df["BO2012A_RESDEPT"].map(DEPT_MAP).fillna("Desconocido")
    df["sexo"] = df["BO2012A_SEX"].map(SEX_MAP).fillna("Desconocido")
    df["nivel_educativo"] = df["BO2012A_EDLEV"].map(EDLEV_MAP).fillna("Desconocido")

    # Crear grupos etarios según la definición
    def age_group_label(age):
        try:
            age = float(age)
        except Exception:
            return "Desconocido"
        for label, low, high in AGE_GROUPS:
            if low <= age <= high:
                return label
        return "Fuera de rango"

    df["grupo_edad"] = df["BO2012A_AGE"].apply(age_group_label)

    # Reemplazar NaN por 'Desconocido' para visualización
    df["department"] = df["department"].replace({np.nan: "Desconocido", "Desconocido": "Desconocido"})
    df["sexo"] = df["sexo"].fillna("Desconocido")
    df["nivel_educativo"] = df["nivel_educativo"].fillna("Desconocido")

    return df

# Cargar datos
st.title("Dashboard educativo — ColegiosFinal.csv")
st.markdown(
    "**Descripción**: Dashboard interactivo que compara totales, por departamento, por sexo, edades y grado de estudio. "
    "La Paz y El Alto están combinados en **La Paz (incl. El Alto)**."
)

try:
    df = load_and_prepare("ColegiosFinal.csv")
except Exception as e:
    st.error(f"Error cargando/parseando el CSV: {e}")
    st.info(
        "Asegúrate de que `ColegiosFinal.csv` está en la misma carpeta y contiene las columnas: "
        "BO2012A_SCHOOL, BO2012A_AGE, BO2012A_SEX, BO2012A_EDLEV, BO2012A_RESDEPT"
    )
    st.stop()

# ----------------------
# KPIs y filtros
# ----------------------
total_filtered = len(df)  # dataset que tú entregaste (filtrado)
st.sidebar.header("Filtros interactivos")

# Selector de departamentos (multiselección)
dept_options = sorted(df["department"].unique())
sel_depts = st.sidebar.multiselect("Seleccionar departamento(s) (vacío = todos)", dept_options, default=dept_options)

# Rango de edades (opcional)
min_age = int(df["BO2012A_AGE"].min(skipna=True)) if not df["BO2012A_AGE"].isna().all() else 5
max_age = int(df["BO2012A_AGE"].max(skipna=True)) if not df["BO2012A_AGE"].isna().all() else 18
age_range = st.sidebar.slider("Rango de edad", min_value=min_age, max_value=max_age, value=(min_age, max_age))

# Selección por sexo
sex_filter = st.sidebar.multiselect("Sexo", options=df["sexo"].unique(), default=list(df["sexo"].unique()))

# Selección por nivel educativo
nivel_filter = st.sidebar.multiselect("Nivel educativo", options=df["nivel_educativo"].unique(), default=list(df["nivel_educativo"].unique()))

# Aplicar filtros
df_filtered = df[
    (df["department"].isin(sel_depts)) &
    (df["sexo"].isin(sex_filter)) &
    (df["nivel_educativo"].isin(nivel_filter)) &
    (df["BO2012A_AGE"].between(age_range[0], age_range[1]))
].copy()

# KPIs en la parte superior
kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Total dataset principal (personas)", f"{PRINCIPAL_TOTAL:,}")
kpi2.metric("10% del dataset principal (muestra)", f"{SAMPLE_10P:,}")
kpi3.metric("Total del dataset filtrado (ColegiosFinal.csv)", f"{total_filtered:,}")

st.markdown("---")

# ----------------------
# Agregaciones globales
# ----------------------
dept_counts = df.groupby("department").size().rename("students").reset_index()

# Asegurarnos que departamentos con 0 estudiantes pero con colegios aparezcan también
for d in school_counts_combined.keys():
    if d not in dept_counts["department"].values:
        dept_counts = pd.concat([dept_counts, pd.DataFrame([{"department": d, "students": 0}])], ignore_index=True)

# Totales por sexo
sex_counts = df.groupby("sexo").size().rename("students").reset_index().sort_values("students", ascending=False)

# Totales por grupo de edad
age_group_counts = df.groupby("grupo_edad").size().rename("students").reset_index().sort_values("students", ascending=False)

# Totales por nivel educativo
nivel_counts = df.groupby("nivel_educativo").size().rename("students").reset_index().sort_values("students", ascending=False)

# ----------------------
# Gráficas principales
# ----------------------
st.subheader("Visión general y comparativas")

col1, col2 = st.columns((2, 1))

with col1:
    st.markdown("**Distribución de estudiantes por departamento** — (La Paz + El Alto combinados).")
    fig_dept = px.bar(
        dept_counts.sort_values("students", ascending=False),
        x="department",
        y="students",
        labels={"students": "Total estudiantes", "department": "Departamento"},
        title="Total de estudiantes por departamento"
    )
    fig_dept.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_dept, use_container_width=True)

    st.markdown("**Distribución por sexo (general)** — muestra proporción de varones y mujeres.")
    fig_sex = px.pie(sex_counts, names="sexo", values="students", title="Distribución por sexo (total)")
    st.plotly_chart(fig_sex, use_container_width=True)

    st.markdown("**Distribución por grupo de edad** — categorías definidas en la descripción.")
    fig_age = px.bar(
        age_group_counts,
        x="grupo_edad",
        y="students",
        labels={"students": "Total estudiantes", "grupo_edad": "Grupo etario"},
        title="Total por grupo de edad"
    )
    st.plotly_chart(fig_age, use_container_width=True)

with col2:
    st.markdown("**Totales por nivel educativo**")
    fig_nivel = px.bar(
        nivel_counts,
        x="students",
        y="nivel_educativo",
        orientation="h",
        labels={"students": "Total estudiantes", "nivel_educativo": "Nivel educativo"},
        title="Estudiantes por nivel educativo"
    )
    st.plotly_chart(fig_nivel, use_container_width=True)

    st.markdown("**Comparativa: alumnos por departamento vs unidades educativas (promedio alumnos/unidad)**")
    comp = dept_counts.set_index("department")["students"].rename("students").to_frame().reset_index()
    comp["schools"] = comp["department"].map(school_counts_combined).fillna(0).astype(int)
    comp["avg_students_per_school"] = comp.apply(lambda r: r["students"] / r["schools"] if r["schools"] > 0 else np.nan, axis=1)
    comp_sorted = comp.sort_values("students", ascending=False)

    fig_comp = make_subplots(specs=[[{"secondary_y": True}]])
    fig_comp.add_trace(go.Bar(x=comp_sorted["department"], y=comp_sorted["students"], name="Estudiantes"), secondary_y=False)
    fig_comp.add_trace(go.Scatter(x=comp_sorted["department"], y=comp_sorted["avg_students_per_school"], mode="lines+markers", name="Promedio alumnos/escuela"), secondary_y=True)
    fig_comp.update_xaxes(tickangle=-45)
    fig_comp.update_yaxes(title_text="Estudiantes", secondary_y=False)
    fig_comp.update_yaxes(title_text="Promedio alumnos por escuela", secondary_y=True)
    fig_comp.update_layout(title_text="Estudiantes vs Unidades educativas (barra = estudiantes, línea = promedio por escuela)")
    st.plotly_chart(fig_comp, use_container_width=True)

st.markdown("---")

# ----------------------
# Comparativas por departamento (profundas)
# ----------------------
st.subheader("Comparativas por departamento (profundas)")

st.markdown("**Heatmap: grupo de edad por departamento** — muestra conteo de estudiantes de cada grupo etario por departamento.")
heat_df = df.groupby(["department", "grupo_edad"]).size().rename("count").reset_index()
heat_pivot = heat_df.pivot(index="department", columns="grupo_edad", values="count").fillna(0)
fig_heat = px.imshow(
    heat_pivot.loc[sorted(heat_pivot.index)],
    labels=dict(x="Grupo de edad", y="Departamento", color="Conteo"),
    title="Heatmap: edad por departamento"
)
st.plotly_chart(fig_heat, use_container_width=True)

st.markdown("**Barras apiladas: sexo por departamento** — muestra la composición por sexo en cada departamento.")
stack_df = df.groupby(["department", "sexo"]).size().rename("count").reset_index()
fig_stack = px.bar(stack_df, x="department", y="count", color="sexo", title="Composición por sexo en cada departamento")
fig_stack.update_layout(barmode="stack", xaxis_tickangle=-45)
st.plotly_chart(fig_stack, use_container_width=True)

st.markdown("**Treemap: jerarquía departamento → nivel educativo** — para identificar dónde se concentran los estudiantes por nivel.")
treemap_df = df.groupby(["department", "nivel_educativo"]).size().rename("count").reset_index()
fig_tree = px.treemap(treemap_df, path=["department", "nivel_educativo"], values="count", title="Treemap: Departamento → Nivel educativo")
st.plotly_chart(fig_tree, use_container_width=True)

st.markdown("---")

# ----------------------
# Métricas porcentuales y diferencias
# ----------------------
st.subheader("Porcentajes, diferencias y promedios")

national_total = df.shape[0]
sex_pct = sex_counts.copy()
sex_pct["pct"] = (sex_pct["students"] / national_total * 100).round(2)

st.markdown("**Porcentaje nacional por sexo**")
st.dataframe(sex_pct)

dept_pct = dept_counts.copy()
dept_pct["pct_total"] = (dept_pct["students"] / national_total * 100).round(3)
dept_pct["schools_assigned"] = dept_pct["department"].map(school_counts_combined).fillna(0).astype(int)
dept_pct["avg_students_per_school"] = dept_pct.apply(lambda r: (r["students"] / r["schools_assigned"]) if r["schools_assigned"] > 0 else np.nan, axis=1)
mean_pct = dept_pct["pct_total"].mean()
dept_pct["diff_vs_mean_pct_points"] = (dept_pct["pct_total"] - mean_pct).round(3)

st.markdown("**Comparativa por departamento — porcentaje del total y promedios por escuela**")
st.dataframe(dept_pct.sort_values("students", ascending=False).reset_index(drop=True))

st.markdown("**Porcentaje por sexo en cada departamento**")
sex_dept = df.groupby(["department", "sexo"]).size().rename("count").reset_index()
sex_dept_total = sex_dept.groupby("department")["count"].sum().rename("dept_total").reset_index()
sex_dept = sex_dept.merge(sex_dept_total, on="department")
sex_dept["pct"] = (sex_dept["count"] / sex_dept["dept_total"] * 100).round(2)
fig_sex_dept = px.bar(sex_dept, x="department", y="pct", color="sexo", title="Porcentaje por sexo dentro de cada departamento")
fig_sex_dept.update_layout(barmode="stack", xaxis_tickangle=-45)
st.plotly_chart(fig_sex_dept, use_container_width=True)

st.markdown("---")

# ----------------------
# Descargas y tablas agregadas
# ----------------------
st.subheader("Descargas y tablas para análisis adicional")

agg_for_download = dept_pct[["department", "students", "schools_assigned", "avg_students_per_school", "pct_total", "diff_vs_mean_pct_points"]].copy()
agg_for_download = agg_for_download.rename(columns={
    "department": "Departamento",
    "students": "Total_estudiantes",
    "schools_assigned": "Total_unidades_educativas",
    "avg_students_per_school": "Promedio_alumnos_por_unidad",
    "pct_total": "Porcentaje_del_total_nacional",
    "diff_vs_mean_pct_points": "Diferencia_vs_promedio_pct_pts"
})

st.markdown("Descargar tabla resumen por departamento:")
csv = agg_for_download.to_csv(index=False).encode("utf-8")
st.download_button("Descargar CSV (resumen por departamento)", data=csv, file_name="resumen_departamentos.csv", mime="text/csv")

st.markdown("Descargar datos filtrados (tabla de entrada después de aplicar filtros):")
csv2 = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button("Descargar CSV (datos filtrados)", data=csv2, file_name="ColegiosFinal_filtrado.csv", mime="text/csv")

st.markdown("---")

# ----------------------
# Explicaciones y guía para interpretación
# ----------------------
st.subheader("Guía rápida de interpretación")
st.markdown("""
- **KPI superior**: muestra los valores fijos que nos diste (total del dataset original, el 10% y el total del dataset filtrado que se carga desde `ColegiosFinal.csv`).
- **Estudiantes por departamento**: barras ordenadas por total. *La Paz (incl. El Alto)* aparece combinada.
- **Distribución por sexo y edad**: gráficas fáciles de interpretar para ver proporciones y concentraciones etarias.
- **Estudiantes vs Unidades educativas**: compara el total de estudiantes con la cantidad de colegios por departamento (los números de colegios que se usan son los que nos proporcionaste). La línea muestra el promedio de alumnos por unidad.
- **Heatmap**: identifica rápidamente qué departamentos concentran más estudiantes en cada grupo etario.
- **Treemap y barras apiladas**: útiles para ver jerarquías (departamento → nivel educativo) y composición por sexo respectivamente.
- **Descargas**: puedes exportar la tabla resumen por departamento y el dataset filtrado con filtros aplicados.
""")

st.markdown("**Notas importantes**:")
st.markdown("""
- Las etiquetas de grado, sexo y departamento se han asignado según la información que proporcionaste.
- Se combinó explícitamente La Paz y El Alto en **La Paz (incl. El Alto)** para todas las agregaciones.
- El promedio por estudiante por escuela se calculó usando los conteos de unidades educativas que proporcionaste (combinando El Alto con La Paz).
- Si algunos departamentos aparecen con `0` o `NaN` en promedios, significa que hay 0 unidades educativas registradas en `school_counts_combined` o 0 estudiantes en el dataset para ese departamento.
""")

st.info("By: Gabby Duran")
