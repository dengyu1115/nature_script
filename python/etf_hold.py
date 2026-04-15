from sql_builder import sql_one, sql_each
import etf_item
import etf_rule
import etf_kline
from org.nature.util import PythonUtil

sql_create_table = """
CREATE TABLE IF NOT EXISTS etf_hold (
    code TEXT NOT NULL,
    type TEXT NOT NULL,
    rule TEXT NOT NULL,
    date_buy TEXT NOT NULL,
    level REAl NOT NULL,
    date_sell TEXT,
    price_mark REAL,
    price_buy REAL,
    price_sell REAL,
    share_mark REAL,
    share_buy REAL,
    share_sell REAL,
    amount_buy REAL,
    amount_sell REAL,
    amount_profit REAL,
    PRIMARY KEY (code,type,rule,date_buy,level)
)
"""

PythonUtil.ddl("nature/biz.db", sql_create_table)


def list_by_con(code, type, rule, handle):
    sql = "select * from etf_hold where code={code} and type={type} and rule={rule}"
    if handle == "buy":
        sql += " and date_sell is null"
    if handle == "sell":
        sql += " and date_sell is not null"
    hold_list = PythonUtil.list(
        "nature/biz.db",
        sql_one(
            sql,
            {"code": code, "type": type, "rule": rule},
        ),
    )
    return _format(hold_list)


def delete_from_db(code, type, rule):
    PythonUtil.update(
        "nature/biz.db",
        sql_one(
            "delete from etf_hold where code={code} and type={type} and rule={rule};",
            {"code": code, "type": type, "rule": rule},
        ),
    )


def save_to_db(data):
    if data:
        PythonUtil.update(
            "nature/biz.db",
            sql_each(
                "insert into etf_hold(code,type,rule,date_buy,level,date_sell,price_mark,price_buy,price_sell,share_mark,share_buy,share_sell,amount_buy,amount_sell,amount_profit) values [({code},{type},{rule},{date_buy},{level},{date_sell},{price_mark},{price_buy},{price_sell},{share_mark},{share_buy},{share_sell},{amount_buy},{amount_sell},{amount_profit})];",
                data,
            ),
        )


def list_next_handle(datum):
    code = datum["code"]
    type = datum["type"]
    rule = datum["name"]
    start_date = datum["start_date"]
    kline_list = etf_kline.list_from_db_decimal_format(code, type, start_date)
    simulator = etf_rule.init_simulator(datum, kline_list)
    simulator.calc()
    holds = simulator.next_handle(datum["count"])
    for hold in holds:
        hold["code"] = code
        hold["type"] = type
        hold["rule"] = rule
    return holds


def list_next_by_con(code, type, rule, handle, num):
    etf_rules = etf_rule.list_by_dynamic(code, type, rule, "1")
    for datum in etf_rules:
        datum["count"] = num
    res_list = PythonUtil.multiThread(etf_rules, list_next_handle)

    def _filter(i):
        if handle == "buy":
            return "date_sell" not in i or not i["date_sell"]
        if handle == "sell":
            return "date_sell" in i and i["date_sell"]
        return True

    return _format([i for i_list in res_list for i in i_list if _filter(i)])


def list_left(datum):
    code = datum["code"]
    type = datum["type"]
    rule = datum["name"]
    start_date = datum["start_date"]
    kline_list = etf_kline.list_from_db_decimal_format(code, type, start_date)
    simulator = etf_rule.init_simulator(datum, kline_list)
    simulator.calc()
    holds = [i for i in simulator.list_hold() if not i.get("date_sell")]
    for hold in holds:
        hold["code"] = code
        hold["type"] = type
        hold["rule"] = rule
    return holds


def list_left_by_con(code, type, rule):
    etf_rules = etf_rule.list_by_dynamic(code, type, rule, "1")
    res_list = PythonUtil.multiThread(etf_rules, list_left)
    return _format([i for i_list in res_list for i in i_list])


def list_latest(datum):
    code = datum["code"]
    type = datum["type"]
    rule = datum["name"]
    start_date = datum["start_date"]
    kline_list = etf_kline.list_from_db_decimal_format(code, type, start_date)
    simulator = etf_rule.init_simulator(datum, kline_list)
    simulator.calc()
    holds = simulator.latest_handle()
    for hold in holds:
        hold["code"] = code
        hold["type"] = type
        hold["rule"] = rule
    return holds


def list_latest_by_con(code=None, type=None, rule=None, handle=None):
    etf_rules = etf_rule.list_by_dynamic(code, type, rule, "1")
    res_list = PythonUtil.multiThread(etf_rules, list_latest)

    def _filter(i):
        if handle == "buy":
            return "date_sell" not in i or not i["date_sell"]
        if handle == "sell":
            return "date_sell" in i and i["date_sell"]
        return True

    return _format([i for i_list in res_list for i in i_list if _filter(i)])


def list_latest_all():
    etf_rules = etf_rule.list_valid()
    res_list = PythonUtil.multiThread(etf_rules, list_latest)
    return [i for i_list in res_list for i in i_list]


def _format(data):
    item_map = etf_item.map_code_type_name()
    for i in data:
        i["item"] = item_map.get(i["code"] + ":" + i["type"])
        i["handle"] = "卖" if i.get("date_sell") else "买"
    data.sort(key=lambda i: (i["code"], i["type"], i["date_buy"]), reverse=True)
    return data
