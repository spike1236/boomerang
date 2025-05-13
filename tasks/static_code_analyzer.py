from app.task_manager import task_processor
import ast


@task_processor
async def static_code_analyzer(input_text):
    code = input_text

    try:
        tree = ast.parse(code)
    except Exception as e:
        return f"Failed to parse code: {e}"

    report = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            report.append(f"Function: {node.name} (line {node.lineno})")
        elif isinstance(node, ast.AsyncFunctionDef):
            report.append(f"Async Function: {node.name} (line {node.lineno})")
        elif isinstance(node, ast.ClassDef):
            report.append(f"Class: {node.name} (line {node.lineno})")
            # List methods in the class
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    report.append(f"  Method: {item.name} (line {item.lineno})")
                elif isinstance(item, ast.AsyncFunctionDef):
                    report.append(f"  Async Method: {item.name} (line {item.lineno})")
    if not report:
        return "No functions or classes found."
    return f"```\n{chr(10).join(report)}\n```"
