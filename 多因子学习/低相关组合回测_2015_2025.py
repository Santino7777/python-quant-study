import warnings
warnings.filterwarnings("ignore")

import math
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import timedelta


def get_nasdaq100_tickers() -> list:
    """
    Return the user-provided NASDAQ 100 tickers list.
    Duplicates are removed; tickers are uppercased and stripped.
    """
    nasdaq_100_tickers = [
        "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "AVGO", "META", "TSLA", "NFLX",
        "COST", "ASML", "PLTR", "AMD", "CSCO", "AZN", "TMUS", "MU", "PEP", "ISRG",
        "LIN", "SHOP", "INTU", "AMGN", "LRCX", "APP", "AMAT", "QCOM", "PDD", "INTC",
        "GILD", "BKNG", "KLAC", "TXN", "ARM", "ADBE", "PANW", "CRWD", "HON", "ADI",
        "CEG", "VRTX", "ADP", "CMCSA", "MELI", "SBUX", "ORLY", "CDNS", "DASH", "REGN",
        "MAR", "CTAS", "MDLZ", "SNPS", "MNST", "ABNB", "MRVL", "AEP", "CSX", "ADSK",
        "TRI", "WDAY", "FTNT", "WBD", "DDOG", "IDXX", "PYPL", "ROST", "PCAR", "EA",
        "MSTR", "BKR", "ROP", "XEL", "NXPI", "EXC", "FAST", "ZS", "TTWO", "FANG",
        "AXON", "CCEP", "PAYX", "CPRT", "TEAM", "KDP", "CHTR", "VRSK", "MNST", "CTSH",
        "CSGP", "BIIB", "DXCM", "ON", "ANSS", "ILMN", "LULU", "SPLK", "FISV", "ODFL",
        "MCHP", "DLTR", "ALGN", "NTES", "JD", "ZM", "SWKS", "BIDU", "ATVI", "REGN",
    ]
    tickers = [t.upper().strip() for t in nasdaq_100_tickers]
    return sorted(set(tickers))


def download_prices(tickers: list, start: str, end: str) -> pd.DataFrame:
    """Download adjusted daily close prices for tickers using yfinance."""
    data = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    # With auto_adjust=True, 'Close' is adjusted; ensure 2D frame of closes
    if isinstance(data.columns, pd.MultiIndex):
        close = data['Close']
    else:
        close = data[['Close']]
    if close.columns.nlevels > 1:
        close.columns = close.columns.get_level_values(0)
    close = close.sort_index()
    # Drop columns with too little data
    min_days = 200
    valid = close.columns[close.notna().sum() >= min_days]
    return close[valid]


def daily_returns(close: pd.DataFrame) -> pd.DataFrame:
    ret = close.pct_change().replace([np.inf, -np.inf], np.nan).dropna(how='all')
    return ret


def quarter_starts(index: pd.DatetimeIndex, start: str, end: str) -> list:
    """Build quarter start dates aligned to the trading calendar in index."""
    qs = pd.date_range(start=start, end=end, freq='QS')
    aligned = []
    for d in qs:
        # if the exact date not in index, shift to next available trading day
        if d in index:
            aligned.append(d)
        else:
            # find the next index date after d
            future = index[index >= d]
            if len(future) == 0:
                break
            aligned.append(future[0])
    return aligned


def select_low_corr(ret_window: pd.DataFrame, k: int = 10) -> list:
    """
    Select k tickers using the described low-correlation heuristic:
    1) First: smallest avg |corr| with all others
    2) Second: smallest |corr| with the first
    3+) Each next: smallest avg |corr| with already selected
    """
    # Filter columns with enough data
    min_days = 60
    cols = ret_window.columns[ret_window.notna().sum() >= min_days]
    ret_window = ret_window[cols]
    if len(ret_window.columns) < k:
        k = len(ret_window.columns)
    corr = ret_window.corr()
    abs_corr = corr.abs()

    selected = []

    # 1) first stock
    avg_abs = abs_corr.apply(lambda s: s.drop(labels=s.name).mean(), axis=1)
    first = avg_abs.idxmin()
    selected.append(first)

    if len(selected) >= k:
        return selected

    # 2) second stock: smallest |corr| with first
    second = abs_corr[first].drop(labels=first).idxmin()
    selected.append(second)

    while len(selected) < k:
        remaining = [c for c in corr.columns if c not in selected]
        # For each candidate, compute avg |corr| with selected set
        scores = {}
        for c in remaining:
            scores[c] = abs_corr.loc[c, selected].mean()
        # pick the minimal score
        nxt = min(scores, key=scores.get)
        selected.append(nxt)
    return selected


