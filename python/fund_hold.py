from sql_builder import sql_one, sql_each
import fund_item
import fund_rule
import fund_net
import workday
from decimal import ROUND_HALF_UP
from consts import ONE, SCALE_4
from org.nature.util import PythonUtil

sql_create_table = """
CREATE TABLE IF NOT EXISTS fund_hold (
    code TEXT NOT NULL,
    rule TEXT NOT NULL,
    date_buy TEXT NOT NULL,
    date_sell TEXT,
    net_buy REAL,
    net_sell REAL,
    share REAL,
    amount_buy REAL,
    amount_sell REAL,
    amount_profit REAL,
    PRIMARY KEY (code,rule,date_buy)
)
"""

PythonUtil.ddl("nature/biz.db", sql_create_table)


def list_by_con(code, rule, handle):
    sql = "select * from fund_hold where code={code} and rule={rule}"
    if handle == "buy":
        sql += " and date_sell is null"
    if handle == "sell":
        sql += " and date_sell is not null"
    hold_list = PythonUtil.list(
        "nature/biz.db",
        sql_one(
            sql,
            {"code": code, "rule": rule},
        ),
    )
    return _format(hold_list)


def delete_from_db(code, rule):
    PythonUtil.update(
        "nature/biz.db",
        sql_one(
            "delete from fund_hold where code={code} and rule={rule}",
            {"code": code, "rule": rule},
        ),
    )


def save_to_db(data):
    if data:
        PythonUtil.update(
            "nature/biz.db",
            sql_each(
                "insert into fund_hold(code,rule,date_buy,date_sell,net_buy,net_sell,share,amount_buy,amount_sell,amount_profit) values [({code},{rule},{date_buy},{date_sell},{net_buy},{net_sell},{share},{amount_buy},{amount_sell},{amount_profit})]",
                data,
            ),
        )


def list_left(datum):
    code = datum["code"]
    rule = datum["name"]
    start_date = datum["start_date"]
    net_list = fund_net.list_from_db_decimal_format(code, start_date)
    simulator = fund_rule.init_simulator(datum, net_list)
    simulator.calc()
    holds = [i for i in simulator.list_hold() if not i.get("date_sell")]
    for hold in holds:
        hold["code"] = code
        hold["rule"] = rule
    return holds


def list_left_by_con(code, rule):
    fund_rules = fund_rule.list_by_dynamic(code, rule, "1")
    res_list = PythonUtil.multiThread(fund_rules, list_left)
    return _format([i for i_list in res_list for i in i_list])


def list_latest(datum):
    code = datum["code"]
    rule = datum["name"]
    start_date = datum["start_date"]
    net_list = fund_net.list_from_db_decimal_format(code, start_date)
    simulator = fund_rule.init_simulator(datum, net_list)
    simulator.calc()
    holds = simulator.latest_handle()
    for hold in holds:
        hold["code"] = code
        hold["rule"] = rule
    return holds


def list_latest_by_con(code=None, rule=None, handle=None):
    fund_rules = fund_rule.list_by_dynamic(code, rule, "1")
    res_list = PythonUtil.multiThread(fund_rules, list_latest)

    def _filter(i):
        if handle == "buy":
            return "date_sell" not in i or not i["date_sell"]
        if handle == "sell":
            return "date_sell" in i and i["date_sell"]
        return True

    return _format([i for i_list in res_list for i in i_list if _filter(i)])


def list_latest_all():
    fund_rules = fund_rule.list_valid()
    res_list = PythonUtil.multiThread(fund_rules, list_latest)
    return [i for i_list in res_list for i in i_list]


def list_next(datum):
    code = datum["code"]
    rule = datum["name"]
    start_date = datum["start_date"]
    net_list = fund_net.list_from_db_decimal_format(code, start_date)
    latest_datum = net_list[-1] if net_list else None
    if not latest_datum:
        return []
    latest_date = latest_datum["date"]
    latest_workday = workday.get_latest_workday()
    if not (latest_workday and latest_date < latest_workday):
        return []
    fund_datum = fund_item.find_by_id(datum)
    est_type = fund_datum["est_type"]
    est_code = code if est_type == 0 else fund_datum["est_code"]
    net_latest = fund_net.get_latest_from_network(est_code, est_type)
    if not net_latest or net_latest["date"] < latest_workday:
        return []
    latest_zzl = net_latest["net_zzl"]

    def _net(val):
        return (val * (ONE + latest_zzl)).quantize(SCALE_4, rounding=ROUND_HALF_UP)

    net_list.append(
        {
            "code": code,
            "date": latest_workday,
            "net_dw": _net(latest_datum["net_dw"]),
            "net_lj": _net(latest_datum["net_lj"]),
            "net_zzl": latest_zzl,
            "net_fq": _net(latest_datum["net_fq"]),
        }
    )
    simulator = fund_rule.init_simulator(datum, net_list)
    simulator.calc()
    holds = []
    count = datum["count"]
    cnt_sell = 0
    for i in simulator.list_hold():
        if i.get("date_buy") == latest_workday:
            holds.append(i)
        if i.get("date_sell") == latest_workday:
            cnt_sell += 1
            if count and cnt_sell >= count:
                break
    for hold in holds:
        hold["code"] = code
        hold["rule"] = rule
    return holds


def list_next_all():
    fund_rules = fund_rule.list_valid()
    for datum in fund_rules:
        datum["count"] = None
    res_list = PythonUtil.multiThread(fund_rules, list_next)
    return [i for i_list in res_list for i in i_list]


def list_next_by_con(code, rule, handle, num):
    fund_rules = fund_rule.list_by_dynamic(code, rule, "1")
    for datum in fund_rules:
        datum["count"] = num
    res_list = PythonUtil.multiThread(fund_rules, list_next)

    def _filter(i):
        if handle == "buy":
            return "date_sell" not in i or not i["date_sell"]
        if handle == "sell":
            return "date_sell" in i and i["date_sell"]
        return True

    return _format([i for i_list in res_list for i in i_list if _filter(i)])


def _format(data):
    item_map = fund_item.map_code_name()
    for i in data:
        i["item"] = item_map.get(i["code"])
        i["handle"] = "卖" if i.get("date_sell") else "买"
    data.sort(key=lambda i: (i["code"], i["date_buy"]), reverse=True)
    return data
