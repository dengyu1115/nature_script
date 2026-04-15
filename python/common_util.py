from datetime import datetime, timedelta
from org.nature.exception import Warn
from consts import FORMAT_DATE


def build_dates(date_rule, date_start=None, date_end=None):
    date = datetime.now()
    today = date.strftime(FORMAT_DATE)
    if date_rule == "00":
        if not date_start:
            raise Warn("请选择开始日期")
        if not date_end:
            raise Warn("请选择结束日期")
        if date_start >= date_end:
            raise Warn("结束日期不可早于开始日期")
        if date_start > today:
            raise Warn("开始日期不可晚于今天")
        return [date_start, date_end]
    if date_rule == "0":
        return ["", date_end or today]
    dates = []
    if date_rule == "1":
        for _ in range(32):
            dates.append(date.strftime(FORMAT_DATE))
            date = date - timedelta(days=1)
    elif date_rule == "2":
        date = date + timedelta(days=6 - date.weekday())
        for _ in range(53):
            dates.append(date.strftime(FORMAT_DATE))
            date = date - timedelta(days=7)
    elif date_rule == "3":
        if date.month == 12:
            date = datetime(date.year + 1, 1, 1)
        else:
            date = datetime(date.year, date.month + 1, 1)
        for _ in range(37):
            last_day = date - timedelta(days=1)
            dates.append(last_day.strftime(FORMAT_DATE))
            if date.month == 1:
                date = datetime(date.year - 1, 12, 1)
            else:
                date = datetime(date.year, date.month - 1, 1)
    elif date_rule == "4":
        date = datetime(date.year + 1, 1, 1)
        for _ in range(11):
            last_day = date - timedelta(days=1)
            dates.append(last_day.strftime(FORMAT_DATE))
            date = datetime(date.year - 1, 1, 1)
    else:
        raise Warn(f"日期规则不支持：{date_rule}")
    dates.reverse()
    return dates


def years(count):
    today = datetime.now()
    date = datetime(today.year + 1 if today.month == 12 else today.year, 1, 1)
    years = []
    for _ in range(count):
        years.append(date.strftime("%Y"))
        date = datetime(date.year - 1, 1, 1)
    return years


def add_day(date, days):
    return (datetime.strptime(date, FORMAT_DATE) + timedelta(days=days)).strftime(
        FORMAT_DATE
    )


def today():
    return datetime.now().strftime(FORMAT_DATE)


def yesterday():
    return (datetime.now() + timedelta(days=-1)).strftime(FORMAT_DATE)
