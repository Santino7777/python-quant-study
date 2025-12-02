'''
第5天:
	练习：运行回测脚本，获取策略的收益率曲线和统计指标。
 
 
    我新申请的student API：N5UJOCR6HL6VJIPR
'''

import pandas as pd  # 导入pandas用于数据处理
import backtrader as bt  # 导入Backtrader回测框架
from alpha_vantage.timeseries import TimeSeries  # 导入Alpha Vantage的时间序列接口
from datetime import datetime  # 导入datetime用于时间计算
import matplotlib.pyplot as plt  # 导入matplotlib用于绘图


def get_daily_data(symbol, API_Key):  # 定义函数，按股票代码与API密钥获取日线数据
    ts = TimeSeries(key=API_Key, output_format='pandas')  # 初始化API客户端，返回pandas格式
    data, meta_data = ts.get_daily(symbol=symbol, outputsize='full')  # 拉取较长历史的日线数据
    data = data.rename(columns={  # 重命名列为常见OHLCV格式
        '1. open': 'Open',  # 开盘价列重命名为Open
        '2. high': 'High',  # 最高价列重命名为High
        '3. low': 'low',    # 最低价列重命名为low（与其他列大小写略不同）
        '4. close': 'Close',  # 收盘价列重命名为Close
        '5. volume': 'Volume'  # 成交量列重命名为Volume
    })
    data.index = pd.to_datetime(data.index)  # 将索引转换为时间戳类型

    one_year_ago = datetime.now() - pd.DateOffset(years=1)  # 计算一年前的日期
    data = data[data.index >= one_year_ago]  # 筛选最近一年的数据
    data = data.sort_index()  # 按时间升序排序
    return data  # 返回处理后的DataFrame

class SMA_Strategy(bt.Strategy):  # 定义简单均线策略类
    def __init__(self):  # 初始化函数，设置指标与变量
        self.sma5 = bt.indicators.SMA(period=5)  # 5日简单移动平均
        self.sma20 = bt.indicators.SMA(period=20)  # 20日简单移动平均
        self.portfolio_value = []       # 用于保存每日组合资金净值

    def next(self):  # 每个新bar到来时执行
        self.portfolio_value.append(self.broker.getvalue())  # 记录当天资金净值
        if not self.position:  # 无持仓时判断买入信号
            if self.sma5[0] > self.sma20[0]:  # 短均线高于长均线，触发买入
                self.buy()  # 执行买入
        else:  # 有持仓时判断卖出信号
            if self.sma5[0] < self.sma20[0]:  # 短均线低于长均线，触发卖出
                self.sell()  # 执行卖出

    def stop(self):  # 回测结束时执行
        # 绘制收益曲线（资金净值随时间）
        plt.figure(figsize=(10, 5))  # 设置图像大小
        plt.plot(self.portfolio_value)  # 绘制资金净值序列
        plt.title('Portfolio Value Over Time')  # 设置标题
        plt.xlabel('day')  # 设置横轴为天数（索引）
        plt.ylabel('Portfolio Value')  # 设置纵轴为资金净值
        plt.grid()  # 显示网格
        plt.tight_layout()  # 自动调整布局避免遮挡
        plt.show()  # 显示图像

def run_testing():  # 封装回测流程的函数
    data = get_daily_data(symbol, API_Key)  # 获取股票的日线数据
    df = bt.feeds.PandasData(dataname=data)  # 将pandas数据封装为Backtrader数据源

    cerebro = bt.Cerebro()  # 创建回测引擎
    cerebro.addstrategy(SMA_Strategy)  # 添加策略类
    cerebro.adddata(df)  # 加载数据源
    cerebro.broker.setcash(100000)  # 设置初始资金为10000
    cerebro.broker.setcommission(commission=0.001)  # 设置交易手续费为千分之一
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)  # 固定每次买入100股

    # 添加分析器，用于统计指标
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')  # 添加夏普比率分析器
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')  # 添加回撤分析器
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')  # 添加交易统计分析器

    print(f"初始资金: {cerebro.broker.getvalue(): .2f}")  # 打印初始资金

    result = cerebro.run()  # 运行回测，返回策略结果列表
    strat = result[0]  # 取第一个策略实例
    print(f"最终资金: {cerebro.broker.getvalue(): .2f}")  # 打印最终资金
    print(f"\n_______回测统计指标_________")  # 输出分隔标题

    drawdown = strat.analyzers.drawdown.get_analysis()  # 获取回撤分析结果
    print(f"最大回测: {drawdown['max']['drawdown']: .2f}")  # 打印最大回撤百分比

    sharpe = strat.analyzers.sharpe.get_analysis()  # 获取夏普比率结果
    print(f"夏普比率: {sharpe.get('sharperatio', '无法计算')}")  # 打印夏普比率或提示无法计算

    trades = strat.analyzers.trades.get_analysis()  # 获取交易分析结果
    print(f"总交易次数: {trades['total']['total']}")  # 打印总交易次数
    print(f"盈利次数: {trades['won']['total']}")  # 打印盈利次数
    print(f"亏损次数: {trades['lost']['total']}")  # 打印亏损次数
    print(f"胜率: {(trades['won']['total'] / trades['total']['total']): .2%}")  # 打印胜率百分比

    cerebro.plot()  # 绘制回测图形（需本地图形环境）


if __name__ == "__main__":  # 作为脚本直接运行时执行
    API_Key = 'LNCEEYGQUGYZCRGO'  # Alpha Vantage API 密钥（可替换为自己的）
    symbol = input(f"请输入股票代码: ")  # 从命令行输入股票代码
    run_testing()  # 调用回测流程
