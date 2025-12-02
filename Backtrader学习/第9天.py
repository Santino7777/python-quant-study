'''
第9天:
	练习：实现止损和止盈策略，并重新回测。
'''

# 导入回测框架 backtrader（策略、数据源、券商等组件）
import backtrader as bt
# 导入 pandas 用于读写和处理 CSV 数据
import pandas as pd
# 引入 trio 的 sleep（当前文件未使用，仅保留导入，不影响逻辑）
from trio import sleep


def load_data():
    # 指定数据文件路径（请确保 CSV 文件存在于相对路径）
    file_path = './AI_year_data.csv'
    # 读取 CSV 为 DataFrame
    df = pd.read_csv(file_path)
    # 将日期列解析为 datetime 类型，便于 backtrader 识别时间索引
    df['date'] = pd.to_datetime(df['date'])
    # backtrader 数据源需要该列（若无就补 0），代表持仓兴趣（期货/期权可用，这里置 0）
    df['openinterest'] = 0
    # 以日期作为索引，满足 PandasData 默认格式需求
    df.set_index('date', inplace=True)
    # print(df.head())
    # 将 DataFrame 封装为 backtrader 的 PandasData 数据源
    data = bt.feeds.PandasData(dataname=df)
    # 返回数据源对象给回测引擎使用
    return data

class Stop_loss_take_profit(bt.Strategy):
    # 策略参数：可在添加策略时传入以覆盖默认值
    params = (
        ('ma_short', 5),        # 短期均线周期（SMA）
        ('ma_long', 30),        # 长期均线周期（SMA）
        ('stop_loss', 0.05),    # 固定止损比例 5%
        ('take_profit', 0.1)    # 固定止盈比例 10%
              )

    ''' 只有计算止盈和止损'''
    def __init__(self):
        # 跟踪当前是否有挂单：避免重复下单
        self.order = None
        # 记录买入价格：用于后续计算止盈/止损价位
        self.buy_price = None

        # 创建短期与长期简单移动平均线（SMA）作为趋势判断依据
        self.ma_short = bt.indicators.MovingAverageSimple(self.data.close, period=self.params.ma_short)
        self.ma_long = bt.indicators.MovingAverageSimple(self.data.close, period=self.params.ma_long)

    def next(self):
        # 若当前仍有未完成订单，则本根 bar 不再做新的下单动作
        if self.order:
            return

        # 无持仓时：评估入场条件
        if not self.position:
            ''' 在这里加入买的条件'''
            # 买入条件：短期均线位于长期均线上方（趋势向上）
            if self.ma_short[0] > self.ma_long[0]:
                # 提交买入订单，并记录买入价用于后续风控
                self.order = self.buy()
                self.buy_price = self.data.close[0]
                print(f"买入时间: {self.datas[0].datetime.date(0)}, 买入价格: {self.buy_price:.2f}")
        else:
            # 已持仓：计算当前价格与止盈/止损价位
            current_price = self.data.close[0]
            # 计算止损和止盈
            take_profit_price = self.buy_price * (1 + self.params.take_profit)
            stop_lost_price = self.buy_price * (1 - self.params.stop_loss)

            # 若达到止盈价：提交卖出订单止盈
            if current_price >= take_profit_price:
                self.order = self.sell()
                print(f"止盈卖出时间: {self.datas[0].datetime.date(0)}, 当前价格: {current_price:.2f}")
            # 若跌破止损价：提交卖出订单止损
            elif current_price <= stop_lost_price:
                self.order = self.sell()
                print(f"止损卖出时间: {self.datas[0].datetime.date(0)},  当前价格: {current_price:.2f}")

    def notify_order(self, order):
        # 当订单成交/取消/被拒绝时，复位 self.order 以允许后续下单
        if order.status in [order.Completed, order.Canceled, order.Rejected]:
            self.order = None

def run_testting():
    # 创建回测引擎实例
    cerebro = bt.Cerebro()
    # 添加策略到引擎（使用默认参数）
    cerebro.addstrategy(Stop_loss_take_profit)

    # 加载数据并添加到引擎
    data = load_data()
    cerebro.adddata(data)
    # 设置初始现金（资金规模）
    cerebro.broker.setcash(10000)
    # 设置交易佣金比例（这里为 1%）
    cerebro.broker.setcommission(commission=0.01)
    # 设置固定下单手数（每次下 10 股/份）
    cerebro.addsizer(bt.sizers.FixedSize, stake=10)

    # 打印初始资金
    print(f"初始资金: {cerebro.broker.getvalue():.2f}")
    # 运行回测
    cerebro.run()
    # 打印最终资金（原文写“最终终极”，保留原输出）
    print(f"最终终极: {cerebro.broker.getvalue():.2f}")
    # 绘制图表，查看价格、交易点与指标
    cerebro.plot()


if __name__ == "__main__":
    # 主程序入口：执行回测
    run_testting()

