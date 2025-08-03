import json
import os
from datetime import datetime, timezone

from binance_client import client

# Arquivo onde o histórico diário de saldos é armazenado
HISTORY_FILE = "daily_balances.json"


def _load_history():
    """Carrega o histórico de saldos salvos no arquivo JSON."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_history(history):
    """Salva o histórico de saldos no arquivo JSON."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def _today_str():
    """Retorna a data de hoje em UTC no formato YYYY-MM-DD."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_initial_balance(asset: str, current_balance: float) -> float:
    """
    Busca o saldo inicial do ativo no início do dia.
    Caso não exista registro para hoje, o saldo atual é usado como inicial
    e gravado no histórico.
    """
    history = _load_history()
    today = _today_str()

    if today not in history:
        history[today] = {}

    if asset not in history[today]:
        history[today][asset] = current_balance
        _save_history(history)

    return history[today][asset]


def get_net_transfers(asset: str) -> float:
    """
    Calcula o valor líquido de transferências e depósitos do dia para o ativo.
    Apenas movimentações ocorridas hoje (UTC) são consideradas:
    
    Net = depósitos - saques
    """
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start_ts = int(start_of_day.timestamp() * 1000)
    end_ts = int(datetime.now(timezone.utc).timestamp() * 1000)

    deposit_qty = 0.0
    withdraw_qty = 0.0

    try:
        deposits = client.get_deposit_history(coin=asset, startTime=start_ts, endTime=end_ts) or []
        deposit_qty = sum(float(d["amount"]) for d in deposits if str(d.get("status")) == "1")
    except Exception:
        # Em caso de erro na API, consideramos nenhum depósito
        deposit_qty = 0.0

    try:
        withdrawals = client.get_withdraw_history(coin=asset, startTime=start_ts, endTime=end_ts) or []
        withdraw_qty = sum(float(w["amount"]) for w in withdrawals if str(w.get("status")) == "6")
    except Exception:
        # Em caso de erro na API, consideramos nenhum saque
        withdraw_qty = 0.0

    return deposit_qty - withdraw_qty


def calculate_daily_pnl(asset: str, current_balance: float, current_price: float) -> tuple:
    """
    Calcula o PnL diário conforme a regra padrão da Binance:

    PnL = Total atual do ativo - Total inicial do ativo hoje - Valor líquido de transferências

    *Total* representa o saldo do token. O valor em USDT é calculado multiplicando
    o resultado pelo preço atual.
    """
    initial_balance = get_initial_balance(asset, current_balance)
    net_transfers = get_net_transfers(asset)

    pnl_qty = current_balance - initial_balance - net_transfers
    pnl_usdt = pnl_qty * current_price

    return pnl_qty, pnl_usdt
