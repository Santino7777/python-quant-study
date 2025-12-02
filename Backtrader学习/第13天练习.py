'''
第13天练习：
    本文件为练习用脚本；当前仅包含基础库导入。
    说明：不会更改任何运行逻辑，仅添加详细中文注释以便学习理解。
'''
import backtrader as bt  # 导入 Backtrader 回测框架，并简写为 bt，后续调用更简洁
import pandas as pd      # 导入 Pandas 数据分析库，用于读取/处理 CSV、时间索引等


def load_data():
    file_path='AAPL_year_data.xlsx'
    df=pd.read_excel(file_path)
    df['date']=pd.to_datetime(df['date'])
    df.set_index('date',inplace=True)
    
    data=bt.feeds.PandasData(dataname=df)
    return data


class MACD_Strategy(bt.Strategy):
    
    params={
        ('take_profit',0.05),
        ('stop_loss',0.2)
        
    }
    
    def __int__(self):
        macd=bt.indicators.MACD(self.data)
        self.macd_hist=macd.macd-macd.signal
        self.crossover=bt.indicators.CrossOver(self.macd_hist,0)
        self.buy_price=None
        self.buy_date=None
        
    def log(self,txt):
        dt=self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()}{txt}")
        
    def next(self):
        current_date= self.datas[0].datetime.date(0)
        current_price=self.data.close[0]
        
        if not self.position:
            if self.crossover>0:
                self.buy()
                self.buy_price=current_price
                self.buy_date=current_date
                self.log(f"买入time：{current_date},买入price：{current_price}")
                
        else:
                change = (current_price-self.buy_price) / self.buy_price
                reason=None
                
                if change>= self.params.take_profit:
                    reason='take_profit'
                elif change<= self.params.stop_loss:
                    reason='stop_loss'
                elif self.crossover<0:
                    reason='cross'
                    
                if reason:
                    self.sell()
                    self.log(f"{reason}")
                    self.log(f"buy_time:{self.buy_date},buy_price:{self.buy_price}")
                    self.log(f"sell time:{current_date},sell price:{current_price},reason:{reason}")
                    self.buy_price=None
                    self.buy_Date=None
    
    
    def run_testing():
        cerebro=bt.Cerebro()
        cerebro.addstrategy(MACD_Strategy)
        data=load_data()
        cerebro.adddata(data)
        cerebro.broker.setcash(100000)
        cerebro.broker.setcommission(commission=0.001)  # 设置默认手续费为千分之一，避免未定义变量错误
        
                
        
        




    