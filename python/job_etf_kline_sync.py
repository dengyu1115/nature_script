from datetime import datetime
import etf_item
import etf_kline
import workday
from consts import FORMAT_DATE
from org.nature.util import PythonUtil
from org.nature.util import NotifyUtil


def do_exec(date):

    if date.hour != 15 or date.minute != 10 or date.second != 0:
        return
    today = datetime.now().strftime(FORMAT_DATE)
    if not workday.is_workday(today):
        return

    etf_items = etf_item.list_valid()

    count_list = PythonUtil.multiThread(etf_items, _sync)
    NotifyUtil.notifyOne("K线数据同步成功", f"共同步{sum(count_list)}条数据")


def _sync(item):
    try:
        return etf_kline.load(item)
    except Exception as e:
        NotifyUtil.notifyOne("K线数据同步失败", item["code"] + str(e))
        return 0
