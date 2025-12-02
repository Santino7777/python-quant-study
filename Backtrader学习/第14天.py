'''
第14天
练习:
    学习策略参数优化：使用 Backtrader 自动搜索最优参数
'''
# 以上为模块文档字符串（docstring），用于说明本文件主题与目的，不参与具体执行

import backtrader as bt  # 导入 Backtrader 回测框架，简写为 bt，后续调用更简洁
import pandas as pd      # 导入 Pandas 数据分析库，用于读取 CSV 与时间序列处理

# 加载数据：从 CSV 构建 Backtrader 可用的数据源（PandasData）
def load_data():                                   # 定义数据加载函数，返回一个数据源对象供 Cerebro 使用
    file_path = './BABA_year_data.csv'              # 数据文件路径，需要含有列：date、open、high、low、close、volume
    df = pd.read_csv(file_path)                    # 使用 Pandas 读取 CSV 到 DataFrame
    df['date'] = pd.to_datetime(df['date'])        # 将日期字符串转换为时间戳类型，便于设为索引与时序处理
    df.set_index('date', inplace=True)             # 将日期列设置为索引，符合 Backtrader 的时间线要求
    df['openinterest'] = 0                         # 补充 openinterest（持仓兴趣）列，股票数据一般没有，置 0 即可

    data = bt.feeds.PandasData(dataname=df)        # 将 DataFrame 封装为 Backtrader 的 PandasData 数据源
    return data                                    # 返回数据源对象，供后续 Cerebro.adddata 添加到引擎

# results 是全局变量：用于收集每组优化参数对应的回测最终资金
results = []    # 初始化为空列表，用于在策略 stop() 阶段追加结果字典

class MACD_strategy(bt.Strategy):                  # 定义策略类，继承 Backtrader 的 Strategy
    params = (
        ('fast', 12),                              # MACD 快线周期（DIF 的快均线长度，默认 12）
        ('slow', 26),                              # MACD 慢线周期（DIF 的慢均线长度，默认 26）
        ('signal', 9),                             # MACD 信号线周期（DEA 的平滑长度，默认 9）
        ('take_profit', 0.05),                     # 止盈阈值：涨幅达到 +5% 触发离场
        ('stop_loss', 0.1)                         # 止损阈值：跌幅达到 -10% 触发离场
    )

    def __init__(self):                            # 初始化：在回测开始时调用，用于创建指标与状态变量
        self.macd = bt.indicators.MACD(            # 添加 MACD 指标，基于收盘价计算
            self.data.close,                       # 指标输入数据线：使用收盘价 close
            period_me1 = self.params.fast,         # 快线周期（DIF 的快均线长度）来源于策略参数 fast
            period_me2 = self.params.slow,         # 慢线周期（DIF 的慢均线长度）来源于策略参数 slow
            period_signal = self.params.signal     # 信号线周期（DEA 的平滑长度）来源于策略参数 signal
        )                                          # 结束 MACD 指标构造

        self.cross = bt.indicators.CrossOver(      # 构造 DIF 与 DEA 的交叉指标：上穿>0，下穿<0
            self.macd.macd,                        # 第一条线：MACD 指标的 macd（即 DIF）
            self.macd.signal                       # 第二条线：MACD 指标的 signal（即 DEA）
        )
        self.buy_price = None                      # 记录最近一次买入价格，用于计算涨跌幅

    def next(self):                                  # 每个新 bar 到来时调用：编写进出场逻辑
        if not self.position:                         # 当前无持仓：寻找做多入场信号
            if self.cross > 0:                        # DIF 上穿 DEA（CrossOver>0）：看多信号
                self.buy()                            # 执行买入（数量由 sizer 决定）
                self.buy_price = self.data.close[0]   # 记录买入价，用于后续止盈/止损计算
        else:                                         # 已有持仓：判断离场条件
            change = (self.data.close[0] - self.buy_price) / self.buy_price  # 计算当前涨跌幅
            if (self.cross < 0                        # 条件1：DIF 下穿 DEA（看空）
                or change >= self.params.take_profit  # 条件2：达到止盈阈值
                or change <= -self.params.stop_loss): # 条件3：达到止损阈值
                self.close()                          # 平仓（关闭当前持仓）

    def stop(self):                                   # 回测结束时调用：收集本次参数组合的最终资金
        # 现在 这里是局部变量.  我需要把下面的代码加入到全局变量里.
        global results                                # 引用全局列表 results，用于存储所有参数组合的结果
        final_value = self.broker.getvalue()          # 获取当前策略实例的最终账户资金
        # print(...)                                   # 可选调试输出：展示本次参数与最终资金

        result = {                                    # 构造结果字典：记录本次参数组合与最终资金
            'fast': self.params.fast,                 # 记录快线周期
            'slow': self.params.slow,                 # 记录慢线周期
            'signal': self.params.signal,             # 记录信号线周期
            'take_profit': self.params.take_profit,   # 记录止盈阈值
            'stop_loss': self.params.stop_loss,       # 记录止损阈值
            'Final Value': final_value                # 记录最终资金
                  }
        results.append(result)                        # 将结果追加到全局 results 列表中

def run_testing():                                  # 回测主函数：配置引擎、参数优化、执行与输出结果
    cerebro = bt.Cerebro()                          # 创建回测引擎实例

    data = load_data()                              # 调用数据加载函数，获取 PandasData 数据源
    cerebro.adddata(data)                           # 添加数据源到引擎（默认作为第 0 个数据）

    # 优化参数：optstrategy 会遍历给定参数集合，生成多个策略实例并并行/串行运行
    cerebro.optstrategy(
        MACD_strategy,                              # 目标策略类
        fast=range(10, 15, 1),     # fast EMA 参数：尝试 10-14 的快线周期
        slow=range(24, 30, 1),     # slow EMA 参数：尝试 24-29 的慢线周期
        signal=range(8, 15, 1),    # signal EMA 参数：尝试 8-14 的信号线周期
        take_profit=[0.05, 0.1, 0.5],               # 止盈阈值候选列表
        stop_loss=[0.02, 0.1, 0.2]                  # 止损阈值候选列表
    )


    cerebro.broker.setcash(10000)                   # 设置初始资金为 10,000
    cerebro.broker.setcommission(commission=0.01)   # 设置佣金率为 1%（示例值）
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)# 固定下单手数：每次买入 100 单位

    cerebro.run(maxcpus=1)                          # 运行回测；maxcpus=1 便于复现实验结果（禁用多核）

    # 优化参数太多, 绘制图只能绘制一个.
    # cerebro.plot()                                 # 如需绘图，可挑选单组参数运行后再绘制

    # 找出最优参数：在所有结果中选择最终资金最大的组合
    best_result = max(results, key=lambda x: x['Final Value'])
    print(f"\n最优参数组合:")                      # 打印提示行
    for k, v in best_result.items():                # 遍历最优组合字典，逐项输出键值
        print(f"{k}: {v}")

# 忘记调用
if __name__ == "__main__":                         # Python 入口保护：仅脚本直接运行时执行回测
    run_testing()                                   # 调用回测主函数，启动策略优化与结果输出








