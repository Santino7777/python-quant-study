'''
第7天:
    练习：编写优化脚本，测试不同参数组合的效果。
'''


import backtrader as bt
import pandas as pd

# 策略类：继承 bt.Strategy 以接入回测引擎的生命周期（__init__/next/stop 等）
class RSI_EMA_Strategy(bt.Strategy):
    # 参数定义：可在添加策略时覆盖，用于控制指标周期与阈值
    params = (
        ('ema_fast', 5),      # 快速 EMA 周期（响应较快）
        ('ema_slow', 20),     # 慢速 EMA 周期（趋势滤波）
        ('rsi_period', 14),   # RSI 指标周期（默认 14）
        ('rsi_buy', 30),      # RSI 买入阈值（超卖区间）
        ('rsi_sell', 70)      # RSI 卖出阈值（超买区间）
    )

    def __init__(self):
        # 创建快速 EMA 指标：对收盘价进行指数平滑，周期为 ema_fast
        self.ema_fast = bt.indicators.ExponentialMovingAverage(self.data.close, period=self.p.ema_fast)
        # 创建慢速 EMA 指标：对收盘价进行指数平滑，周期为 ema_slow
        self.ema_slow = bt.indicators.ExponentialMovingAverage(self.data.close, period=self.p.ema_slow)
        # 创建 RSI 指标：衡量动量强弱，周期为 rsi_period（默认 Wilder 平滑）
        self.rsi = bt.indicators.RelativeStrengthIndex(self.data.close, period=self.p.rsi_period)
        # 创建均线交叉指标：快 EMA 与慢 EMA 的交叉（>0 金叉，<0 死叉，=0 无变动）
        self.cross = bt. indicators.CrossOver(self.ema_fast, self.ema_slow)

        # 交易记录/状态跟踪：当前挂单（None 表示没有未完成订单）
        self.order = None
        # 交易次数统计：买入/卖出触发的累计次数
        self.trade_count = 0

    def next(self):
        # 若存在未完成订单（self.order 非 None），跳过当前 bar 的交易逻辑，防止重复下单
        if self.order:
            return

        # 打印当前 bar 的调试信息：日期、收盘价、快/慢 EMA、RSI 值、均线交叉状态
        print(f"日期: {self.data.datetime.date(0)}, 收盘价: {self.data.close[0]: .2f}, "
              f"EMA快: {self.ema_fast[0]:.2f}, EMA慢: {self.ema_slow[0]:.2f}, "
              f"RSI: {self.rsi[0]:.2f}, 交叉: {self.cross[0]}")

        # 若当前无持仓（self.position 为 False/size 为 0），评估买入条件
        if not self.position:
            # 买入条件：
            # 1) 均线金叉（self.cross[0] > 0：快 EMA 上穿慢 EMA）或
            # 2) RSI 超卖（self.rsi[0] < self.p.rsi_buy），认为可能反弹
            if self.cross[0] > 0 or self.rsi[0] < self.p.rsi_buy:
                # 提交买入订单并记录到 self.order，便于在 notify_order 中跟踪状态
                self.order = self.buy()
                # 输出买入信号的价格信息（当前收盘价）
                print(f"买入信号: {self.data.close[0]:.2f}")
                # 累计交易次数（包括买入与卖出）
                self.trade_count += 1       # 每次都会加入到trade_count
        else:
            # 卖出条件：
            # 1) 均线死叉（self.cross[0] < 0：快 EMA 下穿慢 EMA）或
            # 2) RSI 超买（self.rsi[0] > 阈值）认为可能回落
            if self.cross[0] < 0 or self.rsi[0] > self.p.rsi_buy:
                # 提交卖出订单并记录到 self.order，便于在 notify_order 中跟踪状态
                self.order = self.sell()
                # 输出卖出信号的价格信息（当前收盘价）
                print(f"卖出信号: {self.data.close[0]:.2f}")
                # 累计交易次数（包括买入与卖出）
                self.trade_count += 1

    def stop(self):
        # 策略结束时调用：输出回测期间累计触发的交易次数
        print(f"\n策略结果, 总交易次数: {self.trade_count}")

def run_strategy():
    # 加载数据
    try:
        file_path = './AAPL_year_data.csv'
        df = pd.read_csv(file_path, parse_dates=['date'])
        df.set_index('date', inplace=True)

        data = bt.feeds.PandasData(dataname=df)
    except Exception as e:
        print(f" 数据加载失败: {e}")
        return

    # 创建Cerebro
    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.broker.setcash(10000)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addstrategy(RSI_EMA_Strategy)


    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    # 运行策略
    print(f"\n开始回测.....")
    results = cerebro.run()             # 运行结果保存到results里.
    strat = results[0]
    print(f"初始资金: {strat.broker.getvalue():.2f}")


    # 输出结果:
    print(f"\n===回测结果===")
    print(f"最终资金: {strat.broker.getvalue():.2f}")

    # 分析结果:
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    print(f"夏普比率: {sharpe.get('sharperatio', 0):.2f}")
    print(f"最大回测: {drawdown.get('max', {}).get('min', 0):.2f}")
    print(f"总交易次数: {trades.get('total', {}).get('closed', 0)}")

    # 绘制结果;
    print(f"\n正在绘制结果图表......")
    cerebro.plot()

if __name__ == "__main__":
    run_strategy()

