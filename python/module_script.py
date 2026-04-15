import importlib.util
import sys, gc
from sql_builder import sql_one, sql_each
from org.nature.util import PythonUtil
from org.nature.exception import Warn


sql_ddl_create_table = """
create table if not exists module_script(
    module text not null,
    script text not null,
    status text not null,
    seq text not null,
    primary key (module)
)
"""

PythonUtil.ddl("nature/common.db", sql_ddl_create_table)


def load(module, script):
    spec = importlib.util.spec_from_loader(module, loader=None)
    module_obj = importlib.util.module_from_spec(spec)
    sys.modules[module] = module_obj
    exec(script, module_obj.__dict__)


def load_all():
    module_script_list = list_valid()
    for i in module_script_list:
        load(i["module"], i["script"])


def unload(module):
    del sys.modules[module]
    if module in sys.modules:
        del sys.modules[module]
    globals().pop(module, None)
    gc.collect()


def find_by_id(datum):
    return PythonUtil.find(
        "nature/common.db",
        sql_one(
            "select module,script,status,seq from module_script where module={module}",
            datum,
        ),
    )


def list_all():
    return PythonUtil.list(
        "nature/common.db",
        "select module,script,status,seq from module_script order by seq",
    )


def list_valid():
    return PythonUtil.list(
        "nature/common.db",
        "select module,script,status,seq from module_script where status='1' order by seq",
    )


def save_to_db(data):
    return PythonUtil.update(
        "nature/common.db",
        sql_each(
            "insert into module_script(module,script,status,seq) values[({module},{script},{status},{seq})]",
            data,
        ),
    )


def update_to_db(datum):
    return PythonUtil.update(
        "nature/common.db",
        sql_one(
            "update module_script set script={script},status={status},seq={seq} where module={module}",
            datum,
        ),
    )


def delete_from_db(datum):
    return PythonUtil.update(
        "nature/common.db",
        sql_one(
            "delete from module_script where module={module}",
            datum,
        ),
    )


def do_validate(datum):
    if "module" not in datum or not datum["module"]:
        raise Warn("模块不可为空")
    if "script" not in datum or not datum["script"]:
        raise Warn("脚本内容不可为空")
    if "status" not in datum or not datum["status"]:
        raise Warn("状态不可为空")
    if datum["status"] not in ["0", "1"]:
        raise Warn("状态只能为启用或暂停")
    if "seq" not in datum or not datum["seq"]:
        raise Warn("序号不可为空")


def do_save(datum):
    do_validate(datum)
    return save_to_db([datum])


def do_delete(datum):
    if "module" not in datum or not datum["module"]:
        raise Warn("模块不可为空")
    return delete_from_db(datum)


def do_update(datum):
    do_validate(datum)
    exists = find_by_id(datum)
    if not exists:
        raise Warn(f"模块{datum["module"]}不存在")
    return update_to_db(datum)
