"""Tema visual da aplicacao (dark, compromisso unico) + componentes de layout.

Cores de DADOS vem da paleta validada (passo dark, checada para CVD e contraste).
O vermelho de identidade da F1 aparece apenas em cromo -- barra de marca, badges
de posicao -- nunca codificando valor, para nao competir com o vermelho semantico
("abaixo da mediana") usado nos graficos.
"""

import altair as alt
import streamlit as st

# --- Superficies e texto ---------------------------------------------------
SURFACE = "#1a1a19"
SURFACE_RAISED = "#232322"
SURFACE_SUNKEN = "#141413"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#c3c2b7"
TEXT_MUTED = "#8a8a80"
GRID = "#33332f"
BORDER = "#3a3a35"

# --- Cores de dados (paleta validada, passo dark) --------------------------
ACCENT = "#3987e5"        # slot 1 -- azul
ACCENT_2 = "#d95926"      # slot 2 -- laranja
POSITIVE = "#199e70"      # aqua
NEGATIVE = "#e66767"      # vermelho semantico
MUTED_MARK = "#4a4a45"
SEQUENTIAL = ["#184f95", "#256abf", "#2a78d6", "#3987e5", "#5598e7", "#86b6ef"]

# --- Cromo de identidade (nunca codifica dado) -----------------------------
BRAND = "#e10600"

_CSS = f"""
<style>
  .stApp {{ background: {SURFACE}; }}
  section[data-testid="stSidebar"] {{
      background: {SURFACE_SUNKEN};
      border-right: 1px solid {BORDER};
  }}
  h1, h2, h3, h4 {{ color: {TEXT_PRIMARY}; letter-spacing: -0.015em; }}

  /* Barra de marca no topo da pagina */
  .f1-brandbar {{
      height: 3px; border-radius: 3px; margin: 0 0 1.4rem 0;
      background: linear-gradient(90deg, {BRAND} 0%, {ACCENT_2} 38%, {ACCENT} 100%);
  }}

  /* Cabecalho de pagina */
  .stApp .f1-eyebrow {{
      font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.14em; color: {BRAND}; margin: 0 0 0.35rem 0;
  }}
  .stApp h1.f1-title {{
      font-size: 2.1rem; font-weight: 680; line-height: 1.1;
      color: {TEXT_PRIMARY}; margin: 0 0 0.5rem 0; letter-spacing: -0.02em;
      padding: 0;
  }}
  .stApp .f1-lede {{
      color: {TEXT_SECONDARY}; font-size: 1rem; line-height: 1.55;
      max-width: 70ch; margin: 0 0 0.4rem 0;
  }}
  .stApp .f1-sub {{ color: {TEXT_SECONDARY}; font-size: 0.9rem; }}
  .stApp .f1-muted {{ color: {TEXT_MUTED}; font-size: 0.82rem; }}

  /* Numero-heroi */
  .stApp .f1-hero-label {{
      font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.12em;
      color: {TEXT_MUTED}; margin: 0 0 0.2rem 0; font-weight: 600;
  }}
  .stApp .f1-hero {{
      font-size: 3.4rem; font-weight: 700; line-height: 1;
      color: {TEXT_PRIMARY}; margin: 0 0 0.3rem 0; letter-spacing: -0.03em;
      font-variant-numeric: tabular-nums;
  }}

  /* Cartoes */
  .f1-card {{
      background: {SURFACE_RAISED}; border: 1px solid {BORDER};
      border-radius: 12px; padding: 1.05rem 1.2rem; height: 100%;
  }}

  /* Podio */
  .f1-podium {{
      background: {SURFACE_RAISED}; border: 1px solid {BORDER};
      border-radius: 12px; padding: 1rem 1.1rem; height: 100%;
      position: relative; overflow: hidden;
  }}
  .f1-podium::before {{
      content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  }}
  .f1-podium-1::before {{ background: {BRAND}; }}
  .f1-podium-2::before {{ background: {ACCENT}; }}
  .f1-podium-3::before {{ background: {MUTED_MARK}; }}
  .stApp .f1-pos {{
      font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
      color: {TEXT_MUTED}; text-transform: uppercase;
  }}
  .stApp .f1-podium-name {{
      font-size: 1.18rem; font-weight: 650; color: {TEXT_PRIMARY};
      margin: 0.15rem 0 0.1rem 0; line-height: 1.2;
  }}
  .stApp .f1-podium-team {{ font-size: 0.8rem; color: {TEXT_MUTED}; margin-bottom: 0.6rem; }}
  .stApp .f1-podium-val {{
      font-size: 1.9rem; font-weight: 700; color: {TEXT_PRIMARY};
      line-height: 1; font-variant-numeric: tabular-nums;
  }}
  .stApp .f1-podium-sub {{ font-size: 0.76rem; color: {TEXT_MUTED}; margin-top: 0.25rem; }}

  /* Secoes */
  .stApp h2.f1-section {{
      font-size: 1.15rem; font-weight: 650; color: {TEXT_PRIMARY};
      margin: 1.6rem 0 0.15rem 0; padding: 0;
  }}
  .stApp .f1-section-sub {{
      color: {TEXT_MUTED}; font-size: 0.86rem; margin: 0 0 0.7rem 0;
      max-width: 78ch; line-height: 1.5;
  }}

  /* Metricas nativas */
  div[data-testid="stMetric"] {{
      background: {SURFACE_RAISED}; border: 1px solid {BORDER};
      border-radius: 10px; padding: 0.7rem 0.9rem;
  }}
  div[data-testid="stMetricValue"] {{
      color: {TEXT_PRIMARY}; font-variant-numeric: tabular-nums;
  }}
  div[data-testid="stMetricLabel"] p {{ color: {TEXT_MUTED}; font-size: 0.78rem; }}

  /* Barra lateral */
  .stApp .f1-brand {{
      display: flex; align-items: center; gap: 0.55rem;
      font-size: 1.02rem; font-weight: 700; color: {TEXT_PRIMARY};
      letter-spacing: -0.01em; margin-bottom: 0.1rem;
  }}
  .stApp .f1-brand-tag {{
      font-size: 0.7rem; color: {TEXT_MUTED}; letter-spacing: 0.06em;
      text-transform: uppercase; margin-bottom: 0.9rem;
  }}
  .stApp .f1-sidebar-label {{
      font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.12em; color: {TEXT_MUTED}; margin: 0.4rem 0 0.1rem 0;
  }}

  /* Legenda de estado */
  .stApp .f1-pill {{
      display: inline-block; padding: 0.16rem 0.55rem; border-radius: 999px;
      font-size: 0.72rem; font-weight: 600; border: 1px solid {BORDER};
      color: {TEXT_SECONDARY}; background: {SURFACE_RAISED};
  }}
</style>
"""


