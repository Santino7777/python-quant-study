'''
第8天：
	添加风险管理模块，如止损和止盈机制。
'''

# 导入数据处理库 pandas，用于读取和处理 CSV 数据
import pandas as pd
# 导入回测框架 backtrader，用于搭建策略、指标与回测引擎
import backtrader as bt



# 定义策略类，继承自 bt.Strategy，这样才能被 Cerebro 引擎识别和调用
class MACD_RSI_Strategy(bt.Strategy):
    # 策略参数集合：可在添加策略或参数优化时覆盖默认值
    params = (
        ('macd1', 12),          # MACD 快线周期（短期 EMA 周期），默认 12
        ('macd2', 26),          # MACD 慢线周期（长期 EMA 周期），默认 26
        ('macdsig', 9),         # MACD 信号线周期（对 MACD 值的 EMA 周期），默认 9
        ('rsi_period', 14),     # RSI 指标周期，默认 14
        ('rsi_buy', 30),        # RSI 买入阈值（超卖区间），默认 30
        ('printlog', False),    # 是否打印日志：True 打印，False 不打印
        ('trade_size', 0.95),   # 每次交易使用资金比例（例如 0.95 表示使用 95% 现金）

        # 风控参数设置
        ('stop_loss', 0.05),        # 固定止损比例（5%）：跌破买入价的 5% 时止损
        ('take_profit', 0.1),       # 固定止盈比例（10%）：上涨到买入价的 10% 时止盈
        ('trailing_stop', False),   # 是否启用跟踪止损（True/False）
        ('trail_percent', 0.03),    # 跟踪止损比例（3%）：价格回撤超过 3% 触发
        ('risk_reward_ratio', 2)    # 风险收益比系数：用于动态上调止损位置
    )

    # 日志打印函数：统一输出策略运行中的提示信息
    def log(self, txt, dt=None, doprint=False):  # txt：日志文本；dt：指定日期（可选）；doprint：强制打印开关
        if self.params.printlog or doprint:  # 当策略参数 printlog 为 True 或本次调用显式要求打印时，才输出日志
            dt = dt or self.datas[0].datetime.date(0)  # 若未显式传入日期，则使用当前数据序列的日期（第0根bar的日期）
            print(f"{dt.isoformat()}, {txt}")  # 以 ISO 格式打印日期，并跟随日志文本，例如：2020-01-01, 买入执行

    def __init__(self):
        # 创建 MACD 指标：macd.macd 为 MACD 主图，macd.signal 为信号线，macd.histo 为柱状图
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.p.macd1,
            period_me2=self.p.macd2,
            period_signal=self.p.macdsig)

        # 创建交叉指标：判断 MACD 主图（macd.macd）上穿信号线（macd.signal）是否发生
        # CrossOver 输出：>0 表示上穿（金叉），<0 表示下穿（死叉），=0 表示无变化
        self.macd_cross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

        # 创建 RSI 指标：衡量动量强弱，周期由 rsi_period 控制
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)

        # 初始化订单和状态变量：用于跟踪挂单与入场价格
        self.order = None
        self.stop_order = None
        self.take_profit_order = None
        self.entry_price = 0

        # 统计指标：交易总次数、获胜次数、交易历史（便于事后分析）
        self.trade_count = 0
        self.win_count = 0
        self.trade_history = []

    # 当订单状态改变时调用
    def notify_order(self, order):
        # 订单刚提交或被经纪商接受：尚未成交，直接返回不做处理
        if order.status in [order.Submitted, order.Accepted]:
            return  # 订单还在处理中

        # 订单已成交（买入或卖出）：根据方向处理风控与统计
        if order.status == order.Completed:
            if order.isbuy():
                # 买入成功：记录日志与入场价
                self.log(f"买入执行, 价格: {order.executed.price:.2f}")
                self.entry_price = order.executed.price

                # 根据固定比例设置止损价与止盈价（基于入场价）
                stop_price = self.entry_price * (1-self.p.stop_loss)
                tp_price = self.entry_price * (1+self.p.take_profit)

                # 生成止损订单：类型为 Stop，触发价为 stop_price；transmit=False 以便与止盈一同传输
                self.stop_order = self.sell(
                    exectype=bt.Order.Stop,
                    price=stop_price,
                    size=order.executed.size,
                    transmit=False)

                # 生成止盈订单：类型为 Limit，限价为 tp_price；transmit=True 将止损与止盈一起发送
                self.take_profit_order = self.sell(
                    exectype=bt.Order.Limit,
                    price=tp_price,
                    size=order.executed.size,
                    transmit=True)

                # 可选：跟踪止损，trailpercent 为回撤百分比，价格回撤超过设定比例则触发
                if self.p.trailing_stop:
                    self.trailing_stop_order = self.sell(
                        exectype=bt.Order.StopTrail,
                        trailpercent=self.p.trail_percent,
                        size=order.executed.size)

            elif order.issell():
                # 卖出交易：记录日志与胜负统计（按入场价与成交价比较）
                self.log(f"执行卖出, 价格: {order.executed.price:.2f}")
                profit_pct = (order.executed.price / self.entry_price - 1)* 100
                if profit_pct > 0:
                    self.win_count += 1

                # 订单成交后，取消仍未触发的止损、止盈与（若有）跟踪止损，以防悬挂
                if self.stop_order:
                    self.cancel(self.stop_order)
                if self.take_profit_order:
                    self.cancel(self.take_profit_order)
                if hasattr(self, 'trailing_stop_order'):
                    self.cancel(self.trailing_stop_order)

            # 记录每笔交易的详细信息：日期、方向、价格、数量、成交额、佣金与盈亏
            self.trade_history.append({
                'date': self.data.datetime.date(0),
                'type': 'buy' if order.isbuy() else 'sell',
                'price': order.executed.price,
                'size': order.executed.size,
                'value': order.executed.value,
                'commission': order.executed.comm,
                'pnl': order.executed.pnl
            })

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # 订单被取消/保证金不足/被拒绝：输出日志提示
            self.log('订单取消/保证金不足/被拒绝')
        # 任意订单处理结束后，将 self.order 复位为 None，允许后续交易
        self.order = None

    def next(self):
        # 若有未完成订单，则本 bar 跳过交易逻辑，避免重复下单
        if self.order:
            return

        # 无持仓：评估入场条件
        if not self.position:
            # 入场条件：MACD 金叉且 RSI 低于买入阈值（超卖），认为存在反弹机会
            if self.macd_cross[0] > 0 and self.rsi[0] < self.p.rsi_buy:
                # 计算买入数量：用现金 * 使用比例 / 当前价格，得到可买的股份数
                size = self.broker.getcash() * self.p.trade_size / self.data.close[0]
                # 提交买入订单，并记录到 self.order
                self.order = self.buy(size=size)
                # 交易次数 +1（用于统计）
                self.trade_count += 1
        else:
            # 已持仓：考虑动态更新止损价，提高止损位置以锁定已得收益
            current_price = self.data.close[0]
            # 当当前价已达到（入场价 + 止损比例 * 风险收益比）以上，说明上涨较多，可上调止损
            if current_price > self.entry_price * (1+self.p.stop_loss * self.p.risk_reward_ratio):
                # 新的止损价基于当前价计算：当前价下方 stop_loss 比例
                new_stop = current_price * (1-self.p.stop_loss)
                # 取消原止损单，避免重复或价格冲突
                self.cancel(self.stop_order)
                # 重新设置止损单到新的价位（Stop 类型），保护已有收益
                self.stop_order = self.sell(
                    exectype=bt.Order.Stop,
                    price=new_stop,
                    size=self.position.size,
                    transmit=False)

    # 回测结果后运行
    def stop(self):
        # 输出期末资金（总资产），并强制打印
        self.log("期末资金: %.2f" % self.broker.getvalue(), doprint=True)
        # 输出总交易次数（买入+卖出次数）
        self.log('总交易次数: %d' % self.trade_count, doprint=True)
        # 若有交易，输出胜率（获胜次数 / 总次数）
        if self.trade_count > 0:
            self.log("胜率: %.2f%%" % (self.win_count / self.trade_count * 100), doprint=True)

