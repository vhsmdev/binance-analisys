import os
from binance.client import Client
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

load_dotenv()
client = Client(os.getenv("BINANCE_API_KEY"), os.getenv("BINANCE_API_SECRET"))

ativos = ["XRP", "CAKE", "TRX", "FUN"]
symbol_map = {a: a + "USDT" for a in ativos}

def get_real_balance(token):
    for b in client.get_account()["balances"]:
        if b["asset"] == token:
            return float(b["free"]) + float(b["locked"])
    return 0.0

def get_trades(symbol):
    try:
        return client.get_my_trades(symbol=symbol)
    except Exception as e:
        print(f"[ERRO] get_trades({symbol}):", e)
        return []

def get_price(symbol):
    return float(client.get_symbol_ticker(symbol=symbol)["price"])

def get_opening_price(symbol):
    try:
        hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_ts = int(hoje.timestamp() * 1000)
        end_ts = int((hoje + timedelta(hours=1)).timestamp() * 1000)

        klines = client.get_klines(
            symbol=symbol,
            interval=Client.KLINE_INTERVAL_1HOUR,
            startTime=start_ts,
            endTime=end_ts,
            limit=1
        )
        if klines:
            return float(klines[0][1])
    except Exception as e:
        print(f"[Erro ao buscar preço abertura {symbol}]: {e}")
    return None

def calcular_entrada_liquida_e_qtd(trades):
    entrada = 0.0
    qtd_hoje = 0.0
    hoje = datetime.now(timezone.utc).date()

    for t in trades:
        if t.get("isBuyer", False):
            data_trade = datetime.fromtimestamp(t["time"] / 1000, tz=timezone.utc).date()
            if data_trade == hoje:
                valor = float(t["qty"]) * float(t["price"])
                entrada += valor
                qtd_hoje += float(t["qty"])
    return entrada, qtd_hoje

# Execução principal
print("🔍 Comparando com Binance...\n")
pnl_total = 0.0

for token in ativos:
    symbol = symbol_map[token]
    qtd_atual = get_real_balance(token)
    preco_atual = get_price(symbol)
    preco_abertura = get_opening_price(symbol)
    trades = get_trades(symbol)

    if preco_abertura is None:
        print(f"🪙 {token}")
        print("  ⚠️ Preço de abertura não encontrado.")
        print("-" * 40)
        continue

    entrada_liquida, qtd_comprada_hoje = calcular_entrada_liquida_e_qtd(trades)
    qtd_inicial = qtd_atual - qtd_comprada_hoje

    valor_final = qtd_atual * preco_atual
    valor_inicial = qtd_inicial * preco_abertura
    pnl = valor_final - valor_inicial - entrada_liquida
    pnl_total += pnl

    print(f"🪙 {token}")
    print(f"  Quantidade atual:        {qtd_atual}")
    print(f"  Preço atual:             ${preco_atual:.4f}")
    print(f"  Preço abertura (00:00):  ${preco_abertura:.4f}")
    print(f"  Valor final do ativo:    ${valor_final:.2f}")
    print(f"  Valor inicial do ativo:  ${valor_inicial:.2f}")
    print(f"  Entrada líquida (net):   ${entrada_liquida:.2f}")
    print(f"  📊 PnL do Dia (Binance):  ${pnl:+.2f}")
    print("-" * 40)

print(f"\n📊 PnL Total do Dia (modo Binance): ${pnl_total:+.2f}")
