import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="连锁便利店7天补货助手 Demo", layout="wide")

# ================= 数据层 =================
# 后续接真实数据时，把下面四块换成 pd.read_csv("xxx.csv") 即可，逻辑不用改
baseline = pd.DataFrame([
 # 原有两家门店
 ["S001","office","SKU001","农夫山泉550ml",85,87,88,86,90,12,10],
 ["S001","office","SKU002","东方树叶500ml",42,40,41,39,45,5,4],
 ["S001","office","SKU003","可口可乐330ml",30,28,32,35,38,9,8],
 ["S001","office","SKU004","维生素水500ml",5,5,6,5,6,2,2],
 ["S002","community","SKU001","农夫山泉550ml",35,36,38,38,39,65,60],
 ["S002","community","SKU002","东方树叶500ml",18,19,20,21,24,38,35],
 ["S002","community","SKU003","可口可乐330ml",25,24,26,28,32,52,48],
 # 新增四家门店
 ["S003","office","SKU001","农夫山泉550ml",90,92,93,90,95,13,11],
 ["S003","office","SKU005","元气森林480ml",22,21,22,21,24,4,3],
 ["S003","office","SKU003","可口可乐330ml",28,27,30,33,36,8,7],
 ["S004","community","SKU005","元气森林480ml",8,8,9,9,10,16,15],
 ["S004","community","SKU001","农夫山泉550ml",30,31,33,33,34,55,52],
 ["S004","community","SKU006","康师傅冰红茶500ml",20,20,22,22,25,40,37],
 ["S005","community","SKU006","康师傅冰红茶500ml",18,18,20,20,23,36,33],
 ["S005","community","SKU002","东方树叶500ml",15,15,16,17,20,30,28],
 ["S005","community","SKU001","农夫山泉550ml",28,29,31,31,32,50,47],
 ["S006","office","SKU003","可口可乐330ml",26,25,28,31,34,8,7],
 ["S006","office","SKU001","农夫山泉550ml",70,72,73,71,75,10,9],
 ["S006","office","SKU005","元气森林480ml",18,17,18,17,20,3,3],
], columns=["store_id","store_type","sku_id","sku_name",
            "mon","tue","wed","thu","fri","sat","sun"])

inventory = pd.DataFrame([
 ["S001","SKU001",40],["S001","SKU002",25],["S001","SKU003",50],["S001","SKU004",300],
 ["S002","SKU001",30],["S002","SKU002",20],["S002","SKU003",45],
 ["S003","SKU001",35],["S003","SKU005",60],["S003","SKU003",80],
 ["S004","SKU005",280],["S004","SKU001",90],["S004","SKU006",65],
 ["S005","SKU006",55],["S005","SKU002",16],["S005","SKU001",85],
 ["S006","SKU003",75],["S006","SKU001",75],["S006","SKU005",50],
], columns=["store_id","sku_id","on_hand"])

products = pd.DataFrame([
 ["SKU001","农夫山泉550ml",24,3],["SKU002","东方树叶500ml",15,3],
 ["SKU003","可口可乐330ml",24,4],["SKU004","维生素水500ml",15,3],
 ["SKU005","元气森林480ml",15,3],["SKU006","康师傅冰红茶500ml",15,3],
], columns=["sku_id","sku_name","pack_size","target_cover"])

warehouse = pd.DataFrame([
 ["农夫山泉550ml",1000],["东方树叶500ml",150],["可口可乐330ml",600],
 ["维生素水500ml",1500],["元气森林480ml",100],["康师傅冰红茶500ml",120],
], columns=["sku_name","wh_stock"])

STORE_NAME = {"S001":"亦庄写字楼店","S002":"林肯公园社区店",
 "S003":"京东总部店","S004":"大族广场店","S005":"博客雅居社区店","S006":"中航广场写字楼店"}
TYPE_CN = {"office":"写字楼店","community":"社区店"}
WD = {"周一":"mon","周二":"tue","周三":"wed","周四":"thu","周五":"fri","周六":"sat","周日":"sun"}
DAYS = list(WD.values())

# ================= 参数层（What-if，全部可调不写死） =================
st.sidebar.header("What-if 推演")
start = st.sidebar.selectbox("决策日", list(WD.keys()), index=0)
sales_mult = st.sidebar.slider("销量波动", 0.8, 1.2, 1.0, 0.05)
delay = st.sidebar.selectbox("配送延迟", [0, 1], format_func=lambda x: f"T+{1+x}")
transfer_on = st.sidebar.checkbox("当日调拨可用", value=True)