def simulate_portfolio(ret: pd.DataFrame, rebalance_dates: list, lookback_months: int = 6, k: int = 10, initial_wealth: float = 1_000_000.0) -> pd.Series:
    """
    Simulate equal-weight portfolio rebalanced quarterly using low-correlation selection.
    Portfolio return on each day within the holding window is the simple average of constituent returns.
    """
    wealth = pd.Series(index=ret.index, dtype=float)
    wealth.iloc[0] = initial_wealth

    # Build holding periods
    for i, t0 in enumerate(rebalance_dates):
        # Define t1 as next rebalance start or end of data
        t1 = rebalance_dates[i + 1] if i + 1 < len(rebalance_dates) else ret.index[-1] + timedelta(days=1)

        # Lookback window: past 6 months
        lb_start = t0 - pd.DateOffset(months=lookback_months)
        window = ret[(ret.index >= lb_start) & (ret.index < t0)]
        if window.shape[0] < 40:
            # Not enough data, skip selection, carry wealth forward
            period_idx = ret[(ret.index >= t0) & (ret.index < t1)].index
            wealth.loc[period_idx] = wealth.shift(1).loc[period_idx]
            continue

        selected = select_low_corr(window, k=k)
        if len(selected) == 0:
            period_idx = ret[(ret.index >= t0) & (ret.index < t1)].index
            wealth.loc[period_idx] = wealth.shift(1).loc[period_idx]
            continue

        period_ret = ret[selected]
        period_idx = period_ret[(period_ret.index >= t0) & (period_ret.index < t1)].index

        # Equal weight daily portfolio return
        ew_ret = period_ret.loc[period_idx].mean(axis=1).fillna(0.0)

        # Compound wealth
        for d in period_idx:
            prev = wealth.shift(1).loc[d]
            if pd.isna(prev):
                # initialize previous wealth if missing
                prev = wealth.loc[wealth.index[wealth.index.get_loc(d)-1]] if wealth.index.get_loc(d) > 0 else initial_wealth
            wealth.loc[d] = prev * (1.0 + ew_ret.loc[d])

    wealth = wealth.ffill()
    return wealth


def max_drawdown(wealth: pd.Series) -> float:
    cummax = wealth.cummax()
    dd = (wealth / cummax) - 1.0
    return dd.min()  # negative value


def sharpe_ratio_daily(ret_series: pd.Series) -> float:
    ret_series = ret_series.dropna()
    mu = ret_series.mean()
    sigma = ret_series.std(ddof=1)
    if sigma == 0 or np.isnan(sigma):
        return np.nan
    return mu / sigma


def annualize_sharpe(sharpe_daily: float, periods_per_year: int = 252) -> float:
    if pd.isna(sharpe_daily):
        return np.nan
    return sharpe_daily * math.sqrt(periods_per_year)


def run_backtest():
    start = '2014-06-01'  # include lookback buffer
    end = '2025-12-31'
    tickers = get_nasdaq100_tickers()

    print(f"Downloading prices for {len(tickers)} tickers...")
    close = download_prices(tickers, start=start, end=end)
    ret = daily_returns(close)

    # Rebalance schedule (quarter starts)
    rebal = quarter_starts(ret.index, start='2015-01-01', end='2025-12-31')

    print(f"Simulating quarterly portfolio from {rebal[0].date()} to {rebal[-1].date()}...")
    wealth = simulate_portfolio(ret, rebal, lookback_months=6, k=10, initial_wealth=1_000_000.0)
    port_ret = wealth.pct_change()

    mdd = max_drawdown(wealth)
    sr_daily = sharpe_ratio_daily(port_ret)
    sr_annual = annualize_sharpe(sr_daily)

    # Benchmarks: QQQ and SPY
    bench = yf.download(["QQQ","SPY"], start=start, end=end, auto_adjust=True, progress=False)['Close']
    bench = bench.sort_index()
    qqq = bench['QQQ']
    spy = bench['SPY']
    qqq_ret = qqq.pct_change().dropna()
    spy_ret = spy.pct_change().dropna()
    # Normalize QQQ/SPY to start at 1 on their first available date
    qqq_wealth_norm = (1 + qqq_ret).cumprod()
    spy_wealth_norm = (1 + spy_ret).cumprod()

    qqq_mdd = max_drawdown(qqq_wealth_norm.reindex(wealth.index).dropna())
    spy_mdd = max_drawdown(spy_wealth_norm.reindex(wealth.index).dropna())
    qqq_sr_annual = annualize_sharpe(sharpe_ratio_daily(qqq_ret))
    spy_sr_annual = annualize_sharpe(sharpe_ratio_daily(spy_ret))

    # Print summary
    print("\n==== Performance Summary (2015–2025) ====")
    total_return = wealth.dropna().iloc[-1] / wealth.dropna().iloc[0] - 1
    print(f"Portfolio total return: {total_return*100:.2f}%")
    print(f"Portfolio max drawdown: {mdd*100:.2f}%")
    print(f"Portfolio Sharpe (daily): {sr_daily:.3f}")
    print(f"Portfolio Sharpe (annual): {sr_annual:.3f}")
    print(f"QQQ max drawdown: {qqq_mdd*100:.2f}% | Sharpe annual: {qqq_sr_annual:.3f}")
    print(f"SPY max drawdown: {spy_mdd*100:.2f}% | Sharpe annual: {spy_sr_annual:.3f}")

    # Plot wealth curves (normalized to the same start)
    fig, ax = plt.subplots(figsize=(10, 6))
    base = wealth.dropna().iloc[0]
    ax.plot(wealth.index, wealth / base, label='Low-Corr Portfolio')
    ax.plot(qqq_ret.index, (1 + qqq_ret).cumprod(), label='QQQ (Normalized)')
    ax.plot(spy_ret.index, (1 + spy_ret).cumprod(), label='SPY (Normalized)')
    ax.set_title('Wealth Curves: Low-Correlation Portfolio vs QQQ/SPY (2015–2025)')
    ax.set_ylabel('Growth Multiple')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('low_corr_portfolio_2015_2025.png', dpi=150)
    print("Saved plot: low_corr_portfolio_2015_2025.png")


if __name__ == '__main__':
    run_backtest()