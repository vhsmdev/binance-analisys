import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, date, timezone
from binance_client import get_trades, get_price, get_balance, get_open_orders, get_opening_price, get_real_balance
from storytelling_calculator import processar_trades_completos

st.set_page_config(page_title="Binance PnL Online", layout="wide")
st_autorefresh(interval=1 * 60 * 1000, key="data_refresh")

# ⏰ Controle de dia com base no horário da Binance (UTC)
if "last_loaded_day" not in st.session_state:
    st.session_state["last_loaded_day"] = datetime.now(timezone.utc).date()

if st.session_state["last_loaded_day"] != datetime.now(timezone.utc).date():
    st.session_state.clear()

st.title("📡 PnL com dados ao vivo da Binance")
st.caption("Este painel mostra o desempenho detalhado das suas estratégias de trade na Binance, com histórico completo de operações.")

ativos = {
    "XRPUSDT": "QuickScalp",
    "CAKEUSDT": "QuickScalp",
    "TRXUSDT": "QuickScalp",
    "FUNUSDT": "BREAKX",
    "EDUUSDT": "BREAKX"
}

all_trades = []
all_posicoes = []
resumos = []
saldos_usdt = []
saldos_tokens = []
operacoes_realizadas = []
ordens_abertas = []

with st.spinner("🔄 Coletando dados da Binance..."):
    for symbol, estrategia in ativos.items():
        try:
            trades = get_trades(symbol)
            preco_atual = get_price(symbol)

            token = symbol.replace("USDT", "")
            saldo_livre, _ = get_balance(token)
            saldo_livre = float(saldo_livre)

            df_trades = pd.DataFrame(trades)
            df_trades["symbol"] = symbol
            df_price = pd.DataFrame([{"symbol": symbol, "current_price": preco_atual}])

            if not df_trades.empty:
                df_story, df_posicao = processar_trades_completos(df_trades, df_price, estrategia)
                df_story["Estratégia"] = estrategia
                all_trades.append(df_story)

                if not df_posicao.empty:
                    df_posicao["Estratégia"] = estrategia
                    all_posicoes.append(df_posicao)
                    resumos.append(df_posicao)

                realizadas = df_story[df_story["PnL USDT"].str.contains(r"^-?\$")]
                realizadas["pnl_num"] = pd.to_numeric(
                    realizadas["PnL USDT"].str.replace("$", "").replace("-", None),
                    errors="coerce"
                ).fillna(0.0)
                realizadas["Data"] = pd.to_datetime(realizadas["Data/Hora"]).dt.date
                operacoes_realizadas.append(realizadas)

            saldos_tokens.append((token, saldo_livre))
            saldos_usdt.append(saldo_livre * preco_atual)

            # Ordens abertas (pendentes)
            ordens = get_open_orders(symbol)
            for ordem in ordens:
                ordens_abertas.append({
                    "Ativo": ordem["symbol"],
                    "Tipo": ordem["side"],
                    "Qtd": float(ordem["origQty"]),
                    "Preço": float(ordem["price"]),
                    "Status": ordem["status"],
                    "Criada em": ordem["time"]
                })

        except Exception as e:
            st.error(f"Erro ao processar {symbol}: {e}")

# Saldo USDT
try:
    usdt_saldo, _ = get_balance("USDT")
    usdt_saldo = float(usdt_saldo)
except:
    usdt_saldo = 0.0

meta_dia = 0.50  # 🎯 Meta de lucro diário em USDT

