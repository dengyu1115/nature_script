from sql_builder import sql_one, sql_each
import json
import math
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from consts import ZERO, ONE, HUNDRED, SCALE_4, FORMAT_DATE
import fund_item
from org.nature.util import PythonUtil

sql_create_table = """
CREATE TABLE IF NOT EXISTS fund_net (
    code TEXT NOT NULL,
    date TEXT NOT NULL,
    net_dw REAL NOT NULL,
    net_zzl REAL NOT NULL,
    net_lj REAL NOT NULL,
    net_fq REAL NOT NULL,
    PRIMARY KEY (code, date)
)
"""

PythonUtil.ddl("nature/biz.db", sql_create_table)


def list_from_db_decimal_format(code, start_date=None, end_date=None):
    net_list = list_from_db_dynamic(code, start_date, end_date)

    def decimal(x):
        return Decimal(x).quantize(SCALE_4, rounding=ROUND_HALF_UP)

    return [
        {
            "code": net["code"],
            "date": net["date"],
            "net_dw": decimal(net["net_dw"]),
            "net_lj": decimal(net["net_lj"]),
            "net_zzl": decimal(net["net_zzl"]),
            "net_fq": decimal(net["net_fq"]),
        }
        for net in net_list
    ]


def list_from_db_dynamic(code, start_date=None, end_date=None):
    sql = "select * from fund_net where code={code}"
    param = {"code": code}
    if start_date:
        sql += " and date>={start_date}"
        param.update({"start_date": start_date})
    if end_date:
        sql += " and date<={end_date}"
        param.update({"end_date": end_date})
    sql += " order by date"
    return PythonUtil.list("nature/biz.db", sql_one(sql, param))


def get_latest_from_network(code, type):
    if type == "0":
        url = f"https://hq.sinajs.cn/list=fu_{code}"
        headers = {
            "Referer": "https://finance.sina.com.cn/",
        }
    else:
        url = f"https://w.sinajs.cn/list={code}"
        headers = {
            "Referer": f"https://quotes.sina.cn/hs/company/quotes/view/{code}?from=nbsearchresult",
        }
    res = PythonUtil.get(url, headers, {})
    res_str = res[res.find('"') + 1 : res.rfind('"')]
    s = res_str.split(",")
    if type == "0":
        return {
            "code": code,
            "date": s[7].replace("-", ""),
            "net_zzl": Decimal(s[6]),
        }
    latest = Decimal(s[3])
    last = Decimal(s[2])
    return {
        "code": code,
        "date": s[30].replace("-", ""),
        "net_zzl": ((latest - last) / last).quantize(SCALE_4, rounding=ROUND_HALF_UP),
    }


def list_from_network(code, latest_datum):
    url = "https://api.fund.eastmoney.com/f10/lsjz"
    headers = {
        "Referer": "https://fundf10.eastmoney.com/",
    }
    all_data = []
    page_index = 1
    start_date = _get_date(latest_datum)
    page_data = _list_from_network(
        {"code": code, "date": start_date, "page": page_index}
    )
    count = page_data["count"]
    all_data.extend(page_data["list"])
    params = [
        {"code": code, "date": start_date, "page": i + 1}
        for i in range(1, math.ceil(count / 20))
    ]
    if params:
        pages = PythonUtil.multiThread(params, _list_from_network)
        for page in pages:
            all_data.extend(page["list"])
    if not all_data:
        return []
    all_data.sort(key=lambda x: x["FSRQ"])
    res_list = []
    net_fq = Decimal(latest_datum["net_fq"]) if latest_datum else None
    for record in all_data:
        net_lj = Decimal(record["LJJZ"])
        zzl = (
            (Decimal(record["JZZZL"]) / HUNDRED).quantize(
                SCALE_4, rounding=ROUND_HALF_UP
            )
            if record["JZZZL"]
            else None
        )
        if zzl is not None and net_fq is not None:
            net_fq = (net_fq * (ONE + zzl)).quantize(SCALE_4, rounding=ROUND_HALF_UP)
        else:
            net_fq = net_lj
        res_list.append(
            {
                "code": code,
                "date": record["FSRQ"].replace("-", ""),
                "net_dw": Decimal(record["DWJZ"]),
                "net_lj": net_lj,
                "net_zzl": zzl if zzl else ZERO,
                "net_fq": net_fq,
            }
        )
    return res_list


def delete_from_db(code):
    PythonUtil.update(
        "nature/biz.db",
        sql_one(
            "delete from fund_net where code={code}",
            {"code": code},
        ),
    )


def save_to_db(data):
    if data:
        PythonUtil.update(
            "nature/biz.db",
            sql_each(
                "insert into fund_net(code,date,net_dw,net_zzl,net_lj,net_fq) values[({code},{date},{net_dw},{net_zzl},{net_lj},{net_fq})]",
                data,
            ),
        )


def load(code):
    latest_datum = _get_latest_datum(code)
    data = list_from_network(code, latest_datum)
    save_to_db(data)
    return len(data)


def load_all():
    fund_items = fund_item.list_valid()
    codes = [item["code"] for item in fund_items]
    count_list = PythonUtil.multiThread(codes, load)
    return sum(count_list)


def reload(code):
    delete_from_db(code)
    net_list = list_from_network(code, None)
    save_to_db(net_list)
    return len(net_list)


def reload_all():
    fund_items = fund_item.list_valid()
    codes = [item["code"] for item in fund_items]
    count_list = PythonUtil.multiThread(codes, reload)
    return sum(count_list)


def _get_latest_datum(code):
    return PythonUtil.find(
        "nature/biz.db",
        sql_one(
            "select * from fund_net where code={code} order by date desc limit 1",
            {"code": code},
        ),
    )


def _get_date(datum):
    if not datum:
        return ""
    date_str = datum["date"]
    date_obj = datetime.strptime(date_str, FORMAT_DATE)
    return (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")


def _list_from_network(param):
    params = {
        "fundCode": param["code"],
        "pageIndex": param["page"],
        "pageSize": 20,
        "startDate": param["date"],
        "endDate": "",
    }
    url = "https://api.fund.eastmoney.com/f10/lsjz"
    headers = {
        "Referer": "https://fundf10.eastmoney.com/",
    }
    response = PythonUtil.get(url, headers, params)
    data = json.loads(response)
    if "Data" in data and "LSJZList" in data["Data"]:
        list = data["Data"]["LSJZList"]
        count = data["TotalCount"]
        return {"count": count, "list": list}
    return {"count": 0, "list": []}


def chart(code):
    net_data = list_from_db_decimal_format(code)
    labels = [i["date"] for i in net_data]
    return {"labels": labels, "data": net_data}
