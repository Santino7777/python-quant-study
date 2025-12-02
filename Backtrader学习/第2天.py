'''
第2天：
	设计一个双均线策略的backtrader，定义买卖规则。
'''

from yahooquery import Ticker
import pandas as pd
import backtrader as bt

class EMA(bt.Strategy):
    def __init__(self):
        self.ema5 = bt.indicators.ExponentialMovingAverage(self.data.close, period=5) 
            #exponential moving average是指数移动平均线，和SMA的区别是EMA对最新的数据更敏感，计算方法是加权平均
        self.ema20 = bt.indicators.ExponentialMovingAverage(self.data.close, period=20)
        self.crossover = bt.indicators.CrossOver(self.ema5, self.ema20)
            #crossover指标用于检测两条均线的交叉情况，当短期均线上穿长期均线时，返回1；当短期均线下穿长期均线时，返回-1；否则返回0

    def next(self):
        if not self.position:
            if (self.ema5[0] > self.ema20[0] and self.ema5[-1] <= self.ema20[-1] # 判断5日均线上穿20日均线
                    or self.crossover[0] == 1 or self.data.close[0] > self.crossover[0]): # 判断crossover指标是否为1或收盘价是否高于crossover值
                self.buy()
        elif (self.ema5[0] < self.ema20[0] and self.ema5[-1] >= self.ema20[-1]
              or self.crossover[0] == -1 or self.data.close[0] < self.crossover[0]):
            self.sell()

def run_backtesting():
    ticker = input(f"请输入股票代码: ")
    stock = Ticker(ticker)
    df = stock.history(start='2024-05-05', end='2025-05-05')
    df = df.reset_index()
    df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
    df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)

    cerebro = bt.Cerebro()
    cerebro.addstrategy(EMA)

    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    cerebro.broker.setcash(10000)
    cerebro.broker.setcommission(commission=0.001)

    cerebro.addsizer(bt.sizers.FixedSize, stake=10)

    print(f"初始资金: {cerebro.broker.getvalue():.2f}")
    cerebro.run()
    print(f"最终资金: {cerebro.broker.getvalue():.2f}")

    cerebro.plot()


if __name__ == "__main__":
    run_backtesting()
