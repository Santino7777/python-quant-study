'''
第1天：
	安装并配置Backtrader，了解其基本架构。
	练习：编写一个简单的Backtrader脚本，和获取股票数据。
'''

import pandas as pd
import backtrader as bt
from yahooquery import Ticker

class SMA(bt.Strategy): #继承自 bt.Strategy 基类，EMA 类将拥有 bt.Strategy 的所有功能，并可以添加或修改自己的功能

    def __init__(self):      # 初始化均线指标,init是类的构造函数，初始化时调用
        self.sma5 = bt.indicators.SMA(period=5)
        self.sma10 = bt.indicators.SMA(period=10)
        self.sma40 = bt.indicators.SMA(period=40)

    def next(self):             #next方法在每个时间步调用
        if not self.position:
            if self.sma5[0] > self.sma10[0] and self.sma10[0] > self.sma40[0]:
                self.buy()
        elif self.sma5[0] < self.sma10[0] and self.sma10[0] < self.sma40[0]:
            self.sell()

    def notify_order(self, order):  # 订单状态通知
        if order.status in [order.Completed]: # 订单完成,买入或卖出 order是订单对象，self是策略对象
            if order.isbuy(): #isbuy方法检查订单是否为买入订单
                print(f"买入: {order.executed.price: .2f}")
            elif order.issell():
                print(f"卖出: {order.executed.price: .2f}")

def run_backtesting():
    ticker = input(f"请输入股票代码: ")
    stock = Ticker(ticker)
    data = stock.history(start='2024-11-11', end='2025-11-11')

    data = data.reset_index()
    data = data[['date', 'open', 'high', 'low', 'adjclose', 'volume']]
    data.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    data['datetime'] = pd.to_datetime(data['datetime'])
    data.set_index('datetime', inplace=True)
    
         # 查看DataFrame的基本信息
    print("=== DataFrame基本信息 ===")
    print(f"数据形状: {data.shape}")  # (行数, 列数)
    print(f"列名: {data.columns.tolist()}")

    cerebro = bt.Cerebro()
    cerebro.addstrategy(SMA)
    df = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(df) # 添加数据到Cerebro引擎，是用PandasData数据源，adddata方法添加数据是Cerebro类的方法
    cerebro.broker.setcash(10000)  # 设置初始资金，setcash是Cerebro类的方法
    cerebro.broker.setcommission(commission=0.001) # 设置交易佣金，setcommission是Cerebro类的方法
    cerebro.addsizer(bt.sizers.FixedSize, stake=10) #addsizer方法设置每次交易的股数,是Cerebro类的方法，bt.sizers.FixedSize 是固定大小的仓位管理器


    print(f"初始资金: {cerebro.broker.getvalue(): .2f}")
    cerebro.run()
    print(f"最终资金: {cerebro.broker.getvalue(): .2f}")

    cerebro.plot()

if __name__ == "__main__":   # 程序入口，判断是否为主程序执行
    run_backtesting()
