import streamlit as st
import pandas as pd
import plotly.express as px


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Dashboard Pasarela de Pagos",
    page_icon="📊",
    layout="wide"
)


# ============================================================
# AUTENTICACIÓN
# ============================================================

def mostrar_login():
    st.title("Dashboard de Pagos")
    st.write("Acceso privado.")
    st.button(
        "Ingresar con Google",
        on_click=st.login,
        type="primary"
    )


# Usuario no autenticado
if not st.user.is_logged_in:
    mostrar_login()
    st.stop()


# ============================================================
# AUTORIZACIÓN
# ============================================================

email = getattr(st.user, "email", "").lower()

allowed_emails = [
    x.lower()
    for x in st.secrets["access"]["allowed_emails"]
]


if email not in allowed_emails:

    st.error(
        "Tu cuenta no tiene autorización para acceder a este dashboard."
    )

    st.write(f"Cuenta actual: {email}")

    st.button(
        "Cerrar sesión",
        on_click=st.logout
    )

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.write(f"👤 {getattr(st.user, 'name', '')}")
    st.caption(email)

    st.button(
        "Cerrar sesión",
        on_click=st.logout
    )

    st.divider()


# ============================================================
# CARGA DE DATA
# ============================================================

@st.cache_data
def cargar_datos():

    df = pd.read_csv(
        "data/transacciones_limpias.csv"
    )

    # Fecha
    df["order_created_at"] = pd.to_datetime(
        df["order_created_at"],
        errors="coerce"
    )

    # Valores numéricos
    columnas_numericas = [
        "order_total_price",
        "transaction_response_amount"
    ]

    for col in columnas_numericas:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    # Normalizar estado
    df["transaction_response_status"] = (
        df["transaction_response_status"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    return df


df = cargar_datos()


# ============================================================
# ESTADOS EXITOSOS
# ============================================================

SUCCESS_STATUSES = [
    "charged",
    "paid",
    "approved",
    "success",
    "succeeded",
    "completed"
]

df["is_success"] = (
    df["transaction_response_status"]
    .isin(SUCCESS_STATUSES)
)


# ============================================================
# ENCABEZADO
# ============================================================

st.title("Dashboard Pasarela de Pagos")

st.caption(
    "Análisis histórico de órdenes y transacciones"
)


# ============================================================
# FILTROS
# ============================================================

st.sidebar.header("Filtros")


# --------------------
# Medio de pago
# --------------------

if "order_provider_gateway" in df.columns:

    gateways = sorted(
        df["order_provider_gateway"]
        .dropna()
        .unique()
    )

    gateways_seleccionados = st.sidebar.multiselect(
        "Medio de pago",
        options=gateways,
        default=gateways
    )

    df_filtrado = df[
        df["order_provider_gateway"]
        .isin(gateways_seleccionados)
    ].copy()

else:

    df_filtrado = df.copy()


# --------------------
# Estado
# --------------------

estados = sorted(
    df_filtrado["transaction_response_status"]
    .dropna()
    .unique()
)

estados_seleccionados = st.sidebar.multiselect(
    "Estado de transacción",
    options=estados,
    default=estados
)

df_filtrado = df_filtrado[
    df_filtrado["transaction_response_status"]
    .isin(estados_seleccionados)
]


# --------------------
# Fecha
# --------------------

fecha_min = df_filtrado["order_created_at"].min()
fecha_max = df_filtrado["order_created_at"].max()


if pd.notna(fecha_min) and pd.notna(fecha_max):

    rango_fecha = st.sidebar.date_input(
        "Rango de fechas",
        value=(
            fecha_min.date(),
            fecha_max.date()
        ),
        min_value=fecha_min.date(),
        max_value=fecha_max.date()
    )

    if len(rango_fecha) == 2:

        inicio = pd.Timestamp(rango_fecha[0])
        fin = pd.Timestamp(rango_fecha[1])

        df_filtrado = df_filtrado[
            (df_filtrado["order_created_at"] >= inicio)
            &
            (
                df_filtrado["order_created_at"]
                < fin + pd.Timedelta(days=1)
            )
        ]


# ============================================================
# KPIs
# ============================================================

ordenes = df_filtrado["order_id"].nunique()

df_exitosas = df_filtrado[
    df_filtrado["is_success"]
]

ordenes_exitosas = (
    df_exitosas["order_id"].nunique()
)

tasa_exito = (
    ordenes_exitosas / ordenes * 100
    if ordenes > 0
    else 0
)

volumen = (
    df_exitosas["transaction_response_amount"]
    .sum()
)

ticket_promedio = (
    volumen / ordenes_exitosas
    if ordenes_exitosas > 0
    else 0
)


col1, col2, col3, col4 = st.columns(4)


col1.metric(
    "Órdenes",
    f"{ordenes:,}"
)

col2.metric(
    "Órdenes exitosas",
    f"{ordenes_exitosas:,}"
)

col3.metric(
    "Tasa de éxito",
    f"{tasa_exito:.1f}%"
)

col4.metric(
    "Volumen procesado",
    f"${volumen:,.0f}"
)


st.divider()


# ============================================================
# SEGUNDA FILA KPIs
# ============================================================

col1, col2, col3 = st.columns(3)

col1.metric(
    "Ticket promedio",
    f"${ticket_promedio:,.0f}"
)

col2.metric(
    "Transacciones",
    f"{len(df_filtrado):,}"
)

col3.metric(
    "Medios de pago",
    df_filtrado["order_provider_gateway"].nunique()
    if "order_provider_gateway" in df_filtrado.columns
    else "-"
)


# ============================================================
# EVOLUCIÓN TEMPORAL
# ============================================================

st.subheader("Evolución del volumen procesado")


df_tiempo = (
    df_exitosas
    .set_index("order_created_at")
    .resample("D")["transaction_response_amount"]
    .sum()
    .reset_index()
)


fig = px.line(
    df_tiempo,
    x="order_created_at",
    y="transaction_response_amount",
    markers=True,
    labels={
        "order_created_at": "Fecha",
        "transaction_response_amount": "Monto"
    }
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ============================================================
# ESTADOS
# ============================================================

col1, col2 = st.columns(2)


with col1:

    st.subheader("Estados de transacción")

    estados_chart = (
        df_filtrado[
            "transaction_response_status"
        ]
        .value_counts()
        .reset_index()
    )

    estados_chart.columns = [
        "estado",
        "cantidad"
    ]

    fig_status = px.bar(
        estados_chart,
        x="estado",
        y="cantidad"
    )

    st.plotly_chart(
        fig_status,
        use_container_width=True
    )


# ============================================================
# MEDIOS DE PAGO
# ============================================================

with col2:

    st.subheader("Volumen por medio de pago")

    if "order_provider_gateway" in df_exitosas.columns:

        gateway_chart = (
            df_exitosas
            .groupby(
                "order_provider_gateway",
                as_index=False
            )["transaction_response_amount"]
            .sum()
            .sort_values(
                "transaction_response_amount",
                ascending=False
            )
        )

        fig_gateway = px.bar(
            gateway_chart,
            x="order_provider_gateway",
            y="transaction_response_amount"
        )

        st.plotly_chart(
            fig_gateway,
            use_container_width=True
        )


# ============================================================
# DATA
# ============================================================

st.subheader("Detalle de transacciones")

st.dataframe(
    df_filtrado,
    use_container_width=True,
    hide_index=True
)