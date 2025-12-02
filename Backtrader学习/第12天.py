'''
第12天：
	引入MACD指标，基于MACD柱状图制定交易信号。
'''
# 以上三引号包裹的是模块文档字符串（module docstring），用于说明本文件的用途与主题

import backtrader as bt  # 导入 Backtrader 回测框架，并将模块名简写为 bt，后续调用更简洁
import pandas as pd      # 导入 Pandas，用于读取 CSV 数据并进行时间索引等数据处理



# 读取数据：从本地 CSV 构建 Backtrader 可用的数据源（PandasData）
def load_data():  # 定义数据加载函数，返回一个可被 Cerebro 添加的数据馈源对象
    file_path = './BABA_year_data.csv'  # 数据文件路径，包含必须列：date、open、high、low、close、volume
    df = pd.read_csv(file_path)         # 使用 Pandas 读取 CSV 为 DataFrame
    df['date'] = pd.to_datetime(df['date'])  # 将字符串日期转换为 Pandas 的时间戳类型，便于设为索引
    df.set_index('date', inplace=True)       # 设置日期为索引，以满足 Backtrader 的时间线要求
    df['openinterest'] = 0                   # 补充 openinterest 列（持仓兴趣），多数股票数据没有，置 0 即可
    # print(df.head())                       # 可选调试：打印前几行查看格式是否正确

    data = bt.feeds.PandasData(dataname=df)  # 将 DataFrame 封装为 Backtrader 的 PandasData 数据源
    return data                              # 返回数据源对象，供后续 Cerebro.adddata 使用


class MACD_Strategy(bt.Strategy):  # 定义策略类，继承 Backtrader 的 Strategy
    params = (
        ('take_profit', 0.06),  # 止盈阈值：当涨幅达到 +6% 时触发止盈
        ('stop_loss', 0.2)      # 止损阈值：当跌幅达到 -20% 时触发止损（此处参数为 0.2，表示 20%）
    )
    '''止损还是20%比较好. '''  # 模块内说明：作者倾向使用 20% 作为止损阈值

    def __init__(self):  # 初始化：在回测开始时被调用，用来创建指标、状态变量等
        # 添加 MACD 指标（默认参数：fast=12, slow=26, signal=9；返回对象含 macd、signal、hist）
        macd = bt.indicators.MACD(self.data)  # 传入整条数据（包含 close、open 等），指标内部按需要取用收盘价

        # Backtrader 的标准 MACD 对象不直接提供 histo 属性，这里手动计算柱状图（macd - signal）
        self.macd_hist = macd.macd - macd.signal        # 柱状图：DIF（macd）减去 DEA（signal），>0 表示多头动能
        self.buy_price = None                            # 记录最近一次买入价格，用于计算当前涨跌幅


    # 加入追踪记录 Log：统一输出时间 + 文本，便于观察策略行为
    def log(self, txt):  # 日志函数，传入描述文本，自动拼接当前 K 线日期
        dt = self.datas[0].datetime.date(0) # 当前数据的日期对象（0 表示当前 bar；ago 索引）
        print(f"{dt.isoformat()} {txt}")    # ISO 格式输出日期 + 信息，例如 2021-01-05 买入 @ 123.45

    def next(self):  # 每个新 bar 到来时调用，编写进出场逻辑
        price = self.data.close[0]  # 当前收盘价（用于下单价格参考与涨跌幅计算）
        if not self.position:       # 当前无持仓：寻找做多入场信号
            # 入场条件：MACD 柱状图从非正（<=0）到正（>0），即动能由空转多，视为做多信号
            if self.macd_hist[0] > 0 and self.macd_hist[-1] <= 0:
                self.log(f"买入 @ {self.data.close[0]:.2f}")  # 记录买入价格与时点
                self.buy()                                   # 执行买入（按 sizer 设置的固定手数）
                self.buy_price = price                        # 保存买入价格，用于后续止盈止损计算
        else:                      # 已有持仓：按止盈/止损或动能反转信号进行离场
            # 用止盈止损来买卖.
            # 当前涨跌幅：正值表示盈利，负值表示亏损
            change = (price - self.buy_price) / self.buy_price

            if change >= self.params.take_profit:            # 达到止盈阈值（例如 +6%）
                self.log(f"止盈 @ {price:.2f} (+{change*100:.2f}%)")
                self.sell()                                  # 卖出平仓
                self.buy_price = None                        # 清空买入价记录
            elif change <= -self.params.stop_loss:           # 跌破止损阈值（例如 -20%）
                self.log(f" 止损 @ {price:.2f} ({change*100:.2f}%)")
                self.sell()                                  # 卖出平仓
                self.buy_price = None                        # 清空买入价记录

            # 或者柱状图反转信号也平仓：由非负（>=0）到负（<0），动能由多转空
            elif self.macd_hist[0] < 0 and self.macd_hist[-1] >=0:
                self.log(f"MACD Exit @ {price:.2f}")         # 记录动能反转导致的离场
                self.sell()                                  # 卖出平仓
                self.buy_price = None                        # 清空买入价记录


def run_testing():                               # 回测入口：配置引擎、添加策略与数据、运行并绘图
    cerebro = bt.Cerebro()                        # 创建回测引擎（Cerebro）实例
    cerebro.addstrategy(MACD_Strategy)            # 添加策略类，使用默认参数，也可在此传入自定义 params
    data = load_data()                            # 加载并封装数据源
    cerebro.adddata(data)                         # 将数据源添加到引擎（默认作为第 0 个数据）
    cerebro.broker.setcash(100000)                # 初始资金设为 100,000
    cerebro.broker.setcommission(commission=0.01) # 设置佣金率为 1%（示例值，实际应按市场与券商调整）
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)  # 固定下单手数：每次买入 100 单位
    print(f"初始资金: {cerebro.broker.getvalue():.2f}")   # 打印开局资金
    cerebro.run()                                   # 运行回测（执行所有 bar 的 next）
    print(f"最终资金: {cerebro.broker.getvalue():.2f}")   # 打印结束资金，用于对比绩效
    cerebro.plot()                                   # 绘制图表（含价格与指标），便于可视化检验


if __name__ == "__main__":  # Python 入口：仅在作为脚本运行时执行回测；被导入为模块时不运行
    run_testing()             # 调用回测主函数，触发策略执行与结果输出


    '''试一试其它的股票'''  # 额外提示的文档字符串：可以更换数据文件测试不同标的