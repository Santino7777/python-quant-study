'''
第16天：
任务目标：
编写一个自定义指标，深入理解Backtrader的Indicator类结构和用法。

练习内容：
    学习如何继承bt.Indicator类；
    理解lines、params和next()的作用；
    实现一个加权移动平均线（WMA）指标；
    将自定义指标加入现有策略，观察指标输出和信号。
'''
# 上述三引号块是模块文档字符串（docstring），用于说明练习目标和内容，不参与实际逻辑执行


import backtrader as bt  # 导入 Backtrader 回测框架，简写为 bt，后续调用更简洁
import pandas as pd      # 导入 Pandas，用于读取 CSV、处理时间索引等

# 加载数据：从 CSV 构建 Backtrader 可用的数据源（PandasData）
def load_data():                                 # 定义数据加载函数，返回一个数据源对象供 Cerebro 使用
    file_path = './BABA_year_data.csv'           # 数据文件路径，需包含列：date、open、high、low、close、volume
    df = pd.read_csv(file_path)                  # 使用 Pandas 读取 CSV 为 DataFrame
    df['date'] = pd.to_datetime(df['date'])      # 将日期字符串转换为时间戳类型，便于设为索引与时序处理
    df.set_index('date', inplace=True)           # 设置日期列为索引，符合 Backtrader 的时间线要求
    df['openinterest'] = 0                       # 补充 openinterest（持仓兴趣）列，股票数据一般没有，置 0 即可

    data = bt.feeds.PandasData(dataname=df)      # 将 DataFrame 封装为 Backtrader 的 PandasData 数据源
    return data                                  # 返回数据源对象，供后续 Cerebro.adddata 添加到引擎

# 自定义指标：加权移动平均（WMA）
class WeightMovingAverage(bt.Indicator):                  # 继承 Backtrader 的 Indicator，定义一个自定义指标
    lines = ('wma',)                                      # 指标的输出线集合，仅包含一条线：wma
    params = (('period', 10),)                            # 指标参数集合：period（加权窗口长度，默认 10）

    def __init__(self):                                   # 初始化：预计算权重等静态数据
        # 构造权重：从 1 到 period 的递增权重，例如 period=10 时权重=[1,2,...,10]
        weights = list(range(1, self.p.period + 1))       # 使用 self.p.period 读取参数（self.params 的简写）
        total_weight = sum(weights)                        # 权重总和，用于归一化

        # 将每个权重除以总和，得到归一化权重（之和为 1）；权重越大越靠近当前
        normalized_weights = []                            # 初始化归一化权重列表
        for w in weights:                                  # 遍历原始权重列表
            normalized_weights.append(w / total_weight)    # 追加归一化权重到列表

        # 缓存归一化权重到实例属性，供后续 next() 计算使用
        self.weights = normalized_weights                  # 保存权重列表为对象状态

    def next(self):                                       # 每个新 bar 到来时调用：计算当前 wma 值
        if len(self.data) >= self.p.period:               # 仅当数据样本数不少于窗口长度时才进行计算

            # 取出最近 period 根的价格（默认主数据线为收盘价），用于与权重相乘
            recent_price = list(self.data.get(size=self.p.period))  # 取得最近窗口大小的数据点

            # 创建一个列表用于存放“价格 × 权重”的乘积
            weighted_prices = []                           # 初始化乘积列表

            # 按索引遍历窗口内的价格与对应权重，逐一乘积
            for i in range(self.p.period):                 # i 从 0 到 period-1
                price = recent_price[i]                    # 取第 i 个价格
                weight = self.weights[i]                   # 取第 i 个归一化权重
                weighted_prices.append(price * weight)     # 追加乘积到列表

            # 对所有“价格 × 权重”的乘积求和，得到加权平均值（WMA）
            wma_value = sum(weighted_prices)               # 计算当前的 wma 值

            # 将计算结果写入指标输出线当前位（索引 0 表示当前 bar）
            self.lines.wma[0] = wma_value                   # 将 wma 值输出到指标线供策略使用

# 写一个策略来验证自定义的 WMA 指标
class Test_WMA_Strategy(bt.Strategy):                 # 继承 Backtrader 的 Strategy，实现基于 WMA 的简单交易策略
    def __init__(self):                               # 初始化：创建指标与订单状态变量
        self.wma = WeightMovingAverage(self.data, period=10)  # 将自定义 WMA 指标应用于当前数据，设置周期为 10
        self.order = None                             # 记录当前是否有挂单（避免重复下单）

    def next(self):                                   # 每个新 bar 到来时调用：编写交易逻辑
        if self.order:                                # 若有订单尚未完成（成交/取消/拒绝），暂不发起新的订单
            return                                    # 直接返回等待订单回报

        # 打印当前时间和 WMA 的值，便于观察指标与价格关系
        dt = self.data.datetime.date(0)               # 获取当前 bar 的日期对象（0 表示当前）
        close = self.data.close[0]                    # 当前收盘价
        wma_val = self.wma[0]                         # 当前 WMA 指标值（自定义指标输出线的当前值）
        print(f"{dt} | 收盘价: {close:.2f} | WMA: {wma_val:.2f}")  # 打印观测信息

        # 如果当前没有持仓
        if not self.position:                         # 无持仓时考虑入场
            # 如果收盘价 > WMA => 买入（价格突破均线，趋势看多）
            if close > wma_val:
                print(f"{dt}买入信号 | 收盘价: {close:.2f} > WMA: {wma_val:.2f}")  # 打印买入信号
                self.order = self.buy()               # 执行买入，并将返回的订单对象保存到 self.order
        else:                                         # 已有持仓时考虑离场
            # 如果收盘价 < WMA => 卖出（价格跌破均线，趋势转弱）
            if close < wma_val:
                print(f"{dt}卖出信号 | {close:.2f} < WMA: {wma_val:.2f}")         # 打印卖出信号
                self.order = self.sell()              # 执行卖出，并记录订单对象

    def notify_order(self, order):                    # 订单状态回调：当订单完成/取消/拒绝时被调用
        if order.status in [order.Completed, order.Canceled, order.Rejected]:
            self.order = None                         # 清空订单状态，允许后续再次下单

# 运行回测构架：创建引擎、添加策略与数据、运行并绘图
if __name__ == "__main__":                          # Python 入口保护：仅脚本直接运行时执行回测
    cerebro = bt.Cerebro()                           # 创建回测引擎实例
    cerebro.addstrategy(Test_WMA_Strategy)           # 添加策略类到引擎

    data = load_data()                               # 加载数据源
    cerebro.adddata(data)                            # 添加数据源到引擎（默认作为第 0 个数据）

    cerebro.broker.setcash(10000)                    # 设置初始资金为 10,000
    cerebro.broker.setcommission(commission=0.01)    # 设置佣金率为 1%（示例值）

    print(f" 初始资金: {cerebro.broker.getvalue():.2f}")  # 打印开始资金
    cerebro.run()                                     # 运行回测（遍历所有 bar 调用 next）
    print(f"最终资金: {cerebro.broker.getvalue():.2f}")   # 打印结束资金，便于对比绩效

    cerebro.plot()                                    # 绘制价格与指标图表，便于可视化检查策略行为









