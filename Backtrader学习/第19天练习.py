

import backtrader as bt
import pandas as pd
from datetime import timedelta

def load_data():
    file_path = 'TSLA_year_data.csv'
    df=pd.read_csv(file_path)
    df['date']=pd.to_datetime(df['date'])
    df.set_index('date',inplace=True)
    df['openinterest']=0
    return bt.feeds.PandasData(dataname=df)


class LimitOrderStrategy(bt.Strategy):
    params=dict(
        limit_price_buffer=0.95,
        order_valid_days=2        
    )
    
    def __init__(self):
        self.order= None
        self.order_time=None
        
    def next(self):
        dt=self.data.datetime.datetime(0)
        
        #有挂单就看是否过期
        if self.order:
            expire_time = self.order_time + timedelta(days=self.p.order_valid_days)
            if dt >= expire_time:
                print(f"{dt} 超过固定的 {self.p.order_valid_days} 天，订单已过期")
                self.cancel(self.order)
            return
        
        if not self.position:
            #没有挂单就看是否符合条件
            limit_order = self.data.close[0] * self.p.limit_price_buffer
            self.order_time=dt 
            self.order=self.buy(
                exectype=bt.Order.Limit,
                price=limit_order,
                valid=dt + timedelta(days=self.p.order_valid_days)
                )   #买入
            
            print(f"{dt} 买入 订单{self.order.ref} 价格 {limit_order:.2f}")
    
    
    def notify_order(self,order):
        dt=self.data.datetime.datetime(0)
        
        if order.status == order.Completed:
            if order.isbuy():
                print(f"{dt}订单{order.ref} 已完成")
            self.order=None
        
        elif order.status in [order.Canceled,order.Rejected]:
            print(f"{dt} 订单{order.ref} 已取消或被拒绝")
            self.order=None
        
        
def run_test():
    cerebro=bt.Cerebro()
    cerebro.addstrategy(LimitOrderStrategy)
    data=load_data()
    cerebro.adddata(data)
    cerebro.broker.setcash(1000000)
    cerebro.broker.setcommission(commission=0.0003)
    
    print(f" 初始资金: {cerebro.broker.getvalue():.2f}")
    cerebro.run()
    print(f" 最终资金: {cerebro.broker.getvalue():.2f}")
    cerebro.plot()
    

if __name__ == '__main__':
    run_test()

        
            
        
        
        
        
            
           
         
            
            
            
            
            
            
            
            
            
            
