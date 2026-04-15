import hashlib
from datetime import datetime
from decimal import ROUND_HALF_UP
import fund_item
import fund_hold
import exec_record
import workday
from consts import FORMAT_DATE, SCALE_2
from org.nature.util import NotifyUtil


def do_exec(date):
    hour = date.hour
    minute = date.minute
    second = date.second
    if not (hour == 14 and minute in {55, 57, 59} and second == 0):
        return
    now = datetime.now()
    today = now.strftime(FORMAT_DATE)
    if not workday.is_workday(today):
        return

    holds = fund_hold.list_next_all()

    handle_map = exec_record.get("FUND_NOTICE", today)
    buy_exists = set(handle_map.get("buy", []))
    sell_exists = set(handle_map.get("sell", []))

    map_data = {}

    for hold in holds:
        key = calc_key(hold)
        net_sell = hold.get("net_sell")

        if net_sell is None:
            if key in buy_exists:
                continue
            fill_handle_data(
                map_data, hold, "buy", hold.get("net_buy"), hold.get("share")
            )
            buy_exists.add(key)
        else:
            if key in sell_exists:
                continue
            fill_handle_data(
                map_data,
                hold,
                "sell",
                hold.get("net_sell"),
                hold.get("share"),
            )
            sell_exists.add(key)

    text = build_text(map_data)

    if text is not None:
        NotifyUtil.notifyOne("交易提醒", text)
        NotifyUtil.speak(text)

    handle_map["buy"] = list(buy_exists)
    handle_map["sell"] = list(sell_exists)
    exec_record.set("FUND_NOTICE", today, handle_map)


def fill_handle_data(map_data, hold, handle_key, net, share):
    item_key = f"{hold["code"]}"

    if item_key not in map_data:
        map_data[item_key] = {}

    if handle_key not in map_data[item_key]:
        map_data[item_key][handle_key] = {}

    net_share = map_data[item_key][handle_key]

    if net not in net_share:
        net_share[net] = share
    else:
        net_share[net] = net_share[net] + share


def build_text(map_data):
    if not map_data:
        return None

    item_name_map = fund_item.map_code_name()

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
        for net, share in mb.items():
            builder.append(f"以价格{net}{handle}{format_share(share)}份")

    return "".join(builder)


def format_share(share):
    return share.quantize(SCALE_2, rounding=ROUND_HALF_UP)


def calc_key(i):
    input_str = f"{i['code']}:{i['rule']}:{i['date_buy']}"
    return hashlib.md5(input_str.encode()).hexdigest().upper()
