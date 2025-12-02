'''
第1天：
安装并配置QuantLib和相关Python库，了解QuantLib的基本功能。
练习：编写一个简单脚本，使用QuantLib计算零息债券和固定利息债券的定价。
'''

'''
QuantLib 简单介绍
什么是 QuantLib？
QuantLib 是一个开源的金融计算库，主要用于 金融工具定价、风险管理和利率建模。
它原本用 C++ 写成，现在也有 Python 版本，叫 QuantLib-Python。

QuantLib 的用处：
- 可以计算 债券价格（零息债、固定利息债等）
- 可以构建 利率曲线，做贴现因子计算
- 可以对 期权、互换 等金融衍生品定价
- 可以进行 风险管理 和 蒙特卡洛模拟

QuantLib 的基础功能：
1. 日期与日历：处理交易日、节假日
2. 利率曲线：贴现、远期、收益率
3. 债券定价：零息债券、固定利息债券
4. 期权定价：欧式、美式期权
5. 风险建模：随机过程、模拟
'''

import QuantLib as ql  # 导入 QuantLib 并起别名为 ql，后续通过 ql.类名 调用。等价写法：from QuantLib import *（不推荐，命名空间会变得混乱）。

# 1. 设置评估日期（valuation date），决定折现和定价所依据的“今天”
today = ql.Date(10, 9, 2025)  # 构造 QuantLib 的 Date 对象，参数顺序为 (日, 月, 年)。等价写法：ql.Date(10, ql.September, 2025)
ql.Settings.instance().evalutionDate = today  # 将全局评估日期设置为 today。注意：属性应为 evaluationDate，这里写成 evalutionDate（拼写少了一个 'a'），可能导致评估日期未生效。
# 正确写法示例（仅注释说明，不改动原逻辑）：ql.Settings.instance().evaluationDate = today

# 利率曲线（假设无风险利率为 3%）
rate = ql.SimpleQuote(0.03)  # SimpleQuote 是可变报价容器，可在运行时更新；数值单位为年化利率（0.03 = 3%）。
day_count = ql.Actual365Fixed()  # 日计数规则：Actual/365 Fixed，常用于贴现与利息计算。
calendar = ql.TARGET()  # 选择 TARGET（欧元系统）交易日历，用于日期推进与节假日调整。其他常见日历：ql.UnitedStates(), ql.UnitedKingdom() 等。
curve = ql.FlatForward(today, ql.QuoteHandle(rate), day_count)  # 构造平坦远期曲线（FlatForward），即整条曲线的即期/远期利率常数为 3%。
curve_handle = ql.YieldTermStructureHandle(curve)  # 将曲线包裹为 Handle，以便传入定价引擎，且后续利率更新可自动传播。


# 2. 零息债券定价（Zero-Coupon Bond）：仅在到期偿付本金，不支付期间利息
maturity_date = calendar.advance(today, ql.Period(5, ql.Years))  # 使用日历将 today 推进 5 年，Period(5, Years) 表示一个 5年 的期间。
face_value = 100.0  # 面值（本金）为 100（货币单位任意，QuantLib 不强制货币）。

zero_coupon_bond = ql.ZeroCouponBond(2, calendar, face_value, maturity_date)  # 创建零息债券：2 表示结算天数（settlementDays），calendar 用于日历调整。
engine = ql.DiscountingBondEngine(curve_handle)  # 贴现定价引擎：用收益率曲线进行现金流现值计算（NPV）。
zero_coupon_bond.setPricingEngine(engine)  # 将引擎绑定到债券上，之后可调用 NPV() 得到价格。

print("零息债券价格: ", zero_coupon_bond.NPV())  # NPV() 返回债券现值；此处打印价格。


# 3. 固定利息债券定价（Fixed-Rate Bond）：期间按固定票息率支付利息，到期偿付本金
issue_date = today  # 债券发行日设为今天（与评估日一致，仅用于构造现金流时间表）。
schedule = ql.Schedule(
    issue_date,                 # 起始日期（start）：发行日
    maturity_date,              # 终止日期（end）：到期日
    ql.Period(ql.Annual),       # 付息频率：Annual（每年一次）。其他如 ql.Semiannual、ql.Quarterly。
    calendar,                   # 使用同一交易日历进行日期滚动与调整
    ql.Unadjusted,              # 起始日调整规则：Unadjusted（不调整到工作日）
    ql.Unadjusted,              # 终止日调整规则：Unadjusted（不调整到工作日）
    ql.DateGeneration.Forward,  # 日期生成方向：Forward（从起始向后生成）
    False                       # 是否 end-of-month 规则：False（不启用月底规则）
)  # Schedule 生成一组优惠券现金流日期（付息时间表）。

fixed_rate = [0.05]  # 固定票息率 5%（列表形式允许分段票息，如 [0.05, 0.055, ...]）。
fixed_bond = ql.FixedRateBond(
    settlementDays=2,           # 结算天数：T+2
    faceAmount=face_value,      # 面值（本金）
    schedule=schedule,          # 刚刚构造的付息时间表
    paymentDayCounter=day_count,# 计息规则：Actual/365 Fixed，用于计算每期利息金额
    coupons=fixed_rate          # 固定票息率列表
)

fixed_bond.setPricingEngine(engine)  # 绑定贴现定价引擎（与零息债一致），使用同一收益率曲线。
print('固定利息债券价格: ', fixed_bond.NPV())  # 打印固定利息债券现值（价格）。

