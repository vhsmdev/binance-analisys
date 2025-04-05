import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, date, timezone
from binance_client import get_trades, get_price, get_balance, get_open_orders
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
    "BNBUSDT": "Breakx"
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

meta_dia = 1.00  # 🎯 Meta de lucro diário em USDT

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
        progresso = min(lucro_hoje / meta_dia, 1.0)

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



    # 📊 ANÁLISE GERAL
    with tab1:
        st.subheader("📅 Filtro de Período")
        col1, col2 = st.columns(2)
        data_inicial = col1.date_input("Data Inicial", value=date.today().replace(day=1))
        data_final = col2.date_input("Data Final", value=date.today())

        df_periodo = df_realizadas[
            (df_realizadas["Data"] >= data_inicial) &
            (df_realizadas["Data"] <= data_final)
        ]

        total_realizado = df_periodo["pnl_num"].sum()
        lucro_medio = df_periodo["pnl_num"].mean()
        total_em_ativos = sum(saldos_usdt)

        st.subheader("💼 Visão Geral da Carteira")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💵 Lucro Realizado (Período)", f"${total_realizado:.2f}")
        col2.metric("📈 Lucro Médio por Operação", f"${lucro_medio:.2f}")
        col3.metric("💰 Valor Atual em Ativos", f"${total_em_ativos:.2f}")
        col4.metric("💵 Saldo Atual em USDT", f"${usdt_saldo:.2f}")

        st.subheader("📆 Resultado Diário (Comparado à Meta)")

        df_diaria = (
            df_periodo.groupby("Data")["pnl_num"]
            .sum()
            .reset_index()
            .rename(columns={"pnl_num": "Lucro"})
        )
        df_diaria["Status"] = df_diaria["Lucro"].apply(lambda x: "📈 Positivo" if x > 0 else "📉 Negativo")
        df_diaria["Meta Batida"] = df_diaria["Lucro"].apply(lambda x: "✅ Sim" if x >= meta_dia else "❌ Não")

        st.dataframe(df_diaria[["Data", "Lucro", "Status", "Meta Batida"]], use_container_width=True)


        st.subheader("📦 Ativos em Carteira (Valorização Atual)")
        df_saldos = pd.DataFrame([
            {
                "Ativo": token,
                "Qtd": qtd,
                "Preço Atual (USDT)": get_price(f"{token}USDT"),
                "Valor Total (USDT)": qtd * get_price(f"{token}USDT")
            }
            for token, qtd in saldos_tokens
        ])
        st.dataframe(df_saldos, use_container_width=True)

        if all_posicoes:
            st.subheader("📌 Posições Abertas (PnL Flutuante)")
            df_pos = pd.concat(all_posicoes, ignore_index=True)
            df_pos["Token"] = df_pos["symbol"].str.replace("USDT", "")
            df_pos_mostrar = df_pos[["Estratégia", "Token", "Qtd", "Total", "PnL USDT", "PnL %"]]
            st.dataframe(df_pos_mostrar, use_container_width=True)

        st.subheader("📊 Desempenho Realizado por Estratégia")
        estrategia_grouped = df_periodo.groupby("Estratégia")
        for nome, grupo in estrategia_grouped:
            positivas = grupo[grupo["pnl_num"] > 0].shape[0]
            negativas = grupo[grupo["pnl_num"] < 0].shape[0]
            lucro_total = grupo["pnl_num"].sum()
            st.markdown(f"**📌 {nome}**")
            c1, c2, c3 = st.columns(3)
            c1.metric("📈 Operações Positivas", positivas)
            c2.metric("📉 Operações Negativas", negativas)
            c3.metric("💰 Lucro Total", f"${lucro_total:.2f}")

        st.subheader("📘 Histórico de Trades Realizados")
        df_full = df_full.sort_values("Data/Hora", ascending=False)
        st.dataframe(
            df_full[["Estratégia", "symbol", "Tipo", "Qtd", "Preço", "Total", "PnL USDT", "PnL %", "📍", "Contexto", "Data/Hora"]],
            use_container_width=True
        )

        st.subheader("📈 Evolução Diária do Lucro Realizado")
        df_diario = df_realizadas.groupby("Data")["pnl_num"].sum().cumsum().to_frame(name="Lucro Acumulado")
        st.line_chart(df_diario)
