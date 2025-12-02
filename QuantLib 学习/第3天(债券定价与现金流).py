'''
Day 3：债券定价与现金流分析

目标：
- 使用 Day 2 获取的数据进行债券建模与定价。
- 理解现金流、票息、到期收益率（YTM）。

任务：
- 使用 QuantLib 创建零息债券和固定利率债券对象。
- 计算债券净现值（NPV）、到期收益率。
- 绘制债券现金流表。
输出：债券定价脚本 + 现金流图表。
'''

import QuantLib as ql  # 导入 QuantLib 金融库，简称 ql；后续对象使用 ql.类名 访问（避免通配导入带来的命名冲突）。
import pandas as pd  # 数据处理与表格操作，读取 Excel/CSV。
import matplotlib.pyplot as plt  # 可视化绘图接口。
from datetime import datetime  # Python 标准库 datetime，用于字符串日期解析与构造时间对象。

# -------------------------
# 1. 读取数据
# -------------------------------
# 国债收益率数据（来自 Day 2 保存的 Excel 文件）
df_yields = pd.read_excel('./US_Treasury_Yields.xlsx')  # 返回 DataFrame；常见列包含 'DATE'、'DGS1/2/5/10/30' 等。

# 读取国债拍卖信息（TreasuryDirect 公告/结果数据）
'''https://www.treasurydirect.gov/auctions/announcements-data-results/'''  # 参考数据来源网址
df_sec = pd.read_csv('./Securities.csv')  # 包含 CUSIP、Issue Date、Maturity Date、Coupon 等字段；具体列依 CSV 而定。

print(df_yields.head())  # 快速查看收益率数据前 5 行，确认列名与类型。
print(df_sec.head())     # 快速查看证券信息前 5 行，确认目标 CUSIP 是否存在。

# 选择 5 年期国债（DGS5）对应的目标 CUSIP（示例：'91282CNX5'）。
bond_info = df_sec[df_sec['CUSIP'] == '91282CNX5'].iloc[0]  # 过滤出指定 CUSIP 的记录，取第一行。注意：若无匹配会抛出 IndexError。

# -----------------------
# 日期处理
# ----------------------
# 将字符串日期（如 '8/30/2030'）转为 QuantLib.Date
def to_ql_date(date_str):
    dt = datetime.strptime(date_str, "%m/%d/%Y")  # datetime.strptime 根据格式解析字符串为 datetime 对象。
    return ql.Date(dt.day, dt.month, dt.year)  # 构造 ql.Date(日, 月, 年)。等价写法：ql.Date(dt.day, ql.Month(dt.month), dt.year)。

# QuantLib 格式日期（用于构建债券与时间表）
issue_date = to_ql_date(bond_info['Issue Date'])   # 发行日（起始日期）
maturity_date = to_ql_date(bond_info['Maturity Date'])  # 到期日（终止日期）

# Python datetime 用于绘制图（matplotlib 需要 Python 日期类型）
maturity_dt_py = datetime.strptime(bond_info['Maturity Date'], "%m/%d/%Y")  # 将到期日转为 Python datetime。

# ---------------------------
# 债券基本参数
# ---------------------------
face_value = 100          # 国债面值（本金），单位同曲线所隐含的货币单位。
coupon_rate = 0.0167      # 年票息率 1.67%（小数形式）。示例值，可替换为实际票息。
frequency = ql.Semiannual # 付息频率：半年一次；其他常用值：ql.Annual、ql.Quarterly 等。

# QuantLib 日计数方法，需要指定约定（Convention）
day_count = ql.ActualActual(ql.ActualActual.ISDA)  # Actual/Actual (ISDA) 常用于政府债；影响利息累计与折现计算。

calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)  # 美国政府债券日历（考虑节假日与工作日调整）。
settlement_days = 1  # 结算天数（T+1）；影响价格/收益率换算时的结算日。


# ------------------------------
# 2. 创建固定利率债券对象
# ------------------------------
# 构建付息时间表（Schedule）
schedule = ql.Schedule(
    issue_date,
    maturity_date,
    ql.Period(frequency),    # 半年一次付息；ql.Period 接收频率枚举并生成等间隔日期。
    calendar,
    ql.Following,            # 起始/调整规则：Following 表示如遇非工作日向后调整到下一个工作日。
    ql.Following,            # 终止/调整规则：同上。
    ql.DateGeneration.Backward,   # 日期生成顺序：Backward 从终止日向前生成日期（常用于已知到期日）。
    False                    # 是否使用月底规则（end-of-month）：False 不启用；启用时月底日期会特殊处理。
)

