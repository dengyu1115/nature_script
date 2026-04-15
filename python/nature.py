import inspect


def dynamic_exec(code, params):
    scope = {}
    exec(code, scope)
    functions = [i for i in scope.values() if callable(i)]

    if functions:
        func = functions[0]
        sig = inspect.signature(func)
        args = {k: params.get(k) for k in sig.parameters.keys()}
        return func(**args)
    else:
        raise ValueError("提供的代码字符串中没有可执行的函数")
