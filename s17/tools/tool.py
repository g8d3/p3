"""Tool implementation."""

import json
import subprocess
from typing import Dict, Any, List

from tools.base import ToolBase


class PythonREPLTool(ToolBase):
    """Python REPL tool for code execution."""
    
    def __init__(self):
        super().__init__(
            name="python_repl",
            description="Execute Python code and return the output"
        )
    
    def execute(self, args: Dict[str, Any]) -> str:
        """Execute Python code."""
        code = args.get("code", "")
        if not code:
            return "No code provided"
        
        try:
            import builtins
            output = []
            
            class OutputCapture:
                def write(self, text):
                    output.append(text)
                
                def flush(self):
                    pass
            
            old_stdout = builtins.stdout
            old_stderr = builtins.stderr
            
            builtins.stdout = OutputCapture()
            builtins.stderr = OutputCapture()
            
            try:
                exec(code, {})
                result = "".join(output)
                return result if result else "Code executed successfully (no output)"
            finally:
                builtins.stdout = old_stdout
                builtins.stderr = old_stderr
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_parameters(self) -> Dict:
        """Get parameters schema."""
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                }
            },
            "required": ["code"]
        }


class ShellCommandTool(ToolBase):
    """Shell command execution tool."""
    
    def __init__(self):
        super().__init__(
            name="shell",
            description="Execute a shell command and return the output"
        )
    
    def execute(self, args: Dict[str, Any]) -> str:
        """Execute a shell command."""
        command = args.get("command", "")
        if not command:
            return "No command provided"
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = []
            if result.stdout:
                output.append(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                output.append(f"STDERR:\n{result.stderr}")
            if result.returncode != 0:
                output.append(f"Exit code: {result.returncode}")
            
            return "\n".join(output) if output else "Command executed successfully"
            
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_parameters(self) -> Dict:
        """Get parameters schema."""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute"
                }
            },
            "required": ["command"]
        }


class WebSearchTool(ToolBase):
    """Web search tool."""
    
    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for information"
        )
    
    def execute(self, args: Dict[str, Any]) -> str:
        """Search the web."""
        query = args.get("query", "")
        if not query:
            return "No query provided"
        
        try:
            import urllib.parse
            import urllib.request
            
            url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0"
            })
            
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode("utf-8")
                
                import re
                snippets = re.findall(r'<a class="result__snippet"[^>]*>([^<]*)</a>', content)
                
                if snippets:
                    results = []
                    for i, snippet in enumerate(snippets[:5]):
                        results.append(f"{i+1}. {snippet.strip()}")
                    return "\n".join(results)
                else:
                    return "No results found"
                    
        except Exception as e:
            return f"Error searching: {str(e)}"
    
    def get_parameters(self) -> Dict:
        """Get parameters schema."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }


class FileReadTool(ToolBase):
    """File reading tool."""
    
    def __init__(self):
        super().__init__(
            name="file_read",
            description="Read the contents of a file"
        )
    
    def execute(self, args: Dict[str, Any]) -> str:
        """Read a file."""
        path = args.get("path", "")
        if not path:
            return "No path provided"
        
        try:
            with open(path, 'r') as f:
                content = f.read()
            
            max_length = 10000
            if len(content) > max_length:
                content = content[:max_length] + f"\n... ({len(content) - max_length} more characters)"
            
            return content
            
        except FileNotFoundError:
            return f"File not found: {path}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def get_parameters(self) -> Dict:
        """Get parameters schema."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read"
                }
            },
            "required": ["path"]
        }


class FileWriteTool(ToolBase):
    """File writing tool."""
    
    def __init__(self):
        super().__init__(
            name="file_write",
            description="Write content to a file"
        )
    
    def execute(self, args: Dict[str, Any]) -> str:
        """Write to a file."""
        path = args.get("path", "")
        content = args.get("content", "")
        
        if not path:
            return "No path provided"
        
        try:
            with open(path, 'w') as f:
                f.write(content)
            
            return f"Successfully wrote to {path}"
            
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    def get_parameters(self) -> Dict:
        """Get parameters schema."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                }
            },
            "required": ["path", "content"]
        }


class CalculatorTool(ToolBase):
    """Calculator tool for mathematical expressions."""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="Evaluate a mathematical expression"
        )
    
    def execute(self, args: Dict[str, Any]) -> str:
        """Evaluate a mathematical expression."""
        expression = args.get("expression", "")
        if not expression:
            return "No expression provided"
        
        try:
            import ast
            import operator
            
            allowed_ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
                ast.UAdd: operator.pos,
            }
            
            def eval_expr(node):
                if isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.BinOp):
                    if type(node.op) in allowed_ops:
                        return allowed_ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
                elif isinstance(node, ast.UnaryOp):
                    if type(node.op) in allowed_ops:
                        return allowed_ops[type(node.op)](eval_expr(node.operand))
                else:
                    raise TypeError(f"Unsupported expression: {ast.dump(node)}")
            
            result = eval_expr(ast.parse(expression, mode='eval').body)
            return str(result)
            
        except Exception as e:
            return f"Error evaluating expression: {str(e)}"
    
    def get_parameters(self) -> Dict:
        """Get parameters schema."""
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        }
