'''
Day 2：获取美国国债数据
目标：学会获取真实的美国国债数据，用于债券定价和利率曲线构建。
任务：
选择数据源：
可用 pandas_datareader 获取国债 ETF（如 TLT, IEF）数据；
或使用 FRED 数据库（可用 pandas-datareader）。
下载并查看：
收益率、到期时间、票息等信息。
将数据整理成QuantLib可以使用的格式（利率曲线或现金流表）。
输出：可用国债数据的CSV或DataFrame。
'''

import pandas as pd  # 导入 pandas，用于数据处理与表格操作。
from pandas_datareader import data as pdr  # 从 pandas_datareader 导入 data 子模块并重命名为 pdr，便于调用 DataReader。
import datetime  # Python 标准库的 datetime，用于时间范围设置（开始/结束日期）。
import QuantLib as ql  # 导入 QuantLib 金融库，命名为 ql，后续通过 ql.类名 访问。

# 设置时间范围（用于 FRED 拉取历史数据）
start = datetime.datetime(2020, 1, 1)       # 构造 Python 的 datetime 对象，表示开始时间：2020-01-01。
end = datetime.datetime.today()             # 获取当前系统日期时间，作为结束时间。


# FRED 国债收益率代码（美国财政部恒定到期收益率系列）
# DGS1 -> 1年期
# DGS2 -> 2年期
# DGS5 -> 5年期
# DGS10 -> 10年期

fred_codes = ['DGS1', 'DGS2', 'DGS5', 'DGS10', 'DGS30']  # 选择多个期限的收益率序列；DGS30 为 30 年期。

# 用 pandas_datareader 获取 FRED 数据（数据源：'fred'）
df = pdr.DataReader(fred_codes, 'fred', start, end)     # DataReader(symbols, source, start, end)。symbols 可为列表，返回多列 DataFrame；索引为日期（列名通常为 'DATE'）。

# 删除缺失值（避免空值导致后续计算或绘图报错）
df.dropna(inplace=True)     # inplace=True 原地修改；FRED 在节假日可能缺数据，删除整行以保持时间序列完整性。

# 重设索引（把日期索引转为普通列，便于选择与绘图）
df.reset_index(inplace=True)        # reset_index() 会把索引列变为普通列，列名通常为 'DATE'（FRED 的默认索引名）。
df.rename(columns={'index': 'Date'}, inplace=True)      # 如果原索引名为 'index' 才需要改名；在 FRED 返回中一般为 'DATE'，此行通常不生效，仅保留说明。

print(df.head())  # 查看前 5 行数据，确认列名与数据结构正确（包含 'DATE'、'DGSx' 列）。

df.to_excel('./US_Treasury_Yields.xlsx', index=False)  # 将整理后的收益率数据保存为 Excel，index=False 表示不保存行索引。

# 整理为 QuantLib 可用的表格
# 选择 10 年期的收益率列（DGS10）与日期（DATE）
ten_year_df = df[['DATE', 'DGS10']].copy()  # copy() 以防后续修改影响原 df。

# QuantLib 不能直接用 pandas 的 Timestamp，需要转换为 ql.Date
dates = [ql.Date(d.day, d.month, d.year) for d in ten_year_df['DATE']]  # 逐行构造 QuantLib 的 Date(日, 月, 年)。确保 'DATE' 为 datetime 类型。
rates = list(ten_year_df['DGS10'] / 100)    # 百分比转小数（如 4.2% -> 0.042）。ZeroCurve 期望年化收益率（decimal）。

# 构建零息利率曲线（ZeroCurve）：输入一组日期与对应零息收益率
calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)  # 美国政府债券日历（GovernmentBond），进行交易日/节假日调整。
day_count = ql.Actual360()   # 日计数规则：Actual/360，常用于货币市场计息；亦可用 Actual365Fixed。
zero_curve = ql.ZeroCurve(dates, rates, day_count, calendar)  # 参数：日期数组、收益率数组、日计数、日历。要求日期严格递增、长度与 rates 对齐。


# 尝试：获取最新利率（在曲线末端日期）
'''.zeroRate(date, day_count, comp) 返回给定日期对应的零息利率；comp 复利方式可选 ql.Simple, ql.Compounded(n), ql.Continuous。
.rate() 提取标量数值。'''
latest_rates = zero_curve.zeroRate(dates[-1], day_count, ql.Continuous).rate()  # 使用连续复利形式获取 10 年期零息利率数值。

print(f'最新 10 年期零息利率: {latest_rates:.4%}')  # f-string 格式化为百分比，保留 4 位小数。

# 绘制收益率时间序列曲线（不同期限）
import matplotlib.pyplot as plt  # 导入 Matplotlib 的 pyplot 接口，用于绘图。
plt.figure(figsize=(10, 6))  # 设置图像尺寸（宽 10，高 6）。
plt.plot(df['DATE'], df['DGS1'], label='1y')   # 绘制 1 年期收益率曲线。
plt.plot(df['DATE'], df['DGS2'], label='2y')   # 绘制 2 年期收益率曲线。
plt.plot(df['DATE'], df['DGS5'], label='5y')   # 绘制 5 年期收益率曲线。
plt.plot(df['DATE'], df['DGS10'], label='10y') # 绘制 10 年期收益率曲线。
plt.plot(df['DATE'], df['DGS30'], label='30y') # 绘制 30 年期收益率曲线。

plt.title('US Treasury Yields (FRED)')  # 设置标题。
plt.xlabel('Date')                      # 横轴标签：日期。
plt.ylabel('Yield (%)')                 # 纵轴标签：收益率（百分比）。
plt.legend()                            # 显示图例，标注不同期限。
plt.grid(True)                          # 打开网格线，便于观察。
plt.show()                              # 展示图像（阻塞式，关闭图窗口后继续执行）。


'''
====================总结================
1. 获取数据

使用 pandas_datareader 从 FRED（美国联邦储备经济数据库） 获取国债收益率数据；
-选择了 1年、2年、5年、10年、30年期（DGS1, DGS2, DGS5, DGS10, DGS30）；
-时间范围：2020 年至今；
-删除缺失值，整理成 DataFrame。
👉 用处：拿到真实的 美国国债官方利率数据。

2. 保存数据
-将整理后的国债数据表保存为 US_Treasury_Yields.xlsx。
👉 用处：以后可以直接用 Excel 文件里的数据，不用每次都联网获取。

3. 转换为 QuantLib 可用格式
-提取 10年期国债收益率；
-转换成 QuantLib 的日期对象 (ql.Date) 和利率（小数形式）；
-构建 零息利率曲线（ZeroCurve）。
👉 用处：QuantLib 需要利率曲线来做 债券定价、利率建模。

4. 计算最新利率
-用 QuantLib 获取最近一天的 10年期零息利率；
-打印结果。
👉 用处：展示 最新的市场利率水平。

5. 绘图展示
-使用 Matplotlib 绘制了 1年、2年、5年、10年、30年期国债收益率的走势曲线；
-横轴：日期，纵轴：收益率（%）。
👉 用处：直观展示 利率随时间的变化趋势，方便观察市场走势。


'''












