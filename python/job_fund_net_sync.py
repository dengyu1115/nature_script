from datetime import datetime, timedelta
import fund_item
import fund_net
import workday
from consts import FORMAT_DATE
from org.nature.util import PythonUtil
from org.nature.util import NotifyUtil


def do_exec(date):
    hour = date.hour
    minute = date.minute
    second = date.second
    if not (hour == 8 and minute == 0 and second == 0):
        return
    yesterday = (datetime.now() + timedelta(days=-1)).strftime(FORMAT_DATE)
    if not workday.is_workday(yesterday):
        return

    fund_items = fund_item.list_valid()

    count_list = PythonUtil.multiThread(fund_items, _sync)
    NotifyUtil.notifyOne("净值数据同步成功", f"共同步{sum(count_list)}条数据")


def _sync(item):
    try:
        return fund_net.load(item["code"])
    except Exception as e:
        NotifyUtil.notifyOne("净值数据同步失败", item["code"] + str(e))
        return 0
