import etf_rule
import etf_kline
import etf_hold
import etf_profit
from org.nature.util import PythonUtil


def do_calc(datum):
    code = datum["code"]
    type = datum["type"]
    rule = datum["name"]
    start_date = datum["start_date"]
    kline_list = etf_kline.list_from_db_decimal_format(code, type, start_date)
    simulator = etf_rule.init_simulator(datum, kline_list)
    simulator.calc()
    holds = simulator.list_hold()
    for hold in holds:
        hold["code"] = code
        hold["type"] = type
        hold["rule"] = rule
    etf_hold.delete_from_db(code, type, rule)
    if holds:
        etf_hold.save_to_db(holds)
    profits = simulator.list_profit()
    for profit in profits:
        profit["code"] = code
        profit["type"] = type
        profit["rule"] = rule
    etf_profit.delete_from_db(code, type, rule)
    if profits:
        etf_profit.save_to_db(profits)
    return len(holds) + len(profits)


def do_calc_all():
    etf_rules = etf_rule.list_all()
    count_list = PythonUtil.multiThread(etf_rules, do_calc)
    return sum(count_list)
