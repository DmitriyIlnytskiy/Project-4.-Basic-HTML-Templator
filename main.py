import re
from wsgiref.simple_server import make_server
#Template Engine
class TemplateEngine:
    def render(self, template_path: str, context: dict) -> str:
        with open(template_path, "r") as f:
            template = f.read()
        template = self._render_for(template, context)          #Part 4
        template = self._render_conditionals(template, context) #Parts 2, 3
        template = self._render_vars(template, context)         #Part 1
        return template
    
    #Part 1: Variables (with eval)
    def _render_vars(self, template: str, context: dict) -> str:
        def replace_var(match):
            expr = match.group(1).strip()
            try:
                # Safe eval(): Global scope is empty — preventing access to built-in functions or system operations.
                #Context is passed as locals — only user-defined data is accessible.
                return str(eval(expr, {}, context))
            except Exception:
                return ""  # unknown vars: ""
        return re.sub(r"\{\{\s*(.*?)\s*\}\}", replace_var, template)
    
    #Part 2-3: Conditionals
    def _render_conditionals(self, template: str, context: dict) -> str:
        pattern = r"\{% if (.*?) %\}(.*?)\{% endif %\}"
        def eval_block(match):
            #pattern has two capture groups in the regex:
            #everything between {% if and %} (the condition).
            #everything between {% ... %} and {% endif %} (the block content).

            condition = match.group(1).strip() #condition
            block = match.group(2) #block content
            
            # Split into if/elif/else
            parts = re.split(r"\{% (elif .*?|else) %\}", block)
            conditions = re.findall(r"\{% (elif .*?|else) %\}", block)
            blocks = [("if " + condition, parts[0])]
            for cond, content in zip(conditions, parts[1:]):
                if cond.startswith("elif"):
                    blocks.append((cond, content))
                else:
                    blocks.append(("else", content))
            for cond, content in blocks:
                if cond == "else":
                    return content
                else:
                    expr = cond.replace("elif", "").replace("if", "").strip()
                    try:
                        if eval(expr, {}, context):  # Safe eval
                            return content
                    except Exception:
                        pass
            return ""
        return re.sub(pattern, eval_block, template, flags=re.S)
    
    #Part 4: Loop
    def _render_for(self, template: str, context: dict) -> str:
        pattern = r"\{% for (\w+) in (\w+) %\}(.*?)\{% endfor %\}"
        def render_loop(match):
            var_name, list_name, block = match.groups()
            result = ""
            items = context.get(list_name, [])
            for item in items:
                local_context = dict(context)
                local_context[var_name] = item
                # Allow eval in inner variables
                result += self._render_vars(block, local_context)
            return result
        return re.sub(pattern, render_loop, template, flags=re.S)
    
    #////////////////////////////////////////////////////////////////////////////////////
#Router
class MyFramework:
    def __init__(self):
        self.routes = []
        self.engine = TemplateEngine()

    def __call__(self, environ, start_response):
        method = environ["REQUEST_METHOD"]
        path = environ["PATH_INFO"]
        for route_method, path_regex, param_names, handler in self.routes:
            if method == route_method:
                match = re.fullmatch(path_regex, path)
                if match:
                    kwargs = {name: value for name, value in zip(param_names, match.groups())}
                    response_text = handler(**kwargs)
                    content_type = "text/html" if response_text.strip().startswith("<") else "text/plain"
                    start_response("200 OK", [("Content-Type", content_type)])
                    return [response_text.encode("utf-8")]
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"404 Not Found"]
    
    def get(self, path):
        return self._add_route("GET", path)
    
    def post(self, path):
        return self._add_route("POST", path)
    
    def _add_route(self, method, path):
        param_names = []
        regex_parts = []
        for part in path.strip("/").split("/"):
            if part.startswith("<") and part.endswith(">"):
                name = part[1:-1]
                param_names.append(name)
                regex_parts.append("([^/]+)")
            else:
                regex_parts.append(part)
        path_regex = "^/" + "/".join(regex_parts) + "$"
        def decorator(func):
            self.routes.append((method, path_regex, param_names, func))
            return func
        return decorator
    
# --- App instance & routes ---
app = MyFramework()
# Part 1
@app.get("/hello/<name>/<age>/<city>")
def greeting(name, age, city):
    context = {"name": name, "age": int(age), "city": city}
    return app.engine.render("templates/greeting.html", context)

# Part 2
@app.get("/profile/<name>/<age>")
def profile(name, age):
    context = {"name": name, "age": int(age)}
    return app.engine.render("templates/profile.html", context)

# Part 3
@app.get("/status/<temperature>")
def status(temperature):
    context = {"temperature": int(temperature)}
    return app.engine.render("templates/status.html", context)

# Part 4
@app.get("/tasks")
def tasks():
    context = {"tasks": ["Write code", "Review notes", "Run server", "Test app"]}
    return app.engine.render("templates/tasks.html", context)

if __name__ == "__main__":
    with make_server("127.0.0.1", 8000, app) as server:
        print("Serving on http://127.0.0.1:8000")
        server.serve_forever()
