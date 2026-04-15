from sql_builder import sql_one, sql_each
from decimal import Decimal, ROUND_HALF_UP
from consts import SCALE_4, ZERO
import etf_item
import etf_rule
import etf_kline
from common_util import build_dates
from org.nature.util import PythonUtil

sql_create_table = """
CREATE TABLE IF NOT EXISTS etf_profit (
    code TEXT NOT NULL,
    type TEXT NOT NULL,
    rule TEXT NOT NULL,
    date TEXT NOT NULL,
    share_total REAL NOT NULL,
    price_curr REAL NOT NULL,
    amount_curr REAL NOT NULL,
    times_buy REAL NOT NULL,
    times_sell REAL NOT NULL,
    paid_total REAL NOT NULL,
    paid_max REAL NOT NULL,
    paid_left REAL NOT NULL,
    returned REAL NOT NULL,
    profit_sold REAL NOT NULL,
    profit_hold REAL NOT NULL,
    profit_total REAL NOT NULL,
    PRIMARY KEY (code,type,rule,date)
)
"""

PythonUtil.ddl("nature/biz.db", sql_create_table)


def list_by_rule(code, type, rule):
    return PythonUtil.list(
        "nature/biz.db",
        sql_one(
            "select * from etf_profit where code={code} and type={type} and rule={rule};",
            {"code": code, "type": type, "name": rule},
        ),
    )


def save_to_db(data):
    if data:
        PythonUtil.update(
            "nature/biz.db",
            sql_each(
                "REPLACE INTO etf_profit(code,type,rule,date,share_total,price_curr,amount_curr,times_buy,times_sell,paid_total,paid_max,paid_left,returned,profit_sold,profit_hold,profit_total) VALUES[({code},{type},{rule},{date},{share_total},{price_curr},{amount_curr},{times_buy},{times_sell},{paid_total},{paid_max},{paid_left},{returned},{profit_sold},{profit_hold},{profit_total})]",
                data,
            ),
        )


def delete_from_db(code, type, rule):
    return PythonUtil.update(
        "nature/biz.db",
        sql_one(
            "delete from etf_profit where code={code} and type={type} and rule={rule}",
            {"code": code, "type": type, "rule": rule},
        ),
    )


def list_by_period_rule(rule, date_rule, date_start, date_end):
    rule["dates"] = build_dates(date_rule, date_start, date_end)
    profit_list = list_period(rule)
    profit_list.reverse()
    return profit_list


def list_period(rule):
    profit_list = _list_period_in_simulator(rule)
    item_map = etf_item.map_code_type_name()
    for i in profit_list:
        i["code"] = rule["code"]
        i["type"] = rule["type"]
        i["item"] = item_map.get(rule["code"] + ":" + rule["type"])
        i["rule"] = rule["name"]
    return profit_list


def list_by_con(group_by, date_rule, date_start=None, date_end=None):
    dates = build_dates(date_rule, date_start, date_end)
    group_key_func = _group_key(group_by)
    etf_rules = etf_rule.list_valid()
    for i in etf_rules:
        i["dates"] = dates
    profits_list = PythonUtil.multiThread(etf_rules, list_period)
    profit_list = [item for item_list in profits_list for item in item_list]
    return _merge_sort(profit_list, group_key_func)


def get_profit(code, type, name, date_end):
    rule = etf_rule.find_by_id({"code": code, "type": type, "name": name})
    if not rule:
        return None
    rule["end_date"] = date_end
    profit_datum = _get_profit(rule)
    if not profit_datum:
        return None
    res_list = _merge_sort([profit_datum], lambda i: ":".join(["" for _ in range(5)]))
    return res_list[0] if res_list else None


def get_profit_all(date_end):
    etf_rules = etf_rule.list_valid()
    for i in etf_rules:
        i["end_date"] = date_end
    profit_list = PythonUtil.multiThread(etf_rules, _get_profit)
    profit_list = [i for i in profit_list if i]
    res_list = _merge_sort(profit_list, lambda i: ":".join(["" for _ in range(5)]))
    return res_list[0] if res_list else None


