# 模块文档字符串：说明本日练习目标与内容，便于维护与阅读
'''
第19天：
任务目标：
实现复杂订单管理，掌握挂单和自动撤单的策略逻辑。

练习内容：
    理解订单状态和生命周期；
    在notify_order()中实现限价挂单，设定挂单有效期；
    挂单超过有效期自动撤单并重新挂单；
    运行回测测试挂单和撤单机制的效果。
'''

# 导入pandas用于读取CSV并处理数据
import pandas as pd
# 导入Backtrader框架，提供策略、数据源、订单等功能
import backtrader as bt
# 从datetime模块导入timedelta，用于表达时间跨度（如2天）
from datetime import timedelta

# 加载数据函数：读取CSV并转换为Backtrader可用的PandasData数据源
def load_data():
    file_path = 'COIN_year_data.csv'  # 指定数据文件路径（同目录下）
    df = pd.read_csv(file_path)       # 读取CSV为DataFrame
    df['date'] = pd.to_datetime(df['date'])  # 将日期列转换为pandas的datetime类型
    df.set_index('date', inplace=True)       # 将日期设为索引，符合Backtrader按索引推进bar的要求
    df['openinterest'] = 0                   # 添加openinterest列，通常设为0（合约持仓兴趣，股票可忽略）

    data = bt.feeds.PandasData(dataname=df)  # 构造Backtrader的PandasData数据源
    return data                               # 返回数据源以供回测添加

# 策略类：演示限价挂单与自动撤单逻辑
class LimitOrderStrategy(bt.Strategy):
    # 策略参数：使用dict定义，Backtrader会挂载到self.p上（self.p.xxx 或 self.params.xxx）
    params = dict(
        limit_price_buffer = 0.98,      # 限价买单价格系数 = 当前收盘价 * 0.98（以偏低价格挂买单）
        order_valid_days = 2            # 挂单有效期: 2天（超过该时间未成交则撤单）
    )

    def __init__(self):                 # 初始化：在策略创建时调用一次
        self.order = None               # 记录当前挂出的订单对象；None表示当前没有挂单
        self.order_time = None          # 记录当前订单的挂出时间（datetime），用于计算过期时间

    def next(self):                     # 每个bar推进时调用，编写交易逻辑
        dt = self.data.datetime.datetime(0)             # 当前K线的时间（非基础语法：.datetime(0)返回Python的datetime对象）

        # 如果已有挂单, 检查是否已过期
        if self.order:  # 非None表示有挂单对象正在有效期内或待处理
            expire_time = self.order_time + timedelta(days=self.p.order_valid_days)  # 计算过期时间（当前挂单时间+有效期）
            if dt >= expire_time:  # 当前bar时间达到或超过过期时间
                print(f"[{dt}] 挂单超过{self.p.order_valid_days}天未成交, 撤单")
                self.cancel(self.order)     # 主动撤单（非基础语法：self.cancel(order)向broker发撤单请求）
            return      # 已有订单挂出, 本bar不再新下单，避免重复下单

        # 如果当前没有仓位, 没有挂单, 就挂一个限价买单
        if not self.position:  # 非基础语法：self.position为当前数据源持仓对象，布尔上下文为是否有仓位
            limit_price = self.data.close[0] * self.p.limit_price_buffer  # 计算限价：当前收盘价乘以价格系数
            self.order_time = dt  # 记录挂单时间（用于之后计算是否过期）

            # 创建限价买单, 并设置有效期2天
            self.order = self.buy(
                exectype=bt.Order.Limit,                 # 非基础语法：订单执行类型设为“限价单”（bt.Order.Limit）
                price=limit_price,                        # 限价单价格（触发成交的价格条件）
                valid=dt + timedelta(days=self.p.order_valid_days)  # 非基础语法：订单有效期截至时间（datetime），过期后自动失效
            )
            print(f" [{dt}] 下达限价买单, 价格:{limit_price:.2f}, 有效期: {self.p.order_valid_days}天")

    def notify_order(self, order):      # 订单状态回调：每次订单状态变化时由引擎调用
        dt = self.data.datetime.datetime(0)  # 取当前bar时间（便于日志打印与对齐）

        # 如果订单被成交
        if order.status == order.Completed:  # 非基础语法：订单状态枚举，Completed表示订单完成（全部成交）
            if order.isbuy():                # 非基础语法：订单方向判断，isbuy()返回True表示买单
                print(f"[{dt}]限价单成交: 买入价格={order.executed.price:.2f}")  # 非基础语法：executed.price为成交均价
            self.order = None # 成交后清除订单记录（避免重复识别为挂单）

        # 如果订单被撤销或被拒绝
        elif order.status in [order.Canceled, order.Rejected]:  # 非基础语法：订单状态枚举，Canceled/Rejected分别表示撤单/拒绝
            print(f"[{dt}] 订单被撤销或拒绝, 将再下一根K线重新挂单")
            self.order = None   # 清除订单记录以便下一次 next() 重新挂单

def run_testing():                       # 回测入口函数：搭建并运行回测
    cerebro = bt.Cerebro()               # 创建回测引擎Cerebro
    data = load_data()                   # 加载数据源（PandasData）
    cerebro.adddata(data)                # 将数据源添加到引擎（作为self.datas[0]/self.data）
    cerebro.addstrategy(LimitOrderStrategy)  # 添加策略类到引擎
    cerebro.broker.setcash(10000)        # 设置初始资金（10,000）
    cerebro.broker.setcommission(commission=0.01)  # 设置佣金比例为1%

    print(f" 初始资金: {cerebro.broker.getvalue():.2f}")  # 打印回测开始前资金净值
    cerebro.run()                                     # 运行回测（遍历所有bar并调用策略的next）
    print(f" 最终资金: {cerebro.broker.getvalue():.2f}")   # 打印回测结束后资金净值

    cerebro.plot()                                    # 绘制回测图表（价格、指标、交易标记等）

if __name__ == "__main__":             # 入口保护：仅在脚本直接运行时执行回测
    run_testing()                        # 调用回测函数


