# app.py
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, date
from binance_client import get_trades, get_price, get_balance
from storytelling_calculator import processar_trades_completos

st.set_page_config(page_title="Binance PnL Online", layout="wide")

# 🔄 Atualiza automaticamente a cada 6 minutos
st_autorefresh(interval=6 * 60 * 1000, key="data_refresh")

# ⏰ Verifica mudança de dia para atualizar painel
if "last_loaded_day" not in st.session_state:
    st.session_state["last_loaded_day"] = datetime.today().date()

if st.session_state["last_loaded_day"] != datetime.today().date():
    st.session_state.clear()
    st.experimental_rerun()

st.title("📡 PnL com dados ao vivo da Binance")
st.caption("Este painel mostra o desempenho detalhado das suas estratégias de trade na Binance, com histórico completo de operações.")

ativos = {
    "XRPUSDT": "XRP Agressiva",
    "CAKEUSDT": "CAKE Scalping"
}

all_trades = []
all_posicoes = []
resumos = []
saldos_usdt = []
saldos_tokens = []
operacoes_realizadas = []

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

        except Exception as e:
            st.error(f"Erro ao processar {symbol}: {e}")

# Saldo USDT
try:
    usdt_saldo, _ = get_balance("USDT")
    usdt_saldo = float(usdt_saldo)
except:
    usdt_saldo = 0.0

# Tabs
tab1, tab2 = st.tabs(["📊 Painel Geral", "📆 Resultado de Hoje"])

with tab1:
    if all_trades:
        df_full = pd.concat(all_trades, ignore_index=True)
        df_realizadas = pd.concat(operacoes_realizadas, ignore_index=True)

        total_realizado = df_realizadas["pnl_num"].sum()
        lucro_medio = df_realizadas["pnl_num"].mean()
        total_em_ativos = sum(saldos_usdt)

        estrategia_grouped = df_realizadas.groupby("Estratégia")
        cards = []
        for nome, grupo in estrategia_grouped:
            positivas = grupo[grupo["pnl_num"] > 0].shape[0]
            negativas = grupo[grupo["pnl_num"] <= 0].shape[0]
            lucro_total = grupo["pnl_num"].sum()
            cards.append((nome, positivas, negativas, lucro_total))

        st.subheader("💼 Visão Geral da Carteira")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💵 Lucro Realizado Total", f"${total_realizado:.2f}")
        col2.metric("📈 Lucro Médio por Operação", f"${lucro_medio:.2f}")
        col3.metric("💰 Valor Atual em Ativos", f"${total_em_ativos:.2f}")
        col4.metric("💵 Saldo Atual em USDT", f"${usdt_saldo:.2f}")

        with st.expander("📦 Saldos por Ativo"):
            for token, qtd in saldos_tokens:
                st.write(f"🔸 {token}: {qtd:.4f}")

        # 🗓️ Dias positivos e negativos - MOVIDO PARA CIMA
        st.subheader("📅 Dias Positivos e Negativos")
        df_dias = df_realizadas.groupby("Data").agg(
            Total=('pnl_num', 'sum'),
        ).reset_index()
        df_dias["Status"] = df_dias["Total"].apply(lambda x: "🟢 Positivo" if x > 0 else "🔴 Negativo")
        st.dataframe(df_dias, use_container_width=True)

        st.divider()

        if all_posicoes:
            df_pos = pd.concat(all_posicoes, ignore_index=True)
            st.subheader("📌 Posição Atual por Estratégia")
            for _, row in df_pos.iterrows():
                col1, col2, col3 = st.columns(3)
                col1.metric(f"📍 {row['Estratégia']}", f"{row['Qtd']:.4f} {row['symbol'][:-4]}")
                col2.metric("💰 Valor", row["Total"])
                col3.metric("📊 PnL", row["PnL USDT"], delta=row["PnL %"])
            st.divider()

        st.subheader("📊 Desempenho por Estratégia")
        for nome, pos, neg, total in cards:
            st.markdown(f"**📌 {nome}**")
            c1, c2, c3 = st.columns(3)
            c1.metric("📈 Operações Positivas", pos)
            c2.metric("📉 Operações Negativas", neg)
            c3.metric("💰 Lucro Total", f"${total:.2f}")
        st.divider()

        st.subheader("📘 Histórico de Trades")
        df_full = df_full.sort_values("Data/Hora", ascending=False)
        st.dataframe(
            df_full[["Estratégia", "symbol", "Tipo", "Qtd", "Preço", "Total", "PnL USDT", "PnL %", "📍", "Contexto", "Data/Hora"]],
            use_container_width=True
        )

        st.subheader("📈 Análises Visuais")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📉 Lucro por Ativo**")
            lucro_ativos = df_realizadas.groupby("symbol")["pnl_num"].sum().to_frame(name="Lucro").T
            st.bar_chart(lucro_ativos)

        with col2:
            st.markdown("**📆 Evolução Diária do Lucro**")
            df_diario = df_realizadas.groupby("Data")["pnl_num"].sum().cumsum().to_frame(name="Lucro Acumulado")
            st.line_chart(df_diario)

with tab2:
    if operacoes_realizadas:
        hoje = date.today()
        df_hoje = pd.concat(operacoes_realizadas)
        df_hoje = df_hoje[df_hoje["Data"] == hoje]

        st.subheader(f"📆 Resultado de Hoje ({hoje.strftime('%d/%m/%Y')})")
        if not df_hoje.empty:
            total_hoje = df_hoje["pnl_num"].sum()
            pos_hoje = df_hoje[df_hoje["pnl_num"] > 0].shape[0]
            neg_hoje = df_hoje[df_hoje["pnl_num"] <= 0].shape[0]

            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Lucro do Dia", f"${total_hoje:.2f}")
            c2.metric("📈 Trades Positivos", pos_hoje)
            c3.metric("📉 Trades Negativos", neg_hoje)

            st.dataframe(df_hoje[["Estratégia", "symbol", "Tipo", "Qtd", "Preço", "Total", "PnL USDT", "PnL %", "Data/Hora"]])
        else:
            st.info("Nenhuma operação realizada hoje.")
