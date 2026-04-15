from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING, ROUND_HALF_UP
from datetime import datetime, timedelta
from sql_builder import sql_one, sql_each
import bisect
from consts import SCALE_3, SCALE_4, ZERO, ONE, HUNDRED, FORMAT_DATE
from org.nature.util import PythonUtil
from org.nature.exception import Warn

sql_create_table = """
CREATE TABLE IF NOT EXISTS etf_rule (
    code TEXT NOT NULL,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    status TEXT NOT NULL,
    start_date TEXT,
    amount_base REAL NOT NULL,
    ratio REAL NOT NULL,
    expansion REAL NOT NULL,
    PRIMARY KEY (code,type,name)
)
"""

PythonUtil.ddl("nature/biz.db", sql_create_table)


def list_valid():
    return PythonUtil.list(
        "nature/biz.db",
        "select * from etf_rule where status='1'",
    )


def list_all():
    return PythonUtil.list(
        "nature/biz.db",
        "select * from etf_rule",
    )


def list_by_dynamic(code=None, type=None, name=None, status=None):
    sql = "select * from etf_rule where 1=1"
    param = {}
    if code and type:
        sql += " and code={code} and type={type}"
        param.update({"code": code, "type": type})
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
            "select * from etf_rule where code={code} and type={type} and name={name}",
            datum,
        ),
    )


def save_to_db(data):
    return PythonUtil.update(
        "nature/biz.db",
        sql_each(
            "insert into etf_rule(code,type,name,rule_type,status,start_date,amount_base,ratio,expansion) values[({code},{type},{name},{rule_type},{status},{start_date},{amount_base},{ratio},{expansion})]",
            data,
        ),
    )


def update_to_db(datum):
    return PythonUtil.update(
        "nature/biz.db",
        sql_one(
            "update etf_rule set rule_type={rule_type},status={status},start_date={start_date},amount_base={amount_base},ratio={ratio},expansion={expansion} where code={code} and type={type} and name={name}",
            datum,
        ),
    )


def delete_from_db(datum):
    return PythonUtil.update(
        "nature/biz.db",
        sql_one(
            "delete from etf_rule where code={code} and type={type} and name={name}",
            datum,
        ),
    )


def list_by_con(code, type, rule_type, keyword):
    sql = "select name,code,type,rule_type,amount_base,start_date,ratio,expansion,status from etf_rule where name like {keyword}"
    param = {"keyword": "%" + keyword + "%"}
    if code and type:
        sql = sql + " and code={code} and type={type}"
        param.update({"code": code, "type": type})
    if rule_type:
        sql = sql + " and rule_type={rule_type}"
        param.update({"rule_type": rule_type})
    return PythonUtil.list(
        "nature/biz.db",
        sql_one(sql, param),
    )


def do_validate(datum):
    if "code" not in datum or not datum["code"]:
        raise Warn("编号不可为空")
    if "type" not in datum or not datum["type"]:
        raise Warn("类型不可为空")
    if "name" not in datum or not datum["name"]:
        raise Warn("名称不可为空")
    if "rule_type" not in datum or not datum["rule_type"]:
        raise Warn("规则类型不可为空")
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
    if "type" not in datum or not datum["type"]:
        raise Warn("类型不可为空")
    if "name" not in datum or not datum["name"]:
        raise Warn("名称不可为空")
    return delete_from_db(datum)


