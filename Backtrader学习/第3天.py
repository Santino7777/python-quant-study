# 练习：实现双均线策略，使用 backtrader 库并设置短期与长期均线  # 顶部注释说明脚本目的

import pandas as pd  # 导入 pandas 以便处理行情数据
import backtrader as bt  # 导入 backtrader 作为回测框架
from yahooquery import Ticker  # 导入 yahooquery 的 Ticker 用来抓取雅虎财经数据


class DoubleMA_Strategy(bt.Strategy):  # 定义一个继承自 bt.Strategy 的双均线策略
    params = (  # 声明策略参数的名字和默认值
        ('short_period', 10),  # 短期均线长度默认 10
        ('long_period', 30)  # 长期均线长度默认 30
    )  # 结束参数元组定义

    def __init__(self):  # 初始化策略时创建所需的指标
        self.short_ma = bt.indicators.SMA(period=self.p.short_period)  # 根据短期参数生成简单移动平均
        self.long_ma = bt.indicators.SMA(period=self.p.long_period)  # 根据长期参数生成简单移动平均

    def next(self):  # 每根新 K 线触发一次 next 方法
        if not self.position:  # 如果当前没有持仓
            if self.short_ma[0] > self.long_ma[0]:  # 当短期均线在最新 bar 上穿长期均线
                self.buy()  # 发出买入指令建立多头
        elif self.short_ma[0] < self.long_ma[0]:  # 如果已有仓位且短期均线跌破长期均线
            self.sell()  # 发出卖出指令平仓


def run_backtesting():  # 定义函数执行数据准备与回测
    ticker = input("请输入股票代码: ")  # 读取用户输入的标的代码
    stock = Ticker(ticker)  # 创建 Ticker 对象以便下载数据
    df = stock.history(period='1y')  # 抓取近一年历史行情
    df_ori = df.columns  # 记录原始列名供调试查看
    print(f'原始数据的列名为: {df_ori}')  # 打印原始列名
    df = df.reset_index()  # 把索引恢复成列，方便后续筛选
    df = df[['date', 'open', 'high', 'low', 'close', 'volume']]  # 只保留 backtrader 所需的基本列
    df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']  # 重命名列以符合 backtrader 格式

    df['datetime'] = pd.to_datetime(df['datetime'], utc=True).dt.tz_localize(None)  # 转为时间戳并移除时区便于作为索引
    df.set_index('datetime', inplace=True)  # 把 datetime 设置为索引供 backtrader 使用

    cerebro = bt.Cerebro()  # 实例化 Cerebro 引擎
    cerebro.addstrategy(DoubleMA_Strategy)  # 把双均线策略添加到引擎

    data = bt.feeds.PandasData(dataname=df)  # 将 pandas DataFrame 包装成 backtrader 数据源
    cerebro.adddata(data)  # 把数据源注入回测引擎
    cerebro.broker.setcash(10000)  # 设置初始资金为 10000
    cerebro.broker.setcommission(commission=0.001)  # 设置双向交易佣金为 0.1%
    cerebro.addsizer(bt.sizers.FixedSize, stake=10)  # 指定每次开仓数量为 100 股

    print(f'初始资金: {cerebro.broker.getvalue():.2f}')  # 输出回测前的资金
    cerebro.run()  # 运行回测
    print(f'最终资金: {cerebro.broker.getvalue():.2f}')  # 输出回测后的资金
    cerebro.plot()  # 绘制交易过程图表


if __name__ == "__main__":  # 仅在脚本直接运行时执行回测
    run_backtesting()  # 调用函数开始回测
