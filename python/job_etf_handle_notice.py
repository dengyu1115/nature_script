import hashlib
from datetime import datetime
from decimal import ROUND_HALF_UP
import etf_item
import etf_hold
import exec_record
import workday
from consts import FORMAT_DATE, ONE, HUNDRED
from org.nature.util import NotifyUtil


def do_exec(date):
    hour = date.hour
    minute = date.minute
    second = date.second
    if (
        not (hour == 9 and minute == 25 and second in [10, 20, 30, 40, 50])
        and not (hour == 11 and second < 30)
        and not (hour == 9 and minute >= 30)
        and hour not in [10, 13, 14, 21]
    ):
        return
    now = datetime.now()
    if (now.timestamp() - date.timestamp()) > 1000:
        return
    today = now.strftime(FORMAT_DATE)
    if not workday.is_workday(today):
        return

    holds = etf_hold.list_latest_all()

    handle_map = exec_record.get("ETF_NOTICE", today)
    buy_exists = set(handle_map.get("buy", []))
    sell_exists = set(handle_map.get("sell", []))

    map_data = {}

    for hold in holds:
        key = calc_key(hold)
        price_sell = hold.get("price_sell")

        if price_sell is None:
            if key in buy_exists:
                continue
            fill_handle_data(
                map_data, hold, "buy", hold.get("price_buy"), hold.get("share_buy")
            )
            buy_exists.add(key)
        else:
            if key in sell_exists:
                continue
            fill_handle_data(
                map_data,
                hold,
                "sell",
                hold.get("price_sell"),
                hold.get("share_sell"),
            )
            sell_exists.add(key)

    text = build_text(map_data)

    if text is not None:
        NotifyUtil.notifyOne("交易提醒", text)
        NotifyUtil.speak(text)

    handle_map["buy"] = list(buy_exists)
    handle_map["sell"] = list(sell_exists)
    exec_record.set("ETF_NOTICE", today, handle_map)


def fill_handle_data(map_data, hold, handle_key, price, share):
    item_key = f"{hold["code"]}:{hold["type"]}"

    if item_key not in map_data:
        map_data[item_key] = {}

    if handle_key not in map_data[item_key]:
        map_data[item_key][handle_key] = {}

    price_share = map_data[item_key][handle_key]

    if price not in price_share:
        price_share[price] = share
    else:
        price_share[price] = price_share[price] + share


def build_text(map_data):
    if not map_data:
        return None

    item_name_map = etf_item.map_code_type_name()

    builder = []
    for item_key, handle_map in map_data.items():
        builder.append(item_name_map.get(item_key, ""))
        builder.append(handle_text(handle_map, "buy", "买入"))
        builder.append(handle_text(handle_map, "sell", "卖出"))

    return "".join(builder)


def handle_text(handle_map, handle_key, handle):
    builder = []
    mb = handle_map.get(handle_key)

    if mb is not None:
        for price, share in mb.items():
            builder.append(f"以价格{price}{handle}{format_share(share)}手。")

    return "".join(builder)


def format_share(share):
    return (share / HUNDRED).quantize(ONE, rounding=ROUND_HALF_UP)


def calc_key(i):
    input_str = f"{i['code']}:{i['type']}:{i['rule']}:{i['date_buy']}:{i['level']}"
    return hashlib.md5(input_str.encode()).hexdigest().upper()
