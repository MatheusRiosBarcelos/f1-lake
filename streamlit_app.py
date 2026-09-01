"""F1 Champion Predictor -- interface do modelo servido no Databricks.

Rodar local:  streamlit run streamlit_app.py
"""

import streamlit as st

st.set_page_config(
    page_title="F1 Champion Predictor",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from f1_app import theme  # noqa: E402 -- depois do set_page_config
from f1_app.views import driver, leaderboard, model_card, simulator  # noqa: E402

theme.inject()
st.logo("assets/brand.svg", size="large", link=None)


# `url_path` explicito: as quatro views expoem uma funcao `render`, e o st.Page
# inferiria o mesmo pathname para todas. A pagina default fica na raiz e nao
# recebe url_path -- dar um a ela cria uma rota que responde "Page not found".
PAGINAS = [
    st.Page(leaderboard.render, title="Corrida pelo titulo", icon="🏆", default=True),
    st.Page(driver.render, title="Raio-x do piloto", icon="🔍", url_path="piloto"),
    st.Page(simulator.render, title="Simulador", icon="🎛️", url_path="simulador"),
    st.Page(model_card.render, title="Sobre o modelo", icon="📈", url_path="modelo"),
]

st.navigation(PAGINAS).run()