def chart(code, type, rule, date_rule, date_start=None, date_end=None):
    if code and type and rule:
        rule_datum = etf_rule.find_by_id({"code": code, "type": type, "name": rule})
        etf_rules = [rule_datum] if rule_datum else []
    else:
        etf_rules = etf_rule.list_valid()
    if date_rule in {"0", "00"}:
        profits_list = PythonUtil.multiThread(etf_rules, _list_in_simulator)
        profits_list = [
            [
                (i.update({"date_start": i["date"], "date_end": i["date"]}), i)[1]
                for i in row
                if (not date_start or i["date"] >= date_start)
                and (not date_end or i["date"] <= date_end)
            ]
            for row in profits_list
        ]
    else:
        dates = build_dates(date_rule, date_start, date_end)
        for i in etf_rules:
            i["dates"] = dates
        profits_list = PythonUtil.multiThread(etf_rules, list_period)
    profit_list = [item for item_list in profits_list for item in item_list]
    group_key_func = _group_key({"item", "rule"})
    data = _merge(profit_list, group_key_func)
    labels = [i["date"] for i in data]
    return {"labels": labels, "data": data}


def _get_profit(datum):
    code = datum["code"]
    type = datum["type"]
    start_date = datum["start_date"]
    end_date = datum["end_date"]
    kline_list = etf_kline.list_from_db_decimal_format(code, type, start_date, end_date)
    if not kline_list:
        return None
    simulator = etf_rule.init_simulator(datum, kline_list)
    simulator.calc()
    profits = simulator.list_profit()
    profit = profits[-1] if profits else None
    if profit:
        profit["date_start"] = kline_list[0]["date"]
        profit["date_end"] = kline_list[-1]["date"]
    return profit


def _list_period_in_simulator(datum):
    code = datum["code"]
    type = datum["type"]
    start_date = datum["start_date"]
    kline_list = etf_kline.list_from_db_decimal_format(code, type, start_date)
    if not kline_list:
        return []
    simulator = etf_rule.init_simulator(datum, kline_list)
    simulator.calc()
    profits = simulator.list_profit()
    dates = (
        datum["dates"]
        if "dates" in datum and datum["dates"]
        else [kline_list[0]["date"], kline_list[-1]["date"]]
    )
    profit_list = _build_last_list(profits, dates)
    return _build_period_list(profit_list)


def _list_in_simulator(datum):
    code = datum["code"]
    type = datum["type"]
    start_date = datum["start_date"]
    kline_list = etf_kline.list_from_db_decimal_format(code, type, start_date)
    if not kline_list:
        return []
    simulator = etf_rule.init_simulator(datum, kline_list)
    simulator.calc()
    return simulator.list_profit()


def _build_period_list(profits):
    if len(profits) < 2:
        return []
    profit_list = []
    for i in range(1, len(profits)):
        pre = profits[i - 1]
        curr = profits[i]
        profit_sold = curr["profit_sold"] - pre["profit_sold"]
        paid_max = curr["paid_max"]
        profit_ratio = (
            (profit_sold / paid_max).quantize(SCALE_4, rounding=ROUND_HALF_UP)
            if paid_max > 0
            else ZERO
        )
        profit_list.append(
            {
                "date": curr["date"],
                "date_start": curr["date_start"],
                "date_end": curr["date_end"],
                "times_buy": curr["times_buy"] - pre["times_buy"],
                "times_sell": curr["times_sell"] - pre["times_sell"],
                "paid_total": curr["paid_total"] - pre["paid_total"],
                "paid_max": paid_max,
                "paid_left": curr["paid_left"] - pre["paid_left"],
                "returned": curr["returned"] - pre["returned"],
                "share_total": curr["share_total"] - pre["share_total"],
                "amount_curr": curr["amount_curr"],
                "profit_total": curr["profit_total"] - pre["profit_total"],
                "profit_hold": curr["profit_hold"] - pre["profit_hold"],
                "profit_sold": profit_sold,
                "profit_ratio": profit_ratio,
            }
        )
    return profit_list


