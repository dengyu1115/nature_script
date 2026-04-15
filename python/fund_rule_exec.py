import fund_rule
import fund_net
import fund_hold
import fund_profit
from org.nature.util import PythonUtil


def do_calc(datum):
    code = datum["code"]
    rule = datum["name"]
    start_date = datum["start_date"]
    net_list = fund_net.list_from_db_decimal_format(code, start_date)
    simulator = fund_rule.init_simulator(datum, net_list)
    simulator.calc()
    holds = simulator.list_hold()
    for hold in holds:
        hold["code"] = code
        hold["rule"] = rule
    fund_hold.delete_from_db(code, rule)
    if holds:
        fund_hold.save_to_db(holds)
    profits = simulator.list_profit()
    for profit in profits:
        profit["code"] = code
        profit["rule"] = rule
    fund_profit.delete_from_db(code, rule)
    if profits:
        fund_profit.save_to_db(profits)
    return len(holds) + len(profits)


def do_calc_all():
    fund_rules = fund_rule.list_all()
    count_list = PythonUtil.multiThread(fund_rules, do_calc)
    return sum(count_list)
