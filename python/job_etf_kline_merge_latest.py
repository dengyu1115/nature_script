from datetime import datetime
import etf_item
import etf_kline
import workday
from consts import FORMAT_DATE
from org.nature.util import PythonUtil
from org.nature.util import NotifyUtil


def do_exec(date):
    hour = date.hour
    minute = date.minute
    second = date.second
    if (
        not (hour == 9 and minute == 25 and second in [5, 15, 25, 35, 45])
        and not (hour == 15 and minute == 8 and second in [0, 30])
        and not (hour == 11 and second < 30)
        and not (hour == 9 and minute >= 30)
        and hour not in [10, 13, 14]
    ):
        return
    now = datetime.now()
    if (now.timestamp() - date.timestamp()) > 1000:
        return
    today = now.strftime(FORMAT_DATE)
    if not workday.is_workday(today):
        return

    etf_items = etf_item.list_valid()

    PythonUtil.multiThread(etf_items, _sync)


def _sync(item):
    try:
        return etf_kline.merge_latest(item)
    except Exception as e:
        NotifyUtil.notifyOne("K线数据同步失败", item["code"] + str(e))
        return 0