def _build_last_list(profits, dates):
    if not dates or not profits:
        return []
    date_list = [i for i in dates]
    profit_list = []
    prev = None
    date = date_list.pop(0)
    start_date = profits[0]["date"] if profits else None
    for datum in profits:
        if datum["date"] > date:
            while date_list and date_list[0] < datum["date"]:
                date = date_list.pop(0)
            profit_list.append(_build_last(prev, date, start_date))
            if not date_list:
                prev = datum
                break
            date = date_list.pop(0)
            start_date = datum["date"]
        prev = datum

    if date >= prev["date"]:
        profit_list.append(_build_last(prev, date, start_date))
    return profit_list


def _build_last(prev, date, start_date):
    return {
        "date": date,
        "date_start": start_date if prev else None,
        "date_end": prev["date"] if prev else None,
        "times_buy": prev["times_buy"] if prev else ZERO,
        "times_sell": prev["times_sell"] if prev else ZERO,
        "paid_total": prev["paid_total"] if prev else ZERO,
        "paid_max": prev["paid_max"] if prev else ZERO,
        "paid_left": prev["paid_left"] if prev else ZERO,
        "returned": prev["returned"] if prev else ZERO,
        "share_total": prev["share_total"] if prev else ZERO,
        "amount_curr": prev["amount_curr"] if prev else ZERO,
        "profit_total": prev["profit_total"] if prev else ZERO,
        "profit_hold": prev["profit_hold"] if prev else ZERO,
        "profit_sold": prev["profit_sold"] if prev else ZERO,
    }


def _group_key(group_by):
    if set(group_by) == {"rule", "item"}:
        return lambda i: ":".join([i["date"], "", "", "总计", "总计"])
    if ["item"] == group_by:
        return lambda i: ":".join([i["date"], "", "", i["rule"], "总计"])
    if ["rule"] == group_by:
        return lambda i: ":".join([i["date"], "", "", "总计", i["item"]])
    return lambda i: ":".join([i["date"], i["code"], i["type"], i["rule"], i["item"]])


def _set_or_do(profit, item, field):
    if field not in profit:
        profit[field] = item[field]
    else:
        profit[field] += item[field]


def _merge_sort(profits, group_key_func):
    profit_list = _merge(profits, group_key_func)
    profit_list.sort(key=lambda x: (x["date"], x["code"], x["type"]), reverse=True)
    return profit_list


def _merge(profits, group_key_func):

    group = {}
    for item in profits:
        key = group_key_func(item)
        if key not in group:
            group[key] = []
        group[key].append(item)

    result = []
    for key, value in group.items():
        profit = {}
        for item in value:
            if "date_start" not in profit or profit["date_start"] > item["date_start"]:
                profit["date_start"] = item["date_start"]
            if "date_end" not in profit or profit["date_end"] < item["date_end"]:
                profit["date_end"] = item["date_end"]
            for field in [
                "times_buy",
                "times_sell",
                "paid_max",
                "paid_left",
                "share_total",
                "paid_total",
                "profit_sold",
                "profit_hold",
                "profit_total",
                "returned",
                "amount_curr",
            ]:
                _set_or_do(profit, item, field)

        if profit["paid_max"] == 0:
            profit["profit_ratio"] = 0
        else:
            profit["profit_ratio"] = (
                profit["profit_sold"] / profit["paid_max"]
            ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        split = key.split(":", 5)
        profit["date"] = split[0]
        profit["code"] = split[1]
        profit["type"] = split[2]
        profit["rule"] = split[3]
        profit["item"] = split[4]
        result.append(profit)

    return result
