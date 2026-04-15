from org.nature.util import CtxUtil, JobUtil, PythonUtil
from sql_builder import sql_one, sql_each
from org.nature.service import JobService
from org.nature.exception import Warn

sql_create_table = """
CREATE TABLE IF NOT EXISTS job_config (
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    script TEXT NOT NULL,
    PRIMARY KEY (name)
)
"""

PythonUtil.ddl("nature/common.db", sql_create_table)


def find_by_id(datum):
    return PythonUtil.find(
        "nature/common.db",
        sql_one(
            "select name,status,script from job_config where name={name}",
            datum,
        ),
    )


def save_to_db(data):
    return PythonUtil.update(
        "nature/common.db",
        sql_each(
            "insert into job_config(name,status,script) values[({name},{status},{script})]",
            data,
        ),
    )


def update_to_db(datum):
    return PythonUtil.update(
        "nature/common.db",
        sql_one(
            "update job_config set status={status},script={script} where name={name}",
            datum,
        ),
    )


def delete_from_db(datum):
    return PythonUtil.update(
        "nature/common.db",
        sql_one("delete from job_config where name={name}", datum),
    )


def list_all():
    return PythonUtil.list(
        "nature/common.db", "select name,status,script from job_config"
    )


def list_valid():
    return PythonUtil.list(
        "nature/common.db",
        "select name,status,script from job_config where status='1'",
    )


def get_status():
    return CtxUtil.isServiceRunning(JobService)


def start_service():
    JobUtil.init()
    CtxUtil.startService(JobService)
    return get_status()


def stop_service():
    JobUtil.destroy()
    CtxUtil.stopService(JobService)
    return get_status()


def do_validate(datum):
    if "name" not in datum or not datum["name"]:
        raise Warn("名称不可为空")
    if "script" not in datum or not datum["script"]:
        raise Warn("脚本内容不可为空")
    if "status" not in datum or not datum["status"]:
        raise Warn("状态不可为空")
    if datum["status"] not in ["0", "1"]:
        raise Warn("状态只能为启用或暂停")


def do_save(datum):
    do_validate(datum)
    if find_by_id(datum):
        raise Warn("数据已存在")
    return save_to_db([datum])


def do_update(datum):
    do_validate(datum)
    if not find_by_id(datum):
        raise Warn("数据不存在")
    return update_to_db(datum)


def do_delete(datum):
    if not find_by_id(datum):
        raise Warn("数据不存在")
    return delete_from_db(datum)
