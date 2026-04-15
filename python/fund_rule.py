from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from sql_builder import sql_one, sql_each
import bisect
from consts import SCALE_2, SCALE_3, SCALE_4, ZERO, ONE
from org.nature.util import PythonUtil
from org.nature.exception import Warn

sql_create_table = """
CREATE TABLE IF NOT EXISTS fund_rule (
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    start_date TEXT,
    amount_base REAL NOT NULL,
    ratio REAL NOT NULL,
    expansion REAL NOT NULL,
    PRIMARY KEY (code,name)
)
"""

PythonUtil.ddl("nature/biz.db", sql_create_table)


def list_valid():
    return PythonUtil.list(
        "nature/biz.db",
        "select * from fund_rule where status='1'",
    )


def list_all():
    return PythonUtil.list(
        "nature/biz.db",
        "select * from fund_rule",
    )


def list_by_dynamic(code=None, name=None, status=None):
    sql = "select * from fund_rule where 1=1"
    param = {}
    if code:
        sql += " and code={code}"
        param.update({"code": code})
    if name:
        sql += " and name={name}"
        param.update({"name": name})
    if status:
        sql += " and status={status}"
        param.update({"status": status})
    return PythonUtil.list(
        "nature/biz.db",
        sql_one(sql, param),
    )


def find_by_id(datum):
    return PythonUtil.find(
        "nature/biz.db",
        sql_one(
            "select * from fund_rule where code={code} and name={name}",
            datum,
        ),
    )


def save_to_db(data):
    return PythonUtil.update(
        "nature/biz.db",
        sql_each(
            "insert into fund_rule(code,name,status,start_date,amount_base,ratio,expansion) values[({code},{name},{status},{start_date},{amount_base},{ratio},{expansion})]",
            data,
        ),
    )


def update_to_db(datum):
    return PythonUtil.update(
        "nature/biz.db",
        sql_one(
            "update fund_rule set status={status},start_date={start_date},amount_base={amount_base},ratio={ratio},expansion={expansion} where code={code} and name={name}",
            datum,
        ),
    )


def delete_from_db(datum):
    return PythonUtil.update(
        "nature/biz.db",
        sql_one(
            "delete from fund_rule where code={code} and name={name}",
            datum,
        ),
    )


def list_by_con(code, keyword):
    sql = "select * from fund_rule where name like {keyword}"
    param = {"keyword": "%" + keyword + "%"}
    if code:
        sql = sql + " and code={code}"
        param.update({"code": code})
    return PythonUtil.list(
        "nature/biz.db",
        sql_one(sql, param),
    )


def do_validate(datum):
    if "code" not in datum or not datum["code"]:
        raise Warn("编号不可为空")
    if "name" not in datum or not datum["name"]:
        raise Warn("名称不可为空")
    if "status" not in datum or not datum["status"]:
        raise Warn("状态不可为空")
    if datum["status"] not in ["0", "1"]:
        raise Warn("状态只能为启用或暂停")
    if (
        "amount_base" not in datum
        or not datum["amount_base"]
        or datum["amount_base"] <= 0
    ):
        raise Warn("金额基数必须大于0")
    if "ratio" not in datum or not datum["ratio"] or datum["ratio"] <= 0:
        raise Warn("涨幅必须大于0")
    if "expansion" not in datum or datum["expansion"] is None:
        raise Warn("扩大幅度不可为空")


def do_save(datum):
    do_validate(datum)
    if find_by_id(datum):
        raise Warn("数据已存在")
    return save_to_db([datum])


def do_update(datum):
    do_validate(datum)
    if not find_by_id(datum):
        raise Warn("数据不存在")
    return update_to_db(datum)


def do_delete(datum):
    if "code" not in datum or not datum["code"]:
        raise Warn("编号不可为空")
    if "name" not in datum or not datum["name"]:
        raise Warn("名称不可为空")
    return delete_from_db(datum)


