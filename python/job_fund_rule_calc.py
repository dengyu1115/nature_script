from datetime import datetime, timedelta
import fund_rule
import fund_rule_exec
import workday
from consts import FORMAT_DATE
from org.nature.util import PythonUtil
from org.nature.util import NotifyUtil


def do_exec(date):

    hour = date.hour
    minute = date.minute
    second = date.second
    if not (hour == 8 and minute == 5 and second == 0):
        return
    yesterday = (datetime.now() + timedelta(days=-1)).strftime(FORMAT_DATE)
    if not workday.is_workday(yesterday):
        return

    fund_items = fund_rule.list_valid()

    count_list = PythonUtil.multiThread(fund_items, _calc)
    NotifyUtil.notifyOne(
        "规则计算完成", f"共计算{len(count_list)}条规则，保存{sum(count_list)}条数据"
    )


def _calc(item):
    try:
        return fund_rule_exec.do_calc(item)
    except Exception as e:
        NotifyUtil.notifyOne(f"规则 {item["code"]}：{item["name"]} 计算失败", str(e))
        return 0