# Tabs
tab1, tab2 = st.tabs(["📊 Análise Geral", "📆 Análise do Dia"])
if all_trades:
    df_full = pd.concat(all_trades, ignore_index=True)
    df_realizadas = pd.concat(operacoes_realizadas, ignore_index=True)

    # 📆 ANÁLISE DO DIA
    with tab2:
        st.subheader("📆 Resultado de Hoje (Horário da Binance - UTC)")

        hoje_utc = datetime.now(timezone.utc).date()
        df_hoje = df_realizadas[df_realizadas["Data"] == hoje_utc]
        lucro_hoje = df_hoje["pnl_num"].sum()
        lucro_medio_hoje = df_hoje["pnl_num"].mean() if not df_hoje.empty else 0.0
        progresso = min(max(lucro_hoje / meta_dia, 0.0), 1.0)  # <-- Correção aplicada aqui

        st.markdown(f"🎯 **Meta diária:** ${meta_dia:.2f}")

        col1, col2 = st.columns(2)
        col1.metric("💰 Lucro do Dia", f"${lucro_hoje:.2f}")
        col2.progress(progresso, text=f"{progresso * 100:.1f}% da meta diária")

        col3, col4, col5 = st.columns(3)
        col3.metric("📈 Lucro Médio por Operação", f"${lucro_medio_hoje:.2f}")
        col4.metric("💰 Valor Atual em Ativos", f"${sum(saldos_usdt):.2f}")
        col5.metric("💵 Saldo Atual em USDT", f"${usdt_saldo:.2f}")

        if ordens_abertas:
            st.subheader("📌 Ordens Abertas (Pendentes na Binance)")
            df_abertas = pd.DataFrame(ordens_abertas)
            df_abertas["Criada em"] = pd.to_datetime(df_abertas["Criada em"], unit="ms")
            df_abertas = df_abertas[["Ativo", "Tipo", "Qtd", "Preço", "Status", "Criada em"]]
            st.dataframe(df_abertas, use_container_width=True)
        else:
            st.info("✅ Não há ordens pendentes no momento.")

        st.divider()
        st.subheader("📘 Histórico de Trades do Dia")
        st.dataframe(df_hoje, use_container_width=True)
    with tab1:
        st.subheader("💰 Visão Consolidada da Carteira (Saldo Estimado)")

        hoje_utc = datetime.now(timezone.utc).date()
        hoje_str = hoje_utc.strftime("%Y-%m-%d")

        ativos_detalhados = []
        saldo_estimado_atual = 0.0

        for symbol, estrategia in ativos.items():
            token = symbol.replace("USDT", "")
            preco_atual = get_price(symbol)
            saldo_token = get_real_balance(token)
            valor_atual = saldo_token * preco_atual

            # Obter preço de abertura (00:00 UTC)
            preco_abertura = get_opening_price(symbol) or preco_atual
            valor_inicio_dia = saldo_token * preco_abertura
            pnl_token_hoje = valor_atual - valor_inicio_dia

            saldo_estimado_atual += valor_atual

            ativos_detalhados.append({
                "Ativo": token,
                "Qtd": round(saldo_token, 6),
                "Preço Atual": round(preco_atual, 4),
                "Valor Atual (USDT)": round(valor_atual, 2),
                "PnL do Dia (USDT)": round(pnl_token_hoje, 2)
            })

        saldo_estimado_atual += usdt_saldo
        pnl_total = sum([x["PnL do Dia (USDT)"] for x in ativos_detalhados])

        # Indicadores principais
        st.metric("💰 Saldo Estimado Atual", f"${saldo_estimado_atual:.2f}")
        st.caption(f"📊 PnL do Dia (modo Binance): ${pnl_total:+.2f}")
        st.metric("💵 USDT Disponível", f"${usdt_saldo:.2f}")

        # Detalhamento por token
        st.subheader("🔍 Detalhamento dos Ativos e PnL do Dia")
        df_ativos = pd.DataFrame(ativos_detalhados)
        df_ativos = df_ativos.sort_values(by="PnL do Dia (USDT)", ascending=False)
        st.dataframe(df_ativos, use_container_width=True)

        # Ativos com prejuízo
        df_perdas = df_ativos[df_ativos["PnL do Dia (USDT)"] < 0]
        if not df_perdas.empty:
            st.subheader("❌ Ativos com Prejuízo Hoje")
            st.dataframe(df_perdas, use_container_width=True)
        else:
            st.success("✅ Nenhum ativo com prejuízo hoje.")

        # Gráfico PnL por ativo
        st.subheader("📈 PnL do Dia por Ativo")
        st.bar_chart(df_ativos.set_index("Ativo")["PnL do Dia (USDT)"])

        # Gráfico de distribuição da carteira
        st.subheader("📊 Distribuição da Carteira (em USDT)")
        df_dist = df_ativos[["Ativo", "Valor Atual (USDT)"]].copy()
        df_dist.loc[len(df_dist.index)] = ["USDT", round(usdt_saldo, 2)]
        df_dist = df_dist.sort_values(by="Valor Atual (USDT)", ascending=False)
        st.bar_chart(df_dist.set_index("Ativo")["Valor Atual (USDT)"])

        # Evolução do saldo estimado (em sessão)
        if "evolucao_saldo" not in st.session_state:
            st.session_state["evolucao_saldo"] = {}
        st.session_state["evolucao_saldo"][hoje_str] = saldo_estimado_atual

        df_evolucao = pd.DataFrame([
            {"Data": k, "Saldo Estimado": v}
            for k, v in st.session_state["evolucao_saldo"].items()
        ])
        df_evolucao["Data"] = pd.to_datetime(df_evolucao["Data"])
        df_evolucao = df_evolucao.sort_values("Data").set_index("Data")

        st.subheader("📈 Evolução Diária do Saldo Estimado")
        st.line_chart(df_evolucao["Saldo Estimado"])
