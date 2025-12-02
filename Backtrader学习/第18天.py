# 模块文档字符串：说明本次课程目标与练习内容，便于阅读与维护
'''
第18天：
任务目标：
学习多数据源策略，实现同时管理多只股票的交易逻辑。

练习内容：
    理解self.datas列表结构；
    在策略中分别访问和处理不同股票数据；
    实现两个股票不同买卖条件的示范策略；
    回测多数据策略，观察组合表现。
'''

# 导入Backtrader框架，提供策略、数据源、回测等核心功能
import backtrader as bt
# 导入pandas用于CSV读取和数据预处理
import pandas as pd



# 加载函数：从CSV读取数据并转换为Backtrader可用的数据源
def load_data(file_path, name):    # 这次要加载多个公司股票数据.
    df = pd.read_csv(file_path)  # 读取CSV文件为DataFrame
    df['date'] = pd.to_datetime(df['date'])  # 将日期列转换为pandas的datetime类型
    df.set_index('date', inplace=True)  # 将日期设为索引，符合Backtrader按索引推进bar的要求
    df['openinterest'] = 0  # 添加必需列openinterest，通常设为0代表无持仓兴趣数据
    return bt.feeds.PandasData(dataname=df, name=name)  # 构造并返回PandasData数据源，并用name区分不同股票

# 策略：演示如何在同一策略中处理多只股票数据
class MultiStockStrategy(bt.Strategy):
    def __init__(self):  # 初始化：在策略创建时执行一次
        # 按照名称获取数据源，避免依赖self.datas索引顺序，提高可读性与稳健性
        ''' 如果不用getdatabyname, 就需要用self.datas[0] 和self.datas[1] 代表UNH 和PLTR.
        用getdatabyname, 只需要填写股票名称, 就可以按照self.unh'''
        self.unh = self.getdatabyname('UNH')  # 获取名为'UNH'的数据源并保存引用
        self.pltr = self.getdatabyname('PLTR')  # 获取名为'PLTR'的数据源并保存引用

        # 为每只股票分别创建简单移动平均线（SMA）指标，周期不同以示例化差异
        self.sma1 = bt.indicators.SMA(self.unh.close, period=5)  # UNH使用5日SMA
        self.sma2 = bt.indicators.SMA(self.pltr.close, period=10)  # PLTR使用10日SMA

    def next(self):  # 每推进一个bar时调用，编写具体的买卖逻辑
        # 处理UNH：根据价格与SMA关系决定入场或平仓
        unh1 = self.getposition(self.unh).size  # 获取UNH当前持仓数量（size==0表示空仓）
        if not unh1 and self.unh.close[0] > self.sma1[0]:  # 空仓且收盘价高于SMA，做多入场
            self.buy(data=self.unh)  # 下UNH的买单（默认市价单）
        elif unh1 and self.unh.close[0] < self.sma1[0]:  # 有仓且收盘价跌破SMA，平仓离场
            self.sell(data=self.unh)  # 下UNH的卖单（默认市价单），用于平多仓

        # 处理 PLTR：逻辑与UNH一致，但使用自己的SMA指标
        pltr1 = self.getposition(self.pltr).size  # 获取PLTR当前持仓数量
        if not pltr1 and self.pltr.close[0] > self.sma2[0]:  # 空仓且收盘价高于SMA，做多入场
            self.buy(data=self.pltr)  # 下PLTR的买单
        elif pltr1 and self.pltr.close[0] < self.sma2[0]:  # 有仓且收盘价跌破SMA，平仓离场
            self.sell(data=self.pltr)  # 下PLTR的卖单，用于平多仓

def run_testing():  # 回测执行函数：搭建并运行多股票回测环境
    cerebro = bt.Cerebro()  # 创建回测引擎Cerebro
    cerebro.addstrategy(MultiStockStrategy)  # 添加多股票策略到引擎

    # 加载两个不同的数据文件，并分别命名
    data1 = load_data('./UNH_year_data.csv', 'UNH')  # 读取UNH年度数据，命名为'UNH'
    data2 = load_data('./PLTR_year_data.csv', 'PLTR')  # 读取PLTR年度数据，命名为'PLTR'

    cerebro.adddata(data1)  # 将UNH数据源添加进回测引擎
    cerebro.adddata(data2)  # 将PLTR数据源添加进回测引擎


    cerebro.broker.setcash(100000)  # 设置初始资金为10万
    cerebro.broker.setcommission(commission=0.001)  # 设置佣金为千分之一（双边）
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)  # 固定下单手数，每次买入/卖出100股

    print(f"初始资金: {cerebro.broker.getvalue():.2f}")  # 打印回测前的资金
    cerebro.run()  # 运行回测，推进所有数据并执行策略逻辑
    print(f"最终资金: {cerebro.broker.getvalue():.2f}")  # 打印回测结束后的资金
    cerebro.plot()  # 绘制回测图表（价格与指标、交易标记等）

if __name__ == "__main__":  # 入口保护：仅在脚本直接运行时执行回测
    run_testing()  # 调用回测函数，开始执行