def _altair_theme() -> dict:
    return {
        "config": {
            "background": "transparent",
            "font": "Inter, -apple-system, Segoe UI, sans-serif",
            "view": {"stroke": "transparent", "continuousHeight": 280},
            "title": {
                "color": TEXT_PRIMARY,
                "subtitleColor": TEXT_SECONDARY,
                "fontSize": 15,
                "fontWeight": 600,
                "anchor": "start",
                "offset": 12,
            },
            "axis": {
                "labelColor": TEXT_SECONDARY,
                "titleColor": TEXT_MUTED,
                "labelFontSize": 11,
                "titleFontSize": 11,
                "titleFontWeight": 500,
                "domainColor": GRID,
                "tickColor": GRID,
                "gridColor": GRID,
                "gridOpacity": 0.55,
                "labelPadding": 6,
            },
            "legend": {
                "labelColor": TEXT_SECONDARY,
                "titleColor": TEXT_MUTED,
                "labelFontSize": 11,
                "titleFontSize": 11,
                "symbolType": "square",
                "orient": "top",
                "direction": "horizontal",
            },
            "range": {"category": [ACCENT, ACCENT_2, POSITIVE, "#c98500"]},
            "bar": {"cornerRadiusEnd": 4},
            "line": {"strokeWidth": 2},
            "point": {"size": 70, "filled": True},
        }
    }


def inject() -> None:
    """Aplica CSS e registra o tema Altair. Idempotente."""
    st.markdown(_CSS, unsafe_allow_html=True)
    try:  # Vega-Altair >= 5.5
        alt.theme.register("f1lake", enable=True)(_altair_theme)
    except AttributeError:  # Vega-Altair 5.0 - 5.4
        alt.themes.register("f1lake", _altair_theme)
        alt.themes.enable("f1lake")


# --------------------------------------------------------------------------
# Componentes
# --------------------------------------------------------------------------

def page_header(eyebrow: str, title: str, lede: str, como_ler: list[str] | None = None) -> None:
    """Cabecalho padrao: o que e esta tela, em uma frase, mais um guia opcional."""
    st.markdown('<div class="f1-brandbar"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="f1-eyebrow">{eyebrow}</div>'
        f'<h1 class="f1-title">{title}</h1>'
        f'<div class="f1-lede">{lede}</div>',
        unsafe_allow_html=True,
    )
    if como_ler:
        with st.expander("Como ler esta tela"):
            st.markdown("\n".join(f"- {item}" for item in como_ler))


def section(titulo: str, subtitulo: str = "") -> None:
    st.markdown(
        f'<h2 class="f1-section">{titulo}</h2>'
        + (f'<div class="f1-section-sub">{subtitulo}</div>' if subtitulo else ""),
        unsafe_allow_html=True,
    )


def hero(label: str, value: str, sub: str = "") -> None:
    """Numero-heroi: um valor unico que a tela lidera, sem virar grafico de uma barra."""
    st.markdown(
        f'<div class="f1-hero-label">{label}</div>'
        f'<div class="f1-hero">{value}</div>'
        f'<div class="f1-sub">{sub}</div>',
        unsafe_allow_html=True,
    )


def podium_card(posicao: int, nome: str, equipe: str, valor: str, sub: str) -> None:
    st.markdown(
        f'<div class="f1-podium f1-podium-{posicao}">'
        f'  <div class="f1-pos">{posicao}º lugar previsto</div>'
        f'  <div class="f1-podium-name">{nome}</div>'
        f'  <div class="f1-podium-team">{equipe}</div>'
        f'  <div class="f1-podium-val">{valor}</div>'
        f'  <div class="f1-podium-sub">{sub}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def card(html: str) -> None:
    st.markdown(f'<div class="f1-card">{html}</div>', unsafe_allow_html=True)
