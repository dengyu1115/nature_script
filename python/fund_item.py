from sql_builder import sql_one, sql_each
from org.nature.util import PythonUtil
from org.nature.exception import Warn

sql_create_table = """
CREATE TABLE IF NOT EXISTS fund_item (
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    est_type TEXT NOT NULL,
    est_code TEXT,
    PRIMARY KEY (code)
)
"""

PythonUtil.ddl("nature/biz.db", sql_create_table)


def find_by_id(datum):
    return PythonUtil.find(
        "nature/biz.db",
        sql_one(
            "select * from fund_item where code={code}",
            datum,
        ),
    )


def list_valid():
    return PythonUtil.list(
        "nature/biz.db",
        "select * from fund_item where status='1'",
    )


def list_all():
    return PythonUtil.list(
        "nature/biz.db",
        "select * from fund_item",
    )


def map_code_name():
    item_list = list_all()
    return {i["code"]: i["name"] for i in item_list}


def save_to_db(data):
    return PythonUtil.update(
        "nature/biz.db",
        sql_each(
            "insert into fund_item(code,name,est_type,est_code,status) values[({code},{name},{est_type},{est_code},{status})]",
            data,
        ),
    )


def update_to_db(datum):
    return PythonUtil.update(
        "nature/biz.db",
        sql_one(
            "update fund_item set name={name},est_type={est_type},est_code={est_code},status={status} where code={code}",
            datum,
        ),
    )


def delete_from_db(datum):
    return PythonUtil.update(
        "nature/biz.db",
        sql_one(
            "delete from fund_item where code={code}",
            datum,
        ),
    )


def do_validate(datum):
    if "code" not in datum or not datum["code"]:
        raise Warn("编号不可为空")
    if "name" not in datum or not datum["name"]:
        raise Warn("名称不可为空")
    if "est_type" not in datum or not datum["est_type"]:
        raise Warn("估值类型不可为空")
    if datum["est_type"] != "" and ("est_code" not in datum or not datum["est_code"]):
        raise Warn("估值编号不可为空")
    if "status" not in datum or not datum["status"]:
        raise Warn("状态不可为空")
    if datum["status"] not in ["0", "1"]:
        raise Warn("状态只能为启用或暂停")


def do_save(datum):
    do_validate(datum)
    return save_to_db([datum])


def do_delete(datum):
    if "code" not in datum or not datum["code"]:
        raise Warn("编号不可为空")
    return delete_from_db(datum)


def do_update(datum):
    do_validate(datum)
    exists = find_by_id(datum)
    if not exists:
        raise Warn("项目不存在")
    return update_to_db(datum)
