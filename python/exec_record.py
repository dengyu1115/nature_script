import json
from sql_builder import sql_one
from org.nature.util import PythonUtil

sql_create_table = """
CREATE TABLE IF NOT EXISTS exec_record (
    code TEXT NOT NULL,
    date TEXT NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY (code, date)
)
"""

PythonUtil.ddl("nature/common.db", sql_create_table)


def get(code, date):
    record = PythonUtil.find(
        "nature/common.db",
        sql_one(
            "select * from exec_record where code={code} and date={date}",
            {"code": code, "date": date},
        ),
    )
    if record:
        return json.loads(record["content"])
    return {}


def set(code, date, record):
    content = json.dumps(record, ensure_ascii=False)
    PythonUtil.update(
        "nature/common.db",
        sql_one(
            "replace into exec_record(code,date,content) values({code},{date},{content})",
            {"code": code, "date": date, "content": content},
        ),
    )
