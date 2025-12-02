'''
第13天:
	**练习：**在策略中实现MACD并设定柱状图判断逻辑，回测并输出策略表现图表。
'''

# 上述三引号包裹的是模块文档字符串（module docstring），用于说明本脚本的练习主题与目标，不参与代码执行

import backtrader as bt  # 导入 Backtrader 回测框架，并简写为 bt，后续调用更简洁
import pandas as pd      # 导入 Pandas 数据分析库，用于读取 CSV、处理时间索引等

# 读取数据：从本地 CSV 构建 Backtrader 可用的数据源（PandasData）
def load_data():                                           # 定义数据加载函数，返回一个数据源对象供 Cerebro 使用
    file_path = './COIN_year_data.csv'                     # 数据文件路径，需包含列：date、open、high、low、close、volume
    df = pd.read_csv(file_path)                            # 使用 Pandas 读取 CSV 为 DataFrame
    df['date'] = pd.to_datetime(df['date'])                # 将日期字符串转换为时间戳类型，便于设为索引与时间序列处理
    df.set_index('date', inplace=True)                     # 设置日期列为索引，符合 Backtrader 读取数据的时间线要求
    df['openinterest'] = 0                                 # 补充 openinterest（持仓兴趣）列，常见股票数据没有，置 0 即可

    data = bt.feeds.PandasData(dataname=df)                # 将 DataFrame 封装为 Backtrader 的 PandasData 数据源
    return data                                            # 返回数据源对象，供后续 Cerebro.adddata 添加到引擎

class MACD_Strategy(bt.Strategy):                          # 定义策略类，继承 Backtrader 的 Strategy
    params = (
        ('take_profit', 0.05),    # 止盈阈值：涨幅达到 +5% 触发平仓
        ('stop_loss', 0.2)        # 止损阈值：跌幅达到 -20% 触发平仓（0.2 表示 20%）
    )

    def __init__(self):                                     # 初始化：回测开始时调用，用于创建指标与状态变量
        macd = bt.indicators.MACD(self.data)                # 添加 MACD 指标（默认 fast=12, slow=26, signal=9），基于收盘价
        self.macd_hist = macd.macd - macd.signal            # 手动计算 MACD 柱状图：DIF（macd）减去 DEA（signal）
        self.crossover = bt.indicators.CrossOver(self.macd_hist, 0)  # 构造柱状图与 0 的交叉信号：上穿>0，下穿<0
        self.buy_price = None                                # 记录最近一次买入价格，用于计算涨跌幅
        self.buy_date = None                                 # 记录最近一次买入日期，便于日志输出

    def log(self, txt):                                     # 简易日志函数：统一输出当前日期与信息文本
        dt = self.datas[0].datetime.date(0)                 # 获取当前 bar 的日期对象（0 表示当前；ago 索引）
        print(f"{dt.isoformat()} {txt}")                   # 以 ISO 格式打印日期与日志内容，如 2021-06-01 买入 @ 123.45

    def next(self):                                         # 每个新 bar 到来时调用：编写进出场逻辑
        current_date = self.datas[0].datetime.date(0)       # 当前 bar 的日期（datetime.date 对象）
        current_price = self.data.close[0]                  # 当前收盘价（用于下单与涨跌幅计算）
        if not self.position:                               # 无持仓时：寻找做多入场信号
            if self.crossover > 0:                          # 柱状图上穿 0（CrossOver>0）：动能由空转多，视为买入信号
                self.buy()                                  # 执行买入（下单数量由 sizer 决定）
                self.buy_price = current_price              # 记录买入价，用于后续止盈/止损计算
                self.buy_date = current_date                # 记录买入日期，用于日志输出
                self.log(f"买入时间: {current_date}, 买入价格: {current_price:.2f}")  # 打印入场信息

        else:                                               # 已有持仓时：依据止盈/止损或动能反转离场
            # 当前涨跌幅（相对买入价）：正值表示盈利，负值表示亏损
            change = (current_price - self.buy_price) / self.buy_price
            reason = None                                    # 离场原因描述（用于日志）

            # 止盈：涨幅达到阈值（如 +5%）
            if change >= self.params.take_profit:
                reason = '止盈触发'

            # 止损：跌幅达到阈值（如 -20%）
            elif change <= -self.params.stop_loss:
                reason = '止损触发'

            # MACD 平仓：柱状图下穿 0（CrossOver<0），动能由多转空
            elif self.crossover < 0:
                reason = 'MACD 死叉'

            if reason:                                       # 若满足任一离场条件，则执行卖出平仓
                self.sell()                                  # 卖出以平掉持仓
                self.log(f"{reason}")                       # 打印离场原因
                self.log(f"买入时间: {self.buy_date}, 买入价格:{self.buy_price:.2f}")  # 打印入场信息
                self.log(f"卖出时间: {current_date}, 卖出价格: {current_price:.2f}")     # 打印离场信息
                self.log(f"涨跌幅: {change:.2%}")           # 打印此次交易的收益率（百分比格式）
                self.buy_price = None                        # 清空记录，准备下一次交易
                self.buy_date = None                         # 清空记录，准备下一次交易


def run_testing():                                          # 回测运行入口：配置引擎、添加策略与数据、执行并绘图
    cerebro = bt.Cerebro()                                  # 创建回测引擎实例
    cerebro.addstrategy(MACD_Strategy)                      # 添加策略类（可在此传入自定义参数）
    data = load_data()                                      # 加载数据源（PandasData）
    cerebro.adddata(data)                                   # 将数据源添加到引擎（默认作为第 0 个数据）
    cerebro.broker.setcash(100000)                          # 设置初始资金为 100,000
    cerebro.broker.setcommission(commission=0.01)           # 设置佣金率为 1%（示例值，实际应按市场调整）
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)        # 固定下单手数：每次买入 100 单位

    print(f" 初始资金: {cerebro.broker.getvalue():.2f}")   # 打印开始时账户资金
    cerebro.run()                                           # 运行回测（遍历所有 bar 调用 next）
    print(f" 最终资金: {cerebro.broker.getvalue():.2f}")   # 打印回测结束时账户资金
    cerebro.plot()                                          # 绘制图表（价格、指标等），便于可视化策略效果

if __name__ == "__main__":                                 # Python 入口保护：仅脚本直接运行时执行回测
    run_testing()                                           # 调用回测主函数，启动策略执行与结果输出


'''' 算了就这样吧.   有显示时间就显示吧. 打印出来的前面有时间是卖出时间. '''  # 额外说明的字符串：作为注释用途，不参与逻辑