import backtader as bt
import pandas as pd


Class RSI_EMA_Strategy(bt.strategy):
    
    params = (
        ('ema_slow',20),
        ('ema_fast',5),
        ('rsi_period',14),
        ('rsi_buy',30),
        ('rsi_sell',70),   
    )
    
    def __init__(self):
        self.ema_fast = bt.indicators.ExponentialMovingAverage(self.data.close, periods=self.p.ema_fast)
        self.ema_slow = bt.indicator.ExponentialMovingAverage(self.data.close,periods=self.p.ema_slow)
        self.rsi = bt.indicator.RelativeStrengthIndex(self.data.close,periods=self.p.rsi_period)
        self.cross = bt.indicator.CrossOver(self.ema_fast, self.ema_slow) # 金叉为1, 死叉为-1 左大于右为1，右大于左-1
    
        # 交易记录
        self.order = None
        self.trade_count = 0


    def next(self):
        if self.order:
            return
        
            # 卖出条件: EMA死叉 和RSI超买, 卖出
            
            
            
            
            
            
            
            
            
            
            
            if self.cross[0] < 0 or self.rsi[0] > self.p.rsi_sell:
                self.order = self.sell()
                print(f"卖出信号: {self.data.close[0]:.2f}")
                self.trade_count += 1
        else:
            # EMA金叉 和RSI 超卖, 买入
            if self.cross[0] > 0 or self.rsi[0] < self.p.rsi_buy:
                self.order = self.buy()
                print(f"买入信号: {self.data.close[0]:.2f}")
                self.trade_count += 1       # 每次都会加入到trade_count