class Simulator:

    def __init__(self, rule, kline_list):
        self.rule_type = rule["rule_type"]
        self.amount_base = rule["amount_base"]
        self.expansion = rule["expansion"]
        ratio = rule["ratio"]
        self.ratio_buy = ONE - ratio
        self.ratio_sell = ONE + ratio
        self.kline_list = kline_list
        self.holds = []
        self.holds_temp = []
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
        if not self.kline_list:
            return
        for kline in self.kline_list:
            self.curr = kline
            self._buy()
            self._record_max_min()
            self._sell()
            self._merge_holds()
            self._calc_last()
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

    def next_handle(self, count):
        holds = []
        for h in self.hold_list:
            if h.get("date_sell") is None:
                self._add_sorted(holds, h)

        latest = holds[0] if holds else None
        if latest is None and self.last is None:
            return []
        mark = self.last if self.last else latest["price_mark"]
        results = []
        for _ in range(count):
            mark = (mark * self.ratio_buy).quantize(SCALE_3, rounding=ROUND_FLOOR)
            share = self._calc_share(mark)
            results.append(
                {
                    "price_mark": mark,
                    "price_buy": mark,
                    "date_buy": datetime.now().strftime(FORMAT_DATE),
                    "share_mark": share,
                    "share_buy": share,
                }
            )
        for i in range(min(len(holds), count)):
            hold = holds[i]
            hold["date_sell"] = datetime.now().strftime(FORMAT_DATE)
            price_mark = hold["price_mark"]
            price_cell = (price_mark * self.ratio_sell).quantize(
                SCALE_3, rounding=ROUND_CEILING
            )
            if self.rule_type == "1":
                share = self._calc_share(price_mark)
            elif self.rule_type == "2":
                share = self._calc_share(price_cell)
            else:
                share = hold["share_buy"]
            hold["share_sell"] = share
            hold["price_sell"] = price_cell
            hold["amount_sell"] = share * price_cell
            hold["amount_profit"] = (price_cell - hold["price_buy"]) * share
            results.append(hold)
        return results

    def list_profit(self):
        return self.profit_list

    def _record_profit(self):
        latest = self.curr["latest"]
        amount_curr = self.share_total * latest
        profit_hold = amount_curr - self.paid_left
        self.profit_list.append(
            {
                "date": self.curr["date"],
                "share_total": self.share_total,
                "price_curr": latest,
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
        self.level = 0
        while self._do_buy():
            self.level += 1

    def _sell(self):
        while self._do_sell():
            pass

    def _merge_holds(self):
        if not self.holds:
            for hold in self.holds_temp:
                self._add_sorted(self.holds, hold)
            self.holds_temp.clear()
        else:
            while self.holds_temp:
                hold = self.holds_temp.pop(-1)
                hold["price_mark"] = (
                    self.holds[0]["price_mark"] * self.ratio_buy
                ).quantize(SCALE_3, rounding=ROUND_FLOOR)
                self._add_sorted(self.holds, hold)

    def _add_sorted(self, list, item):
        bisect.insort_left(list, item, key=lambda x: x["price_mark"])

    def _do_buy(self):
        if not self.holds_temp and self.last is None:
            return False
        low = self.curr["low"]
        mark = self.holds_temp[0]["price_mark"] if self.holds_temp else self.last
        target = (mark * self.ratio_buy).quantize(SCALE_3, rounding=ROUND_FLOOR)
        if low > target:
            return False
        open_price = self.curr["open"]
        price = open_price if target > open_price else target
        share = self._calc_share(price)
        share_mark = self._calc_share(mark)
        hold = {
            "date_buy": self.curr["date"],
            "level": self.level,
            "price_mark": target,
            "price_buy": price,
            "share_mark": share_mark,
            "share_buy": share,
            "reason": "compare" if self.holds else "empty",
        }
        self._add_sorted(self.holds_temp, hold)
        self.hold_list.append(hold)
        money = price * share
        self.share_total += share
        self.paid_total += money
        self.paid_left += money
        hold["amount_buy"] = money
        if self.paid_left > self.paid_max:
            self.paid_max = self.paid_left
        self.times_buy += 1
        return True

    def _do_sell(self):
        if not self.holds:
            return False
        first = self.holds[0]
        mark = first["price_mark"]
        price_buy = first["price_buy"]
        target = (mark * self.ratio_sell).quantize(SCALE_3, rounding=ROUND_CEILING)
        high = self.curr["high"]
        if target > high:
            return False
        open_price = self.curr["open"]
        price_sell = open_price if target < open_price else target
        if self.rule_type == "1":
            share = self._calc_share(target)
        elif self.rule_type == "2":
            share = self._calc_share(price_sell)
        else:
            share = first["share_buy"]
        profit = (price_sell - price_buy) * share
        first.update(
            {
                "date_sell": self.curr["date"],
                "share_sell": share,
                "price_sell": price_sell,
                "amount_sell": share * price_sell,
                "amount_profit": profit,
            }
        )
        self.profit_sold += profit
        if len(self.holds) == 1:
            self.last = first["price_mark"]
        self.holds.pop(0)
        money = price_buy * share
        self.share_total -= share
        self.paid_left -= money
        self.returned += money
        self.times_sell += 1
        return True

    def _calc_last(self):
        if self.holds:
            self.last = self.holds[0]["price_mark"]
            return
        latest = self.curr["latest"]
        if self.last is None or latest > self.last:
            self.last = latest

    def _calc_share(self, price):
        den = (self.max - self.min) if (self.max and self.min) else ZERO
        num = (price - self.min) if self.min else ZERO
        ratio = (
            (num / den).quantize(SCALE_3, rounding=ROUND_HALF_UP) if den > 0 else ONE
        )
        if ratio < 0:
            ratio = ZERO
        expansion_ratio = ONE + (ONE - ratio) * self.expansion
        share = (
            self.amount_base
            * (ONE + self.profit_ratio)
            * expansion_ratio
            / (price * HUNDRED)
        ).quantize(ONE, rounding=ROUND_CEILING) * HUNDRED
        return share

    def _record_max_min(self):
        latest = self.curr["latest"]
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


def init_simulator(rule, kline_list):
    rule["amount_base"] = Decimal(rule["amount_base"])
    rule["ratio"] = Decimal(rule["ratio"])
    rule["expansion"] = Decimal(rule["expansion"])
    return Simulator(rule, kline_list)
