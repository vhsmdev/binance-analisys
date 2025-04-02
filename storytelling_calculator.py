import pandas as pd

def format_pct(value):
    return f"{value:.2f}%" if pd.notnull(value) else "-"

def format_usdt(value):
    return f"${value:.2f}" if pd.notnull(value) else "-"

def processar_trades_completos(df_orders, df_price, strategy_name):
    symbol = df_orders["symbol"].iloc[0]
    current_price = float(df_price[df_price["symbol"] == symbol]["current_price"].values[0])
    df = df_orders[df_orders["symbol"] == symbol].sort_values("time").copy()

    historico = []
    preco_medio = 0
    quantidade_total = 0
    resultado_realizado = 0

    for _, row in df.iterrows():
        row_time = pd.to_datetime(row["time"], unit="ms")
        price = float(row["price"])
        qty = float(row["qty"])
        quote = float(row["quoteQty"])

        if row["isBuyer"]:  # Compra
            if quantidade_total < 0:
                # Encerrando short
                lucro = (preco_medio - price) * min(abs(quantidade_total), qty)
                lucro_pct = ((preco_medio / price) - 1) * 100 if price > 0 else 0
                resultado_realizado += lucro

                quantidade_total += qty
                if quantidade_total > 0:
                    preco_medio = price  # nova compra
                elif quantidade_total == 0:
                    preco_medio = 0

                historico.append({
                    "Estratégia": strategy_name,
                    "symbol": symbol,
                    "Tipo": "Compra",
                    "Qtd": qty,
                    "Preço": format_usdt(price),
                    "Total": format_usdt(quote),
                    "PnL USDT": format_usdt(lucro),
                    "PnL %": format_pct(lucro_pct),
                    "📍": "📈" if lucro > 0 else "📉" if lucro < 0 else "⬜",
                    "Contexto": f"Compra de {qty:.2f} {symbol[:-4]} a {format_usdt(price)}",
                    "Data/Hora": row_time
                })
            else:
                preco_total = preco_medio * quantidade_total + price * qty
                quantidade_total += qty
                preco_medio = preco_total / quantidade_total if quantidade_total != 0 else 0

                historico.append({
                    "Estratégia": strategy_name,
                    "symbol": symbol,
                    "Tipo": "Compra",
                    "Qtd": qty,
                    "Preço": format_usdt(price),
                    "Total": format_usdt(quote),
                    "PnL USDT": "-",
                    "PnL %": "-",
                    "📍": "",
                    "Contexto": f"Compra de {qty:.2f} {symbol[:-4]} a {format_usdt(price)}",
                    "Data/Hora": row_time
                })

        else:  # Venda
            if quantidade_total > 0:
                # Encerrando posição comprada
                lucro = (price - preco_medio) * qty
                lucro_pct = ((price / preco_medio) - 1) * 100 if preco_medio > 0 else 0
                resultado_realizado += lucro

                quantidade_total -= qty
                if quantidade_total == 0:
                    preco_medio = 0

                historico.append({
                    "Estratégia": strategy_name,
                    "symbol": symbol,
                    "Tipo": "Venda",
                    "Qtd": qty,
                    "Preço": format_usdt(price),
                    "Total": format_usdt(quote),
                    "PnL USDT": format_usdt(lucro),
                    "PnL %": format_pct(lucro_pct),
                    "📍": "📈" if lucro > 0 else "📉" if lucro < 0 else "⬜",
                    "Contexto": f"Venda de {qty:.2f} {symbol[:-4]} a {format_usdt(price)}",
                    "Data/Hora": row_time
                })

            else:
                # Abrindo ou ampliando posição short
                preco_total = preco_medio * abs(quantidade_total) + price * qty
                quantidade_total -= qty
                preco_medio = preco_total / abs(quantidade_total) if quantidade_total != 0 else 0

                historico.append({
                    "Estratégia": strategy_name,
                    "symbol": symbol,
                    "Tipo": "Venda",
                    "Qtd": qty,
                    "Preço": format_usdt(price),
                    "Total": format_usdt(quote),
                    "PnL USDT": "-",
                    "PnL %": "-",
                    "📍": "",
                    "Contexto": f"Venda de {qty:.2f} {symbol[:-4]} a {format_usdt(price)} (abrindo short)",
                    "Data/Hora": row_time
                })

    # Posição atual
    if abs(quantidade_total) > 0.00001:
        if quantidade_total > 0:
            pnl_flutuante = (current_price - preco_medio) * quantidade_total
            pnl_pct = ((current_price / preco_medio) - 1) * 100 if preco_medio > 0 else 0
        else:
            pnl_flutuante = (preco_medio - current_price) * abs(quantidade_total)
            pnl_pct = ((preco_medio / current_price) - 1) * 100 if current_price > 0 else 0

        df_posicao = pd.DataFrame([{
            "Estratégia": strategy_name,
            "symbol": symbol,
            "Tipo": "Posição Atual",
            "Qtd": quantidade_total,
            "Preço": format_usdt(current_price),
            "Total": format_usdt(current_price * quantidade_total),
            "PnL USDT": format_usdt(pnl_flutuante),
            "PnL %": format_pct(pnl_pct),
            "📍": "🟢" if pnl_flutuante >= 0 else "🔴",
            "Contexto": f"Saldo atual de {quantidade_total:.4f} {symbol[:-4]} a {format_usdt(current_price)}",
            "Data/Hora": pd.NaT
        }])
    else:
        df_posicao = pd.DataFrame()

    return pd.DataFrame(historico), df_posicao
