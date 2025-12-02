'''
第6天：
	优化策略参数，如短期和长期均线的周期。
'''

import pandas as pd  # 导入pandas用于数据读取、处理与保存
import backtrader as bt  # 导入Backtrader回测框架


class RsiStrategy(bt.Strategy):  # 定义一个基于RSI交叉的策略类，继承bt.Strategy
    #RSI: Relative Strength Index，相对强弱指数
    params = (  # 声明可调参数集合（用于优化与策略配置）
        ('rsi_short', 7),  # 短期RSI周期，默认7
        ('rsi_long', 28),  # 长期RSI周期，默认28
        ('oversold', 30),  # 超卖阈值，非本策略核心逻辑，但保留为参数
        ('overbought', 70),  # 超买阈值，同上
    )

    def __init__(self):  # 初始化方法，在策略创建时执行一次
        # 计算两个RSI指标：分别使用短期与长期窗口对收盘价计算RSI
        self.rsi_short = bt.indicators.RSI(self.data.close, period=self.p.rsi_short)  # 短期RSI指标
        self.rsi_long = bt.indicators.RSI(self.data.close, period=self.p.rsi_long)  # 长期RSI指标

        # 交叉信号：当短期RSI与长期RSI发生上/下穿，CrossOver会返回1/-1/0
        self.crossover = bt.indicators.CrossOver(self.rsi_short, self.rsi_long)  # RSI交叉指示器

    def next(self):  # 每个新bar（K线）到来时执行一次的回调
        # 简单的交叉策略：短期RSI高于长期RSI则做多，反向则平仓
        if not self.position:  # 如果当前无持仓（空仓）
            if self.rsi_short > self.rsi_long:  # 短期上穿长期，视为买入信号
                self.buy()  # 下买单（数量由sizer或默认值决定）
        elif self.rsi_short < self.rsi_long:  # 有持仓且短期低于长期，视为平仓信号
            self.close()  # 平掉当前持仓


def optimize_parameters():  # 定义优化流程函数
    # 1. 加载本地AAL数据（美国航空AAL），日期列解析为datetime并设为索引
    df = pd.read_csv('./AAL_year_data.csv', parse_dates=['date'], index_col='date')  # 读取CSV为DataFrame

    # 2. 确保列名正确（Backtrader默认PandasData期望小写的open/high/low/close/volume）
    df = df.rename(columns={  # 将OHLCV列统一转换为小写，便于直接喂给PandasData
        'Open': 'open', 'High': 'high',  # 开盘与最高价重命名
        'Low': 'low', 'Close': 'close',  # 最低与收盘价重命名
        'Volume': 'volume'  # 成交量重命名
    })

    # 3. 创建回测引擎并加载数据源
    cerebro = bt.Cerebro()  # 创建Cerebro主引擎
    data = bt.feeds.PandasData(dataname=df)  # 将pandas数据封装为Backtrader数据源
    cerebro.adddata(data)  # 向引擎添加数据源

    # 4. 设置优化参数范围（网格搜索），对策略参数进行组合遍历
    cerebro.optstrategy(  # 使用optstrategy进行参数优化而非addstrategy
        RsiStrategy,  # 目标策略类
        rsi_short=range(5, 16, 2),  # 测试短期周期5到15，步长2（5,7,9,11,13,15）
        rsi_long=range(20, 41, 5)  # 测试长期周期20到40，步长5（20,25,30,35,40）
    )

    # 5. 回测基础设置：初始资金与手续费
    cerebro.broker.setcash(10000)  # 设置初始资金为10000
    cerebro.broker.setcommission(commission=0.001)  # 设置交易手续费为千分之一

    # 6. 添加分析指标（Analyzer），用于统计回报和夏普比率
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')  # 添加收益分析器，输出年化等指标
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')  # 添加夏普比率分析器

    # 7. 运行优化：框架会按参数组合并行/串行执行多次回测
    print("开始参数优化...")  # 输出提示信息
    results = cerebro.run()  # 执行优化，返回多组运行结果（每组为一个策略实例列表）

    # 8. 分析优化结果：遍历所有策略实例，挑选夏普最高的参数组合
    best_sharpe = -float('inf')  # 初始化最佳夏普为负无穷
    best_params = None  # 保存最佳参数组合
    results_list = []  # 保存所有参数组合的统计结果，用于后续写CSV

    for run in results:  # 每个run对应一个参数组合的回测（可能包含多个策略实例）
        for strat in run:  # 逐个策略实例读取分析器结果
            ret = strat.analyzers.returns.get_analysis()['rnorm100']  # 读取归一化年化收益（百分数）
            sharpe = strat.analyzers.sharpe.get_analysis()['sharperatio']  # 读取夏普比率
            results_list.append({  # 记录该参数组合的核心指标
                'rsi_short': strat.params.rsi_short,  # 当前短期参数
                'rsi_long': strat.params.rsi_long,  # 当前长期参数
                'return': ret,  # 年化收益百分比
                'sharpe': sharpe  # 夏普比率
            })

            # 选择夏普比率最高的参数作为最佳
            if sharpe > best_sharpe:  # 若当前夏普更优
                best_sharpe = sharpe  # 更新最佳夏普
                best_params = {  # 记录最佳参数与对应表现
                    'rsi_short': strat.params.rsi_short,
                    'rsi_long': strat.params.rsi_long,
                    'return': ret,
                    'sharpe': sharpe
                }

    # 9. 输出结果：打印最佳参数组合与其表现
    print("\n=== 最佳参数组合 ===")  # 分隔标题
    print(f"短期RSI周期: {best_params['rsi_short']}天")  # 输出最佳短期周期
    print(f"长期RSI周期: {best_params['rsi_long']}天")  # 输出最佳长期周期
    print(f"年化回报率: {best_params['return']:.2f}%")  # 输出最佳年化收益（保留两位小数）
    print(f"夏普比率: {best_params['sharpe']:.2f}")  # 输出最佳夏普比率

    # 10. 保存所有结果到CSV（便于离线分析与复盘）
    results_df = pd.DataFrame(results_list)  # 将结果列表转换为DataFrame
    results_df.to_csv('AAL_optimization_results.csv', index=False)  # 写入CSV文件
    print("\n所有参数组合结果已保存到 AAL_optimization_results.csv")  # 提示保存成功

    # 用最佳参数绘制图：创建新的引擎，加载数据与最佳策略参数，运行并绘图
    print(f"\n使用最佳参数运行并绘制")  # 提示即将使用最佳参数再次运行
    cerebro = bt.Cerebro()  # 新建Cerebro实例（避免沿用旧的优化配置）
    cerebro.adddata(data)  # 加载数据源
    cerebro.addstrategy(  # 加入策略并传入最佳参数
        RsiStrategy,
        rsi_short = best_params['rsi_short'],  # 设置最佳短期RSI周期
        rsi_long = best_params['rsi_long']  # 设置最佳长期RSI周期
    )
    cerebro.broker.setcash(10000)  # 设置初始资金为10000
    cerebro.broker.setcommission(commission=0.001)  # 设置交易手续费为千分之一
    cerebro.run()  # 运行回测
    cerebro.plot()  # 绘制资金曲线与图表（需本地图形环境支持）

if __name__ == '__main__':  # 当该脚本作为主程序运行时执行
    optimize_parameters()  # 调用参数优化流程
