'''
第10天：
	整合成交量指标，设计成交量均线策略。
'''  # 文件说明：第10天练习，基于成交量与价格均线的策略示例

import pandas as pd  # 导入 pandas，用于读取与处理 CSV 数据
import backtrader as bt  # 导入 backtrader 回测框架（策略、数据、券商等组件）

# 获取数据
def load_data():  # 定义数据加载函数，返回 backtrader 的数据源对象
    file_path = './GME_year_data.csv'  # 数据文件路径（相对路径，示例使用 GME 年度数据）
    df = pd.read_csv(file_path)  # 读取 CSV 为 DataFrame
    df['date'] = pd.to_datetime(df['date'])  # 将 'date' 列解析为日期类型，便于设置时间索引
    df.set_index('date', inplace=True)  # 将日期设为索引，满足 PandasData 默认格式
    df['openinterest'] = 0  # 补充 openinterest 列（期货/期权用，这里置 0 以满足数据结构）
    # print(df)
    data = bt.feeds.PandasData(dataname=df)  # 封装为 backtrader 的 PandasData 数据源
    return data  # 返回数据源供回测引擎使用

class Volume_SMA_Strategy(bt.Strategy):  # 定义策略类，继承 bt.Strategy 以便引擎识别和运行
    params = (
        ('volume_ma_period', 10),  # 成交量均线周期，默认 10
        ('price_ma_period', 20),   # 价格均线周期，默认 20
        ('stop_loss', 0.05),       # 固定止损比例 5%
        ('take_profit', 0.1)       # 固定止盈比例 10%
    )  # params：策略参数集合，可在添加策略或优化时覆盖

    def __init__(self):  # 初始化：创建指标与状态变量
        self.volume_ma = bt.indicators.MovingAverageSimple(self.data.volume, period=self.params.volume_ma_period)  # 成交量的简单移动平均线（SMA）
        self.price_ma = bt.indicators.MovingAverageSimple(self.data.close, period=self.params.price_ma_period)  # 收盘价的简单移动平均线（SMA）
        self.buy_price = None  # 记录买入价格：用于计算止盈/止损价位
        self.order = None  # 跟踪当前是否有挂单：避免重复下单

    def next(self):  # 每根新 bar（新K线）调用一次，编写交易逻辑
        if self.order:  # 若仍有未完成订单，则本根不再触发新下单，防止重复
            return  # 直接返回，等待订单完成

        if not self.position:  # 无持仓：评估入场条件
            # 买入条件: 当前成交量 > 成交量均线 且 当前价格 > 价格均线（量价同时放量/走强）
            if self.data.volume[0] > self.volume_ma[0] and self.data.close[0] > self.price_ma[0]:  # 同时满足量价信号
                self.buy_price = self.data.close[0]  # 记录买入价格（用于后续风控）
                self.order = self.buy()  # 提交买入订单（使用默认手数/资金配置）
                print(f"买入时间: {self.datas[0].datetime.date(0)}, 买入股价: {self.buy_price}")  # 控制台打印买入信息

        else:  # 已持仓：计算止盈/止损价位并判断是否触发
            current_price = self.data.close[0]  # 当前收盘价（用作触发判断）
            # 计算止损和止盈
            take_profit = self.buy_price * (1 + self.params.take_profit)  # 止盈价：买入价上浮 take_profit 比例
            stop_loss = self.buy_price * ( 1- self.params.stop_loss)  # 止损价：买入价下浮 stop_loss 比例

            if current_price >=take_profit:  # 到达止盈价：平仓止盈
                self.order = self.close()  # 提交平仓订单（关闭当前持仓）
                print(f"止盈卖出时间:{self.datas[0].datetime.date(0)}, 当前价格:{current_price:.2f}, 买入股价: {self.buy_price}")  # 打印止盈信息
            elif current_price <= stop_loss:  # 跌破止损价：平仓止损
                self.order = self.close()  # 提交平仓订单
                print(f"止损卖出时间: {self.datas[0].datetime.date(0)}, 当前价格:{current_price:.2f}, 买入股价: {self.buy_price}")  # 打印止损信息

    def notify_order(self, order):  # 订单状态回调：在订单完成/取消/拒绝时触发
        if order.status in [order.Completed, order.Canceled, order.Rejected]:  # 订单已完成或不可执行
            self.order = None  # 清空跟踪，允许后续再次下单

def run_testing():  # 回测主函数：构建引擎、加载数据、添加策略并运行
    cerebro = bt.Cerebro()  # 创建回测引擎实例
    data = load_data()  # 加载数据
    cerebro.adddata(data)  # 把数据源添加到引擎
    cerebro.addstrategy(Volume_SMA_Strategy)  # 添加策略类（使用默认参数）

    cerebro.broker.setcash(10000)  # 设置初始资金（账户现金）
    cerebro.broker.setcommission(commission=0.01)  # 设置佣金比例（例如 1%）
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)  # 设置固定下单手数（每次买入/卖出 100 股）

    print(f"初始资金: {cerebro.broker.getvalue():.2f}")  # 打印初始账户资金
    cerebro.run()  # 运行回测（执行策略逻辑）
    print(f"最终资金: {cerebro.broker.getvalue():.2f}")  # 打印最终账户资金
    cerebro.plot()  # 绘制图表（价格、交易点、指标等）

if __name__ == "__main__":  # Python 程序入口：仅在直接运行该脚本时执行
    run_testing()  # 调用回测主函数