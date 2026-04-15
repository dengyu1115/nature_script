import re
from datetime import datetime


class SqlBuilder:
    """
    SQL 构建器类
    """

    @staticmethod
    def one(template, obj):
        """
        解析对象字段构建SQL
        :param template: sql模板
        :param obj: 数据集合
        :return: sql
        """
        # 模板可能是这种结构"insert into user(id,name) values({id},{name})"，对象可能是这种结构{id:1,name:"张三"}
        # 得到的sql是"insert into user(id,name) values(1,'张三')"
        # 可以根据字段的类型的自动进行拼接处理
        if not template or not obj:
            return ""
        
        # 使用正则表达式匹配所有 {字段名} 的占位符
        regex = r"\{(\w+)\}"
        sql = template
        
        # 找到所有匹配项
        matches = re.findall(regex, template)
        for field_name in matches:
            placeholder = f"{{{field_name}}}"
            if field_name in obj:
                value = obj[field_name]
                formatted_value = SqlBuilder.format_value(value)
                # 替换所有相同的占位符
                sql = sql.replace(placeholder, formatted_value)
            else:
                # 如果对象中没有这个字段，替换为NULL
                sql = sql.replace(placeholder, "NULL")
        
        return sql

    @staticmethod
    def each(template, items):
        """
        遍历数组构建SQL
        :param template: sql模板
        :param items: 数据集合
        :return: sql
        """
        # 模板可能是这种结构"insert into user(id,name) values[({id},{name})]"，对象可能是这种结构[{id:1,name:"张三"},{id:2,name:"张三"}]
        # 得到的sql是"insert into user(id,name) values(1,'张三'),(2,'张三')"
        # 可以遍历数组，根据字段的类型自动进行拼接处理
        if not template or not items or not isinstance(items, list) or len(items) == 0:
            return ""

        # 查找循环部分：用方括号 [] 括起来的部分，里面包含占位符
        loop_pattern = r"\[([^\[\]]*?\{.*?\}.*?)\]"
        match = re.search(loop_pattern, template)

        if match:
            # 提取循环部分（去掉方括号）
            loop_part = match.group(1)  # group(1) 是第一个捕获组，即方括号内的内容
            # 获取循环部分前和后的固定部分
            before_loop = template[:match.start()]
            after_loop = template[match.end():]
            sql_parts = []
            for item in items:
                part = SqlBuilder.one(loop_part, item)
                sql_parts.append(part)
            # 将前缀 + 循环部分处理结果 + 后缀
            return before_loop + ",".join(sql_parts) + after_loop
        else:
            raise ValueError("模板格式错误")

    @staticmethod
    def format_value(value):
        """
        根据值类型格式化值
        :param value: 要格式化的值
        :return: 格式化后的值
        """
        if value is None:
            return "NULL"
        if isinstance(value, str):
            # 转义字符串中的单引号
            return "'" + value.replace("'", "''") + "'"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, datetime):
            return f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'"
        # 对于其他类型，转换为字符串并加上引号
        return f"'{str(value)}'"


if __name__ == "__main__":
    # 测试示例
    print("测试 SqlBuilder 功能:")
    
    # 测试 one 方法
    obj = {"id": 1, "name": "张三"}
    template1 = "insert into user(id,name) values({id},{name})"
    result1 = SqlBuilder.one(template1, obj)
    print(f"one 结果: {result1}")
    
    # 测试 each 方法
    items = [
        {"id": 1, "name": "张三"},
        {"id": 2, "name": "李四"}
    ]
    template2 = "insert into user(id,name) values[({id},{name})]"
    result2 = SqlBuilder.each(template2, items)
    print(f"each 结果: {result2}")
    
    # 测试格式化功能
    obj3 = {"id": None, "name": "测试'单引号", "age": 25, "active": True, "date": datetime.now()}
    template3 = "insert into user(id,name,age,date,active) values({id},{name},{age},{date},{active})"
    result3 = SqlBuilder.one(template3, obj3)
    print(f"format test 结果: {result3}")