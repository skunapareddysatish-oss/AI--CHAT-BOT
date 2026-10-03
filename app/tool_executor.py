from app.tools import AVAILABLE_FUNCTIONS


def execute_tool(name: str, arguments: dict):
    """
    Execute a tool by name using the supplied arguments.
    """

    if name not in AVAILABLE_FUNCTIONS:
        return f"Unknown tool: {name}"

    func = AVAILABLE_FUNCTIONS[name]

    try:
        return func(**arguments)

    except TypeError as e:
        return f"Tool argument error: {e}"

    except Exception as e:
        return f"Tool execution failed: {e}"