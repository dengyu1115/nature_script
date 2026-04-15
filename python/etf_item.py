from sql_builder import sql_one, sql_each
from org.nature.util import PythonUtil
from org.nature.exception import Warn

sql_create_table = """
CREATE TABLE IF NOT EXISTS etf_item (
    code TEXT NOT NULL,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY (code,type)
)
"""

PythonUtil.ddl("nature/biz.db", sql_create_table)


def find_by_id(datum):
    return PythonUtil.find(
        "nature/biz.db",
        sql_one(
            "select code,type,name,status from etf_item where code={code} and type={type}",
            datum,
        ),
    )


def list_valid():
    return PythonUtil.list(
        "nature/biz.db",
        "select code,type,name,status from etf_item where status='1'",
    )


def list_all():
    return PythonUtil.list(
        "nature/biz.db",
        "select code,type,name,status from etf_item",
    )


def map_code_type_name():
    item_list = list_all()
    return {i["code"] + ":" + i["type"]: i["name"] for i in item_list}


def save_to_db(data):
    return PythonUtil.update(
        "nature/biz.db",
        sql_each(
            "insert into etf_item(code,type,name,status) values[({code},{type},{name},{status})]",
            data,
        ),
    )


def update_to_db(datum):
    return PythonUtil.update(
        "nature/biz.db",
        sql_one(
            "update etf_item set name={name},status={status} where code={code} and type={type}",
            datum,
        ),
    )


def delete_from_db(datum):
    return PythonUtil.update(
        "nature/biz.db",
        sql_one(
            "delete from etf_item where code={code} and type={type}",
            datum,
        ),
    )


def do_validate(datum):
    if "code" not in datum or not datum["code"]:
        raise Warn("编号不可为空")
    if "type" not in datum or not datum["type"]:
        raise Warn("类型不可为空")
    if "name" not in datum or not datum["name"]:
        raise Warn("名称不可为空")
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
    if "type" not in datum or not datum["type"]:
        raise Warn("类型不可为空")
    return delete_from_db(datum)


def do_update(datum):
    do_validate(datum)
    exists = find_by_id(datum)
    if not exists:
        raise Warn("项目不存在")
    return update_to_db(datum)
