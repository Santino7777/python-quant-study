'''
第11天:
	练习：*在Backtrader中加入成交量和成交量均线，设定基于成交量变化的买卖规则，并运行回测。
'''  # 文件说明：第11天练习，基于成交量与价格均线的量价策略

import backtrader as bt  # 引入 backtrader 回测框架（策略、指标、数据、券商等）
import pandas as pd  # 引入 pandas 处理 CSV 数据（读写与时间索引）

def load_data():  # 加载数据函数：读取 CSV，封装为 backtrader 数据源
    file_path = './AAL_year_data.csv'  # 数据文件路径（相对路径，示例使用 AAL 年度数据）
    df = pd.read_csv(file_path)  # 读取 CSV 成 DataFrame
    df['date'] = pd.to_datetime(df['date'])  # 将 'date' 列转换为 datetime 类型，便于设为索引
    df.set_index('date', inplace=True)  # 设置日期为索引（满足 PandasData 默认格式）
    df['openinterest'] = 0  # 补充 openinterest 列（通常用于期货/期权，这里置 0）
    # print(df.head())  # 可选：查看数据头部以验证读入正确

    data = bt.feeds.PandasData(dataname=df)  # 封装为 backtrader 的 PandasData 数据源
    return data  # 返回数据源给回测引擎使用

class volume_strategy(bt.Strategy):  # 定义策略类，继承 bt.Strategy，以便 Cerebro 可运行
    ''' 加入其它指标(MA)'''  # 策略说明：使用成交量与价格的移动平均作为信号

    def __init__(self):  # 初始化：创建指标对象
        self.vol_ma = bt.indicators.SMA(self.data.volume, period=20)  # 成交量 SMA（20 天平均）；self.vol_ma[0] 取当前值
        """加入ma"""  # 说明：再加入价格的均线作为过滤条件
        self.price_ma = bt.indicators.MovingAverageSimple(self.data.close, period=20)  # 收盘价 SMA（20 天平均）；self.price_ma[0] 取当前值

    def next(self):  # 每根新 bar 调用一次：编写量价交易逻辑
        ''' 优化代码. 看起来比较好读.'''  # 说明：提前缓存当前值，提升可读性
        current_date = self.datas[0].datetime.date(0)  # 当前 bar 的日期（ISO 格式）
        current_volume = self.data.volume[0]  # 当前成交量（第 0 根，即最新）
        volume_avg = self.vol_ma[0]  # 当前均量（成交量 SMA 的最新值）
        current_close_price = self.data.close[0]  # 当前收盘价（最新）
        close_avg = self.price_ma[0]  # 当前价格均线值（注意使用 [0] 取值）

        if not self.position:  # 无持仓：评估入场条件
            # 成交量 > 均量 并且 收盘价 > 收盘均价: 买入（量价齐升）
            if current_volume >= volume_avg * 1.5 and current_close_price > close_avg:  # 放量 1.5 倍且价格站上均线
                self.buy()  # 提交买入订单（默认手数/资金配置）
                # 加入买入时间, 成交量, 均量, 和价格.
                print(f"买入时间: {current_date}, "
                      f"成交量: {current_volume}, "
                      f"均量:{volume_avg}, "
                      f"价格: {current_close_price}")  # 控制台打印买入信息

        else:  # 已持仓：评估出场条件
            # 成交量 < 均量 并且 收盘价 < 收盘均价: 卖出（量价走弱）
            if current_volume <= volume_avg and current_close_price < close_avg:  # 缩量且价格跌破均线
                self.sell()  # 提交卖出订单（减仓/平仓）
                # 加入卖出时间, 成交量, 均量, 和价格
                print(f"卖出时间: {current_date}, "
                      f"成交量: {current_volume}, "
                      f"均量: {volume_avg}, "
                      f"价格: {current_close_price}")  # 控制台打印卖出信息

def run_testing():  # 回测主函数：构建引擎、加载数据、添加策略并运行
    cerebro = bt.Cerebro()  # 创建回测引擎实例
    cerebro.addstrategy(volume_strategy)  # 添加策略类（使用默认参数）

    data = load_data()  # 加载数据
    cerebro.adddata(data)  # 将数据源添加到引擎

    cerebro.broker.setcash(10000)  # 设置初始资金（账户现金）
    cerebro.broker.setcommission(commission=0.01)  # 设置交易佣金比例（示例为 1%）
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)  # 固定下单手数（每次 100 股）

    print(f"初始资金: {cerebro.broker.getvalue():.2f}")  # 打印初始资金
    cerebro.run()  # 运行回测
    print(f"最终资金: {cerebro.broker.getvalue():.2f}")  # 打印最终资金
    cerebro.plot()  # 绘制图表（价格、交易点、指标等）

if __name__ == "__main__":  # Python 程序入口：仅在直接运行该脚本时执行
    run_testing()  # 调用回测主函数