# 创建固定利率债券对象（FixedRateBond）
fixed_bond = ql.FixedRateBond(
    settlement_days,   # 结算天数
    face_value,        # 面值
    schedule,          # 付息时间表
    [coupon_rate],     # 票息列表（支持分段票息，如 [0.02, 0.025, ...]）
    day_count          # 计息规则
)

#----------------------
# 3. 构建贴现曲线 (FlatForward)
#----------------------
# 选择特定日期的收益率（示例：2020-01-02 的 DGS5）
ytm_val = df_yields.loc[df_yields['DATE'] == '2020-01-02', 'DGS5'].values[0]  # 注意：若 'DATE' 列为 datetime 类型，需改为 pd.Timestamp('2020-01-02') 才能匹配。
ytm = ytm_val / 100     # 转换为小数形式（例如 1.67% -> 0.0167）。

# 创建恒定利率贴现曲线（FlatForward）：即整条曲线以常数收益率 ytm 表示
discount_curve = ql.FlatForward(
    issue_date,   # 曲线参考日期（valuation/settlement 基准）
    ytm,          # 年化利率（小数）
    day_count,    # 日计数规则
    ql.Compounded,# 复利方式：Compounded（离散复利）；可选 ql.Continuous（连续复利）、ql.Simple（单利）。
    frequency     # 复利频率：Semiannual（半年复利）；与 Compounded 搭配使用。
)
discount_curve_handle = ql.YieldTermStructureHandle(discount_curve)  # 将曲线封装为 Handle 以便传入引擎（并支持后续动态更新）。

# 设置债券定价引擎（DiscountingBondEngine）：基于收益率曲线进行现金流贴现求和
engine = ql.DiscountingBondEngine(discount_curve_handle)
fixed_bond.setPricingEngine(engine)  # 绑定引擎后可调用 NPV() 获取价格。

# 计算债券净现值（NPV = 未来现金流现值之和）
npv = fixed_bond.NPV()
print(f"固定利率债券净现值 (NPV) : {npv: .4f}")  # f-string 打印并保留 4 位小数；注意此处多了一个空格（格式化要求）。

# -------------------------
# 4. 绘制现金流图
# --------------------------
# 获取现金流金额（cashflows 返回 Leg[CashFlow]；每个 cf 可能是 FixedRateCoupon 或 Redemption）
cf_amounts = [cf.amount() for cf in fixed_bond.cashflows()]  # amount() 返回该期现金流的金额（票息或本金）。

# 将 QuantLib.Date 转换为 Python datetime，用于绘图
cf_dates_py = [
    datetime(cf.date().year(), cf.date().month(), cf.date().dayOfMonth())
    for cf in fixed_bond.cashflows()
]  # 注意：QuantLib 的 Date.month() 在 Python 绑定中返回整数 1-12；dayOfMonth() 返回日。

# 设置中文显示（防止乱码）
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体。
matplotlib.rcParams['axes.unicode_minus'] = False    # 负号正常显示。

import matplotlib.dates as mdates  # 时间刻度格式化工具。
plt.figure(figsize=(10, 5))        # 设置图形尺寸。

cf_dates_mpl = mdates.date2num(cf_dates_py)  # 转为 Matplotlib 内部的浮点日期格式（便于绘图与刻度控制）。

plt.bar(cf_dates_mpl, cf_amounts, width=15, color='skyblue', label='现金流')  # 柱状图显示各期现金流的大小。

plt.plot(cf_dates_mpl, cf_amounts, color='red', marker='o', label='现金流曲线')  # 折线图连接各期现金流位置，增强视觉效果。

plt.gca().xaxis_date()  # 将 x 轴设为日期轴。
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))  # 设置日期格式。
plt.xticks(rotation=45)  # 横轴日期旋转 45 度，避免重叠。

plt.title('DGS5 真实5年期国债现金流图')  # 标题。
plt.xlabel('日期')                    # 横轴标签。
plt.ylabel('现金流 ($)')               # 纵轴标签，单位为美元。
plt.legend()                          # 图例。
plt.tight_layout()                    # 紧凑布局，减少边缘空白。
plt.show()                            # 展示图像。



'''
======================总结==========================
今天主要做了三件事：  
1. 把国债的收益率和债券信息导入进来，找到目标债券（DGS5）。  
2. 用 QuantLib 建模，创建了一个固定利率债券，设定了面值、票息率、付息频率和到期日。  
3. 根据市场收益率搭建折现曲线，算出了债券的净现值（NPV），然后把未来的现金流绘制成图表。  

最大的收获：  
- 明白了债券价格其实就是“未来现金流折现的总和”。  
- 会用 QuantLib 快速生成现金流表，还能画图直观看每期的付款情况。

'''