# 先加载数据
def load_data():
    # 指定数据文件路径（请确保文件存在）
    file_path = './AI_year_data.csv'
    # 使用 pandas 读取 CSV 文件为 DataFrame
    df = pd.read_csv(file_path)
    # 将 'date' 列解析为日期类型，便于 backtrader 识别时间索引
    df['date'] = pd.to_datetime(df['date'])
    # 将日期列设为索引，符合 PandasData 的默认格式
    df.set_index('date', inplace=True)

    # 将 DataFrame 封装为 backtrader 的 PandasData 数据源
    data = bt.feeds.PandasData(dataname=df)
    # 返回数据源给上层调用
    return data

# 回测主函数
def run_optimization():
    # 创建回测引擎 Cerebro；optreturn=False 表示优化时返回完整策略对象（非精简）
    cerebro = bt.Cerebro(optreturn=False)

    # 加载数据并添加到引擎
    data = load_data()      # 调用数据加载函数
    cerebro.adddata(data)

    # 添加策略的参数优化组合：为每个参数指定候选值，形成网格搜索
    cerebro.optstrategy(
        MACD_RSI_Strategy,
        macd1 = [12],
        macd2 = [26],
        macdsig = [9],
        rsi_buy = [25, 30, 35],
        stop_loss = [0.03, 0.05],
        take_profit = [0.08, 0.1],
        trailing_stop = [False],
        printlog = [True]
    )

    # 设置初始现金与佣金比例（例如 0.1% 手续费）
    cerebro.broker.set_cash(100000)
    cerebro.broker.setcommission(commission=0.001)

    # 运行参数优化：返回每组参数下的运行结果列表
    opt_runs = cerebro.run()

    # 遍历输出每组参数的回测结果：打印最终资金与关键参数
    for run in opt_runs:
        strat = run[0]
        print('最终终极: %.2f, 参数: rsi_buy=%d, stop_loss=%.2f, take_profit=%.2f' % (
            strat.broker.getvalue(),
            strat.params.rsi_buy,
            strat.params.stop_loss,
            strat.params.take_profit
        ))

    # 绘制结果图表（蜡烛图样式），直观展示价格与交易点
    cerebro.plot(style='candlestick')

if __name__ == "__main__":
    # 主程序入口：执行参数优化回测
    run_optimization()

