from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING, ROUND_HALF_UP
from datetime import datetime, timedelta
import bisect

SCALE_2 = Decimal("0.01")
SCALE_3 = Decimal("0.001")
SCALE_4 = Decimal("0.0001")
ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")

FORMAT_DATE = "%Y%m%d"
import json


class Simulator:

    def __init__(self, rule, kline_list):
        self.grid_type = rule["grid_type"]
        self.profit_type = rule["profit_type"]
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
        self.price_diff = ZERO

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
            if self.profit_type == "1":
                share = self._calc_share(price_mark)
            elif self.profit_type == "2":
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
        diff = mark - target
        if diff > self.price_diff:
            self.price_diff = diff
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
        hold_size = len(self.holds) - 1
        first = self.holds[0]
        mark = first["price_mark"]
        price_buy = first["price_buy"]
        if self.grid_type == "1":
            target = mark + self.price_diff
        elif self.grid_type == "2":
            target = (
                mark * (ONE + (self.ratio_sell - ONE) * (self.ratio_sell**hold_size))
            ).quantize(SCALE_3, rounding=ROUND_CEILING)
        elif self.grid_type == "3":
            target = (mark + self.price_diff * (self.ratio_sell**hold_size)).quantize(
                SCALE_3, rounding=ROUND_CEILING
            )
        elif self.grid_type == "4":
            target = ((mark * self.ratio_sell ** (hold_size + 1))).quantize(
                SCALE_3, rounding=ROUND_CEILING
            )
        else:
            target = (mark * self.ratio_sell).quantize(SCALE_3, rounding=ROUND_CEILING)
        high = self.curr["high"]
        if target > high:
            return False
        open_price = self.curr["open"]
        price_sell = open_price if target < open_price else target
        if self.profit_type == "1":
            share = self._calc_share(target)
        elif self.profit_type == "2":
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


if __name__ == "__main__":
    import os

    rule = {
        "code": "159941",
        "name": "百1加投",
        "type": "0",
        "grid_type": "4",
        "profit_type": "2",
        "amount_base": "10000",
        "ratio": "0.01",
        "expansion": "0",
    }
    # 读取json文件获取K线数据
    script_dir = os.path.dirname(os.path.abspath(__file__))
    kline_path = os.path.join(script_dir, "kline.json")
    with open(kline_path, "r", encoding="utf-8") as f:
        kline_lines = json.load(f)
    kline_list = [
        {
            "code": "159941",
            "type": "0",
            "date": parts[0].replace("-", ""),
            "open": Decimal(parts[1]),
            "latest": Decimal(parts[2]),
            "high": Decimal(parts[3]),
            "low": Decimal(parts[4]),
            "share": Decimal(parts[5]),
            "amount": Decimal(parts[6]),
        }
        for line in kline_lines
        for parts in [line.strip().split(",")]
        if len(parts) >= 7
    ]
    simulator = init_simulator(rule, kline_list)
    simulator.calc()
    profits = simulator.list_profit()
    if profits:
        print(profits[-1])
