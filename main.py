import json
import matplotlib.pyplot as plt
import requests
import platform
from datetime import datetime
import os
import calendar

account = ""
hallticket = ""
TEMP_DIR = "temp"


def is_valid_date(date_str):
    """检查日期是否符合YYYY-MM-DD格式且为有效日期"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def format_date(date_str):
    """确保日期始终以两位数显示月份和日期"""
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%Y-%m-%d")  # 格式化为YYYY-MM-DD


def fetch_data(sdate, edate, account, hallticket, use_cache=True):
    """获取指定日期范围内的消费数据，并支持缓存，以免hallticket过期带来的麻烦"""
    os.makedirs(TEMP_DIR, exist_ok=True)
    cache_file = os.path.join(TEMP_DIR, f"data_{sdate}_{edate}_{account}.json")

    if use_cache and os.path.exists(cache_file):
        print(f"从缓存读取数据: {cache_file}")
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    url = "https://card.pku.edu.cn/Report/GetPersonTrjn"
    cookie = {"hallticket": hallticket}
    post_data = {
        "sdate": sdate,
        "edate": edate,
        "account": account,
        "page": "1",
        "rows": "9000",
    }
    try:
        response = requests.post(url, cookies=cookie, data=post_data)
        response.raise_for_status()  # 检查 HTTP 状态码
        if "<title></title>" in response.text:
            print("hallticket 可能已过期，请重新输入账户信息。")
            return []
        data = json.loads(response.text)["rows"]
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"数据已缓存到: {cache_file}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"请求失败：{e}")
        return []  # 返回空列表，以便后续处理
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败：{e}")
        print(f"响应内容：{response.text}")
        return []  # 返回空列表，以便后续处理


def analyze_spending(data):
    """分析消费数据并按商家汇总"""
    all_data = dict()
    for item in data:
        try:
            if item["TRANAMT"] < 0:
                merchant = item["MERCNAME"].strip()
                amount = abs(item["TRANAMT"])
                if merchant in all_data:
                    all_data[merchant] += amount
                else:
                    all_data[merchant] = amount
        except Exception:
            pass
    return {k: round(v, 2) for k, v in all_data.items()}


def analyze_spending_by_year(account, hallticket, use_cache=True):
    """按年份分析消费情况，返回各年份的消费数据"""
    years = {
        "大一": ("2021-09-01", "2022-08-31"),
        "大二": ("2022-09-01", "2023-08-31"),
        "大三": ("2023-09-01", "2024-08-31"),
        "大四": ("2024-09-01", "2024-12-31"),
    }
    spending_by_year = {}
    for year, (sdate, edate) in years.items():
        data = fetch_data(sdate, edate, account, hallticket, use_cache)
        spending_by_year[year] = analyze_spending(data)
    return spending_by_year


def plot_spending_bars(spending_by_year):
    """绘制按年份和商家划分的消费柱状图（横向累积，无中间省略）"""
    all_data = {}
    for year, data in spending_by_year.items():
        for merchant, amount in data.items():
            if merchant in all_data:
                all_data[merchant][year] = amount
            else:
                all_data[merchant] = {year: amount}
    for merchant, value_dic in all_data.items():
        for year in spending_by_year.keys():
            if year not in value_dic.keys():
                value_dic[year] = 0

    all_data_sorted = dict(
        sorted(all_data.items(), key=lambda item: sum(item[1].values()), reverse=False)
    )

    # 绘制横向累积柱状图
    merchants = list(all_data_sorted.keys())
    freshman_values = [all_data_sorted[merchant].get("大一", 0) for merchant in merchants]
    sophomore_values = [all_data_sorted[merchant].get("大二", 0) for merchant in merchants]
    junior_values = [all_data_sorted[merchant].get("大三", 0) for merchant in merchants]
    senior_values = [all_data_sorted[merchant].get("大四", 0) for merchant in merchants]

    colors = ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3"]  # Modified colors
    if platform.system() == "Darwin":
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
    elif platform.system() == "Linux":
        plt.rcParams['font.family'] = ['Droid Sans Fallback', 'DejaVu Sans']
    else:
        plt.rcParams['font.sans-serif'] = ['SimHei']

    plt.figure(figsize=(12, len(merchants) / 66 * 18))
    y = range(len(merchants))

    # Create the stacked bars

    total_values = []
    for i in range(len(merchants)):
        total_values.append(
            freshman_values[i] + sophomore_values[i] + junior_values[i] + senior_values[i]
        )

    plt.barh(y, freshman_values, color=colors[0], label="大一")
    plt.barh(y, sophomore_values, left=freshman_values, color=colors[1], label="大二")
    plt.barh(
        y,
        junior_values,
        left=[freshman_values[i] + sophomore_values[i] for i in range(len(merchants))],
        color=colors[2],
        label="大三"
    )
    plt.barh(
        y,
        senior_values,
        left=[
            freshman_values[i] + sophomore_values[i] + junior_values[i]
            for i in range(len(merchants))
        ],
        color=colors[3],
        label="大四"
    )

    for index, value in enumerate(total_values):
        plt.text(value + 0.01 * max(total_values), index, str(value), va='center', fontsize=4)

    plt.yticks(y, merchants, fontsize=4)  # Modified ytick fontsize
    plt.xlabel("消费金额（元）")
    plt.title("白鲸大学食堂消费情况（按年级）")
    plt.xlim(0, 1.2 * max(total_values))
    plt.legend()
    plt.text(
        0.8,
        0.1,
        f"统计总种类数：{len(all_data_sorted)}\n总消费次数：{sum(len(v) for v in spending_by_year.values())}\n总消费金额：{round(sum(total_values),1)}",
        ha='center',
        va='center',
        transform=plt.gca().transAxes
    )
    plt.savefig("result.png")
    plt.show()


def analyze_yearly_spending(spending_by_year):
    """分析每年的消费金额和次数"""
    yearly_data = {}
    for year, data in spending_by_year.items():
        total_amount = 0
        total_count = 0
        for amount in data.values():
            total_amount += amount
            total_count += 1
        yearly_data[year] = {"amount": round(total_amount, 2), "count": total_count}
    return yearly_data


def plot_top_merchant_trends(spending_by_year):
    """绘制大一到大四四年消费金额和次数的变化（双纵坐标轴，柱状图+折线图）"""
    yearly_data = analyze_yearly_spending(spending_by_year)
    if not yearly_data:
        print("没有找到消费记录")
        return

    years = list(yearly_data.keys())
    amounts = [yearly_data[year]["amount"] for year in years]
    counts = [yearly_data[year]["count"] for year in years]

    if platform.system() == "Darwin":
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
    elif platform.system() == "Linux":
        plt.rcParams['font.family'] = ['Droid Sans Fallback', 'DejaVu Sans']
    else:
        plt.rcParams['font.sans-serif'] = ['SimHei']

    fig, ax1 = plt.subplots(figsize=(12, 6))

    color_amount = '#66c2a5'
    color_count = '#fc8d62'
    x = range(len(years))
    bar_width = 0.4

    ax1.set_xlabel('年级')
    ax1.set_ylabel('消费金额（元）', color=color_amount)
    bars = ax1.bar(x, amounts, color=color_amount, label="消费金额", width=bar_width)
    ax1.tick_params(axis='y', labelcolor=color_amount)
    for bar in bars:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2, yval, yval, ha='center', va='bottom')

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    ax2.set_ylabel('消费次数', color=color_count)  # we already handled the x-label with ax1
    count_line = ax2.plot(x, counts, color=color_count, label="消费次数")
    ax2.tick_params(axis='y', labelcolor=color_count)
    for x_val, y_val in zip(x, counts):
        ax2.text(x_val, y_val, str(y_val), ha='center', va='bottom')

    ax1.set_xticks(x)
    ax1.set_xticklabels(years)

    plt.title("每年消费金额和次数变化")

    # 合并图例
    lines = [bars] + count_line
    labels = [l.get_label() if not isinstance(l, list) else l[0].get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper right')

    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.savefig("trend.png")
    plt.show()


if __name__ == "__main__":
    # 读入账户信息
    while True:
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                account = config["account"]
                hallticket = config["hallticket"]
            break
        except Exception:
            print("账户信息读取失败，请重新输入")
            account = input("请输入account: ")
            hallticket = input("请输入hallticket: ")
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump({"account": account, "hallticket": hallticket}, f, indent=4)

    default_sdate = "2021-08-01"
    default_edate = "2024-12-31"

    sdate = default_sdate
    edate = default_edate

    print(f"开始日期: {sdate}, 结束日期: {edate}")

    spending_by_year = analyze_spending_by_year(account, hallticket)
    if any(not data for data in spending_by_year.values()):
        print("未能成功获取全部年份的数据，请检查 hallticket 并重试。")
    else:
        plot_spending_bars(spending_by_year)
        plot_top_merchant_trends(spending_by_year)