class Simulator:

    def __init__(self, rule, net_list):
        self.amount_base = rule["amount_base"]
        self.expansion = rule["expansion"]
        self.ratio_sell = ONE + rule["ratio"]
        self.net_list = net_list
        self.holds = []
        self.hold_list = []
        self.profit_list = []
        self.profit_sold = ZERO
        self.paid_total = ZERO
        self.paid_left = ZERO
        self.paid_max = ZERO
        self.returned = ZERO
        self.share_total = ZERO
        self.last = None
        self.max = None
        self.min = None
        self.profit_ratio = ZERO
        self.times_buy = 0
        self.times_sell = 0
        self.level = 0
        self.curr = None

    def calc(self):
        if not self.net_list:
            return
        for net in self.net_list:
            self.curr = net
            self._record_max_min()
            self._buy()
            self._sell()
            self._record_paid()
            self._record_profit()

    def list_hold(self):
        return self.hold_list

    def latest_handle(self):
        if not self.curr:
            return []
        date = self.curr["date"]
        return [
            h
            for h in self.hold_list
            if h.get("date_buy") == date or h.get("date_sell") == date
        ]

    def list_profit(self):
        return self.profit_list

    def _record_profit(self):
        if self.paid_max <= 0:
            self.profit_ratio = ZERO
            return
        ratio = (self.profit_sold / self.paid_max).quantize(
            SCALE_4, rounding=ROUND_HALF_UP
        )
        if ratio > self.profit_ratio:
            self.profit_ratio = ratio
        latest = self.curr["net_dw"]
        amount_curr = self.share_total * latest
        profit_hold = amount_curr - self.paid_left
        self.profit_list.append(
            {
                "date": self.curr["date"],
                "share_total": self.share_total,
                "net_curr": latest,
                "amount_curr": amount_curr,
                "times_buy": self.times_buy,
                "times_sell": self.times_sell,
                "paid_total": self.paid_total,
                "paid_max": self.paid_max,
                "paid_left": self.paid_left,
                "returned": self.returned,
                "profit_sold": self.profit_sold,
                "profit_hold": profit_hold,
                "profit_total": self.profit_sold + profit_hold,
            }
        )

    def _buy(self):
        net = self.curr["net_dw"]
        share = self._calc_share(net)
        hold = {
            "date_buy": self.curr["date"],
            "net_buy": net,
            "share": share,
        }
        self._add_sorted(self.holds, hold)
        self.hold_list.append(hold)
        money = net * share
        self.share_total += share
        self.paid_total += money
        self.paid_left += money
        hold["amount_buy"] = money
        if self.paid_left > self.paid_max:
            self.paid_max = self.paid_left
        self.times_buy += 1

    def _sell(self):
        while self._do_sell():
            pass

    def _add_sorted(self, list, item):
        bisect.insort_left(list, item, key=lambda x: x["net_buy"])

    def _do_sell(self):
        if not self.holds:
            return False
        first = self.holds[0]
        net_buy = first["net_buy"]
        target = (net_buy * self.ratio_sell).quantize(SCALE_3, rounding=ROUND_CEILING)
        net_sell = self.curr["net_dw"]
        if target > net_sell:
            return False
        share = first["share"]
        profit = (net_sell - net_buy) * share
        first.update(
            {
                "date_sell": self.curr["date"],
                "net_sell": net_sell,
                "amount_sell": share * net_sell,
                "amount_profit": profit,
            }
        )
        self.profit_sold += profit
        self.holds.pop(0)
        money = net_buy * share
        self.share_total -= share
        self.paid_left -= money
        self.returned += money
        self.times_sell += 1
        return True

    def _calc_share(self, net):
        den = (self.max - self.min) if (self.max and self.min) else ZERO
        num = (net - self.min) if self.min else ZERO
        ratio = (
            (num / den).quantize(SCALE_3, rounding=ROUND_HALF_UP) if den > 0 else ONE
        )
        if ratio < 0:
            ratio = ZERO
        expansion_ratio = ONE + (ONE - ratio) * self.expansion
        share = (
            self.amount_base * (ONE + self.profit_ratio) * expansion_ratio / net
        ).quantize(SCALE_2, rounding=ROUND_CEILING)
        return share

    def _record_max_min(self):
        latest = self.curr["net_dw"]
        self.max = latest if self.max is None or latest > self.max else self.max
        self.min = latest if self.min is None or latest < self.min else self.min

    def _record_paid(self):
        if self.paid_max <= 0:
            self.profit_ratio = ZERO
            return
        ratio = (self.profit_sold / self.paid_max).quantize(
            SCALE_4, rounding=ROUND_HALF_UP
        )
        if ratio > self.profit_ratio:
            self.profit_ratio = ratio


def init_simulator(rule, net_list):
    rule["amount_base"] = Decimal(rule["amount_base"])
    rule["ratio"] = Decimal(rule["ratio"])
    rule["expansion"] = Decimal(rule["expansion"])
    return Simulator(rule, net_list)