# ================= 逻辑层（专家补货口径） =================
def build_suggestions():
    i = DAYS.index(WD[start]); rows = []
    for _, b in baseline.iterrows():
        p = products[products.sku_id == b.sku_id].iloc[0]
        inv = inventory[(inventory.store_id == b.store_id) &
                        (inventory.sku_id == b.sku_id)].iloc[0].on_hand
        today_fcst = b[WD[start]] * sales_mult          # 今日预测
        gap  = max(0, today_fcst - inv)                 # 今日应急缺口
        pre  = max(0, inv - today_fcst)                 # 预计到货前库存
        cover = int(p.target_cover + delay)             # 目标覆盖天数
        future = [DAYS[(i + 1 + k) % 7] for k in range(cover)]
        target = sum(b[d] for d in future) * sales_mult # 目标库存
        regular = max(0, target - pre)                  # 常规建议量
        rounded = math.ceil(regular / p.pack_size) * p.pack_size if regular > 0 else 0
        daily_avg = b[DAYS].mean()
        sellable = inv / daily_avg if daily_avg else 99
        nxt_fcst = b[DAYS[(i + 1) % 7]] * sales_mult

        if gap > 0:           risk = "红色"
        elif sellable > 15:   risk = "蓝色"
        elif pre < nxt_fcst:  risk = "橙色"
        else:                 risk = "绿色"

        if risk == "红色":
            if transfer_on:
                action = f"今日调拨{gap:.0f}瓶；明日补{rounded:.0f}"
            else:
                tot = math.ceil((gap + regular) / p.pack_size) * p.pack_size
                action = f"调拨不可用，并入常规补{tot:.0f}"
        elif risk == "橙色":  action = f"确认明早到货；明日补{rounded:.0f}"
        elif risk == "蓝色":  action = "暂停补货，促销/调拨消化"
        else:                 action = f"常规补货{rounded:.0f}"

        rows.append([STORE_NAME[b.store_id], TYPE_CN[b.store_type], b.sku_name,
                     risk, inv, round(today_fcst), round(gap), round(target),
                     round(regular), rounded, round(rounded - regular),
                     round(sellable, 1), action])
    cols = ["门店","店型","商品","风险","当前库存","今日预测","今日缺口",
            "目标库存","常规建议","圆整后","溢出","可售天数","建议动作"]
    return pd.DataFrame(rows, columns=cols).sort_values(
        "风险", key=lambda s: s.map({"红色":0, "橙色":1, "蓝色":2, "绿色":3}))

df = build_suggestions()

# ================= 输出层：五个页面 =================
page = st.sidebar.radio("页面", ["驾驶舱","风险清单","仓库视角","回测与价值","决策报告"])

if page == "驾驶舱":
    st.title("今日补货驾驶舱")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("红色缺货", int((df.风险 == "红色").sum()))
    c2.metric("橙色风险", int((df.风险 == "橙色").sum()))
    c3.metric("蓝色积压", int((df.风险 == "蓝色").sum()))
    c4.metric("圆整溢出总量", int(df.溢出.sum()))
    st.dataframe(df.groupby("店型").agg(
        红色=("风险", lambda s: (s == "红色").sum()),
        橙色=("风险", lambda s: (s == "橙色").sum()),
        蓝色=("风险", lambda s: (s == "蓝色").sum())), width="stretch")

elif page == "风险清单":
    st.title("门店 × 商品 风险清单")
    st.dataframe(df, width="stretch")

elif page == "仓库视角":
    st.title("区域仓满足与分配")
    g = df.groupby("商品").agg(门店圆整需求=("圆整后", "sum")).reset_index()
    g = g.merge(warehouse, left_on="商品", right_on="sku_name")
    g = g.rename(columns={"wh_stock": "仓库可用"})
    g["缺口"] = g["门店圆整需求"] - g["仓库可用"]
    def judge(r):
        if r["缺口"] > 0: return "缺口，按优先级分配"
        if r["仓库可用"] > r["门店圆整需求"] * 2: return "积压，控制采购"
        return "可满足"
    g["判断"] = g.apply(judge, axis=1)
    st.dataframe(g[["商品","门店圆整需求","仓库可用","缺口","判断"]], width="stretch")
    st.caption("缺口分配优先级：红色门店 > 橙色门店 > 高销量门店；缺口同步触发采购建议")

elif page == "回测与价值":
    st.title("7天影子回测（代表商品：写字楼店农夫山泉）")
    st.dataframe(pd.DataFrame([
        ["周一",40,45,0,85,0],["周二",0,0,264,87,177],["周三",177,0,96,88,185],
        ["周四",185,0,24,86,123],["周五",123,0,0,90,33],["周六",33,0,96,12,117],
        ["周日",117,0,72,10,179]],
        columns=["星期","期初","应急调拨","常规到货","销量","期末"]), width="stretch")
    st.subheader("策略对比")
    st.dataframe(pd.DataFrame([
        ["A 经验补货","67瓶","不处理今日缺口","较高"],
        ["B 专家补货","0瓶","今日调拨+目标库存","3.45%"]],
        columns=["策略","模拟缺货量","逻辑","圆整溢出率"]), width="stretch")

elif page == "决策报告":
    st.title("区域经理决策报告")
    report = f"""# {start}补货决策摘要
- 红色缺货风险：{int((df.风险 == "红色").sum())} 项，需今日处理
- 橙色风险：{int((df.风险 == "橙色").sum())} 项，需确认明早到货
- 蓝色积压：{int((df.风险 == "蓝色").sum())} 项，暂停补货

## 今日必须处理
{df[df.风险 == "红色"][["门店","商品","建议动作"]].to_markdown(index=False)}
"""
    st.markdown(report)
    st.download_button("下载报告.md", report, file_name="replenishment_report.md")
