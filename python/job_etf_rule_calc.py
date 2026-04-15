from datetime import datetime
import etf_rule
import etf_rule_exec
import workday
from consts import FORMAT_DATE
from org.nature.util import PythonUtil
from org.nature.util import NotifyUtil


def do_exec(date):

    if date.hour != 15 or date.minute != 11 or date.second != 0:
        return
    today = datetime.now().strftime(FORMAT_DATE)
    if not workday.is_workday(today):
        return

    etf_items = etf_rule.list_valid()

    count_list = PythonUtil.multiThread(etf_items, _calc)
    NotifyUtil.notifyOne(
        "规则计算完成", f"共计算{len(count_list)}条规则，保存{sum(count_list)}条数据"
    )


def _calc(item):
    try:
        return etf_rule_exec.do_calc(item)
    except Exception as e:
        NotifyUtil.notifyOne(
            f"规则 {item["code"]}：{item["type"]}：{item["name"]} 计算失败", str(e)
        )
        return 0
