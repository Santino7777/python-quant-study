'''
第4天：
	需要学习新的库用了获取股票数据.
	回测双均线策略，分析回测结果。
'''
import pandas as pd  # 导入pandas并命名为pd，用于数据处理
from alpha_vantage.timeseries import TimeSeries  # 从Alpha Vantage库导入时间序列接口
from datetime import datetime  # 导入datetime用于时间处理
import backtrader as bt  # 导入Backtrader并命名为bt，用于回测框架



def get_daily_data(symbol, API_Key):  # 定义函数，获取指定股票的日线数据
    ts = TimeSeries(key=API_Key, output_format='pandas')  # 初始化TimeSeries客户端，返回pandas格式
    data, meta_data = ts.get_daily(symbol=symbol, outputsize='full')    # 获取20年的数据
    data = data.rename(columns={  # 重命名列名为常见OHLCV格式
        '1. open': 'Open',  # 开盘价
        '2. high': 'High',  # 最高价
        '3. low': 'Low',    # 最低价
        '4. close': 'Close',  # 收盘价
        '5. volume': 'Volume'  # 成交量
    })
    data.index = pd.to_datetime(data.index)  # 将索引转换为时间戳

    # 获取一年的数据.
    one_year_ago = datetime.now() - pd.DateOffset(years=1)  # 计算一年前的时间点
    data = data[data.index >= one_year_ago]  # 仅保留最近一年的数据
    data = data.sort_index()  # 按时间索引升序排序
    return data  # 返回处理后的DataFrame

class TestStrategy(bt.Strategy):  # 定义Backtrader策略类
    def __init__(self):  # 初始化指标
        self.sma5 = bt.indicators.SMA(period=5)  # 5日简单移动平均线
        self.sma20= bt.indicators.SMA(period=20)  # 20日简单移动平均线

    def next(self):  # 每个新bar执行一次
        if not self.position:  # 无持仓时判断买入信号
            if self.sma5[0] > self.sma20[0]:  # 短均线上穿长均线则买入
                self.buy()  # 执行买入
        elif self.sma5[0] < self.sma20[0]:  # 有持仓且短均线下穿长均线则卖出
            self.sell()  # 执行卖出

def run_backtest():  # 封装回测流程
    data = get_daily_data(symbol, API_Key)  # 获取指定股票日线数据
    df = bt.feeds.PandasData(dataname=data)  # 将pandas数据封装为Backtrader数据源

    cerebro = bt.Cerebro()  # 创建回测主引擎
    cerebro.addstrategy(TestStrategy)  # 添加策略
    cerebro.adddata(df)  # 加载数据源
    cerebro.broker.setcash(100000)  # 设置初始资金为10000
    cerebro.broker.setcommission(commission=0.001)  # 设置手续费比例为千分之一
    cerebro.addsizer(bt.sizers.FixedSize, stake=10)  # 固定每次买入30股

    print(f"初始资金: {cerebro.broker.getvalue(): .2f}")  # 打印初始资金
    cerebro.run()  # 运行回测
    print(f"回测结果资金: {cerebro.broker.getvalue():.2f}")  # 打印回测结束资金
    cerebro.plot()  # 绘制回测图形（需本地环境支持图形界面）

if __name__ == "__main__":  # 作为脚本直接运行时执行
    API_Key = 'LNCEEYGQUGYZCRGO'  # Alpha Vantage API 密钥（请替换为你自己的）
    symbol = '300001.SZ'  # 设置股票代码为300001.SZ
    df = get_daily_data(symbol, API_Key)  # 先拉取数据以校验接口工作
    run_backtest()  # 启动回测