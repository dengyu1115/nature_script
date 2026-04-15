import json
import datetime
from sql_builder import sql_one, sql_each
from consts import FORMAT_DATE
from org.nature.util import PythonUtil
from org.nature.exception import Warn

sql_create_table = """
create table if not exists workday (
    date text not null,
    type text not null,
    primary key (date)
);
"""

PythonUtil.ddl(
    "nature/common.db",
    sql_create_table,
)

sql_list_month_days = """
SELECT SUBSTR(date, 0, 7) AS month,
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '01' THEN type END) AS "01",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '02' THEN type END) AS "02",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '03' THEN type END) AS "03",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '04' THEN type END) AS "04",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '05' THEN type END) AS "05",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '06' THEN type END) AS "06",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '07' THEN type END) AS "07",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '08' THEN type END) AS "08",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '09' THEN type END) AS "09",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '10' THEN type END) AS "10",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '11' THEN type END) AS "11",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '12' THEN type END) AS "12",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '13' THEN type END) AS "13",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '14' THEN type END) AS "14",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '15' THEN type END) AS "15",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '16' THEN type END) AS "16",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '17' THEN type END) AS "17",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '18' THEN type END) AS "18",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '19' THEN type END) AS "19",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '20' THEN type END) AS "20",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '21' THEN type END) AS "21",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '22' THEN type END) AS "22",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '23' THEN type END) AS "23",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '24' THEN type END) AS "24",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '25' THEN type END) AS "25",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '26' THEN type END) AS "26",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '27' THEN type END) AS "27",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '28' THEN type END) AS "28",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '29' THEN type END) AS "29",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '30' THEN type END) AS "30",       
    MAX(CASE WHEN SUBSTR(date, 7, 2) = '31' THEN type END) AS "31"     
  FROM workday     
  WHERE date LIKE {year}     
  GROUP BY SUBSTR(date, 5, 2)     
  ORDER BY month;
"""

sql_count_by_year = "select count(*) as count from workday where date like {year}"


def is_workday(date):
    record = PythonUtil.find(
        "nature/common.db",
        sql_one(
            "select * from workday where date={date}",
            {"date": date},
        ),
    )
    return record and record["type"] == "W"


def get_latest_workday():
    today = datetime.datetime.now().strftime(FORMAT_DATE)
    workday_datum = PythonUtil.find(
        "nature/common.db",
        sql_one(
            "select * from workday where date<={date} and type='W' order by date desc limit 1",
            {"date": today},
        ),
    )
    return workday_datum["date"] if workday_datum else None


def save_to_db(data):
    if data:
        PythonUtil.update(
            "nature/common.db",
            sql_each(
                "insert into workday(date,type) values[({date},{type})]",
                data,
            ),
        )


def delete_by_year_from_db(year):
    PythonUtil.update(
        "nature/common.db",
        sql_one(
            "delete from workday where date like {year}",
            {"year": year + "%"},
        ),
    )


def list_by_year_from_network(year):
    url = f"https://tool.bitefu.net/jiari/"
    params = {"d": year}
    response = PythonUtil.get(url, None, params)
    data = json.loads(response)
    date_map = data[year]
    date_set = {year + key for key in date_map.keys()}
    start_day = datetime.datetime.strptime(year + "0101", "%Y%m%d")
    results = []
    for i in range(366):
        date = start_day + datetime.timedelta(days=i)
        day = date.strftime("%Y%m%d")
        if not day.startswith(year):
            break
        if date.weekday() == 5 or date.weekday() == 6 or day in date_set:
            results.append({"date": day, "type": "H"})
        else:
            results.append({"date": day, "type": "W"})
    return results


def list_month_days(year):
    return PythonUtil.list(
        "nature/common.db", sql_one(sql_list_month_days, {"year": year + "%"})
    )


def load(year):
    count = PythonUtil.find(
        "nature/common.db", sql_one(sql_count_by_year, {"year": year + "%"})
    )
    if count["count"] > 0:
        raise Warn(f"已存在{year}的数据")
    data = list_by_year_from_network(year)
    save_to_db(data)
    return len(data)


def reload(year):
    delete_by_year_from_db(year)
    data = list_by_year_from_network(year)
    save_to_db(data)
    return len(data)
