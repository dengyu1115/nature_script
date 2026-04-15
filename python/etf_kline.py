import json
from datetime import datetime, timedelta
from sql_builder import sql_one, sql_each
from decimal import Decimal, ROUND_HALF_UP
from consts import SCALE_3
import etf_item
from org.nature.util import PythonUtil

sql_create_table = """
CREATE TABLE IF NOT EXISTS kline (
    code TEXT NOT NULL,
    type TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    latest REAL,
    high REAL,
    low REAL,
    share REAL,
    amount REAL,
    PRIMARY KEY (code,type,date)
)
"""

PythonUtil.ddl("nature/biz.db", sql_create_table)


def _latest_date(code, type):
    date_data = PythonUtil.find(
        "nature/biz.db",
        sql_one(
            "SELECT date FROM kline WHERE code={code} and type={type} order by date desc limit 1",
            {"code": code, "type": type},
        ),
    )
    if not date_data or not date_data["date"]:
        return ""
    date_str = date_data["date"]
    date_obj = datetime.strptime(date_str, "%Y%m%d")
    next_day = date_obj + timedelta(days=1)
    return next_day.strftime("%Y%m%d")


def delete_from_db(code, type):
    PythonUtil.update(
        "nature/biz.db",
        sql_one(
            "DELETE FROM kline WHERE code={code} and type={type}",
            {"code": code, "type": type},
        ),
    )


def list_from_db(code, type):
    return PythonUtil.list(
        "nature/biz.db",
        sql_one(
            "select * from kline where code={code} and type={type} order by date;",
            {"code": code, "type": type},
        ),
    )


def list_from_db_dynamic(code, type, start_date=None, end_date=None):
    sql = "select * from kline where code={code} and type={type}"
    param = {
        "code": code,
        "type": type,
    }
    if start_date:
        sql += " and date>={start_date}"
        param.update({"start_date": start_date})
    if end_date:
        sql += " and date<={end_date}"
        param.update({"end_date": end_date})
    sql += " order by date"
    return PythonUtil.list("nature/biz.db", sql_one(sql, param))


def list_from_db_decimal_format(code, type, start_date=None, end_date=None):
    kline_list = list_from_db_dynamic(code, type, start_date, end_date)

    def decimal(x):
        return Decimal(x).quantize(SCALE_3, rounding=ROUND_HALF_UP)

    return [
        {
            "code": kline["code"],
            "type": kline["type"],
            "date": kline["date"],
            "open": decimal(kline["open"]),
            "latest": decimal(kline["latest"]),
            "high": decimal(kline["high"]),
            "low": decimal(kline["low"]),
            "share": decimal(kline["share"]),
            "amount": decimal(kline["amount"]),
        }
        for kline in kline_list
    ]


def get_latest_from_network(code, type):
    market = "sz" if type == "0" else "sh"
    url = f"https://w.sinajs.cn/list={market}{code}"
    headers = {
        "Referer": f"https://quotes.sina.cn/hs/company/quotes/view/{market}{code}?from=nbsearchresult",
    }
    params = {}
    res = PythonUtil.get(url, headers, params)
    res_str = res[res.find('"') + 1 : res.rfind('"')]
    s = res_str.split(",")
    return {
        "code": code,
        "type": type,
        "date": s[30].replace("-", ""),
        "open": float(s[1]),
        "latest": float(s[3]),
        "high": float(s[4]),
        "low": float(s[5]),
        "share": float(s[8]),
        "amount": float(s[9]),
    }


def list_from_network(code, type, date_start, date_end):
    url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
    headers = {
        "Referer": "https://fundf10.eastmoney.com/",
    }
    params = {
        "fields1": "f1,f2,f3,f4,f5",
        "fields2": "f51,f52,f53,f54,f55,f56,f57",
        "klt": "101",
        "fqt": "1",
        "secid": f"{type}.{code}",
        "beg": date_start,
        "end": date_end,
    }
    response = PythonUtil.get(url, headers, params)
    data = json.loads(response)
    kline_lines = (
        data["data"]["klines"] if "data" in data and "klines" in data["data"] else []
    )
    return [
        {
            "code": code,
            "type": type,
            "date": parts[0].replace("-", ""),
            "open": float(parts[1]),
            "latest": float(parts[2]),
            "high": float(parts[3]),
            "low": float(parts[4]),
            "share": float(parts[5]),
            "amount": float(parts[6]),
        }
        for line in kline_lines
        for parts in [line.strip().split(",")]
        if len(parts) >= 7
    ]


def save_to_db(kline_data):
    if kline_data:
        PythonUtil.update(
            "nature/biz.db",
            sql_each(
                """
                REPLACE INTO kline(code,type,date,open,latest,high,low,share,amount) 
                VALUES [({code},{type},{date},{open},{latest},{high},{low},{share},{amount})]
                """,
                kline_data,
            ),
        )


def load(item):
    code = item["code"]
    type = item["type"]
    date_latest = _latest_date(code, type)
    date_now = datetime.now().strftime("%Y%m%d")
    if date_latest > date_now:
        return 0
    kline_data = list_from_network(code, type, date_latest, date_now)
    save_to_db(kline_data)
    return len(kline_data)


def load_all():
    etf_item_list = etf_item.list_valid()
    return sum(PythonUtil.multiThread(etf_item_list, load))


def reload(item):
    code = item["code"]
    type = item["type"]
    delete_from_db(code, type)
    date_latest = ""
    date_now = datetime.now().strftime("%Y%m%d")
    kline_data = list_from_network(code, type, date_latest, date_now)
    save_to_db(kline_data)
    return len(kline_data)


def reload_all():
    etf_item_list = etf_item.list_valid()
    return sum(PythonUtil.multiThread(etf_item_list, reload))


def merge_latest(item):
    code = item["code"]
    type = item["type"]
    kline_datum = get_latest_from_network(code, type)
    save_to_db([kline_datum])
    return 1


def merge_latest_all():
    etf_item_list = etf_item.list_valid()
    return sum(PythonUtil.multiThread(etf_item_list, merge_latest))


def chart(code, type):
    kline_data = list_from_db_decimal_format(code, type)
    labels = [i["date"] for i in kline_data]
    for i in range(len(kline_data)):
        for num in [5, 10, 30, 60]:
            if i >= num - 1:
                sum_val = sum(
                    [kline["latest"] for kline in kline_data[i - num + 1 : i]]
                )
                kline_data[i]["ma" + str(num)] = (sum_val / Decimal(num)).quantize(
                    SCALE_3, rounding=ROUND_HALF_UP
                )
    return {"labels": labels, "data": kline_data}
