import workday
from org.nature.util import NotifyUtil


def do_exec(date):
    month = date.month
    day = date.day
    hour = date.hour
    minute = date.minute
    second = date.second
    if not (
        month == 12
        and day in (22, 25, 28)
        and hour == 8
        and minute == 0
        and second == 0
    ):
        return
    try:
        count = workday.load(str(date.year))
        NotifyUtil.notifyOne("工作日数据同步成功", f"共同步{count}条数据")
    except Exception as e:
        NotifyUtil.notifyOne("工作日数据同步失败", str(e))
