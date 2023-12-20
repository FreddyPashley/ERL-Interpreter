import flask
import subprocess
import os
import json
import shutil

iteration_timeout = 10  # secs
brackets = False  # curly

keywords = {
    "endwhile": "",
    "endfunction": "",
    "endif": "",
    "elseif": "elif",
    "else": "else:",
    "function": "def",
    " then": ":",
    "^": "**",
    "MOD": "%",
    "//": "#",
    "DIV": "//",
    "AND": "and",
    "OR": "or",
    "NOT":"not",
    "const ": "",
    "true": "True",
    "false": "False",
    ".upper": ".upper()",
    ".lower": ".lower()",
    ".readLine(": ".readline(",
    ".writeLine(": ".writelines("
}

placeholder = """
function factorial(n)
    if n <= 1 then
        return 1
    else
        return n * factorial(n - 1)
    endif
endfunction

function main(n)
    result = factorial(abs(n))  // Absolute value of n --> positive value
    if n < 0 then
        if n MOD 2 == 0 then
            return result
        else
            return -result
        endif
    else
        return result
    endif
endfunction

for x=-7 to 12 step 3
    result = main(x)
    f_result = "{:,}".format(result)  // Python method of converting int to str with commas
    print(str(x) + "! = " + f_result)
next x
"""

def run_code(code):
    lines = [l.strip("\n") for l in code.split("\n")]
    if brackets: lines = [i.strip() for i in lines]
    codelines = []
    indent_lvl = 0

    function_count = 0
    endfunction_count = 0
    if_count = 0
    endif_count = 0
    for_count = 0
    endfor_count = 0
    while_count = 0
    endwhile_count = 0
    do_count = 0
    until_count = 0

    process_i = 0
    while "code"+str(process_i) in os.listdir("./"): process_i += 1

    for line_count, line_content in enumerate(lines):
        line = line_content
        if "endfunction" in line: endfunction_count += 1
        if "endif" in line: endif_count += 1
        if "endwhile" in line: endwhile_count += 1
        if "until " in line: until_count += 1

        if line.startswith("newFile("):
            path = line.split("newFile(")[1].strip("\r").strip(")").strip('"')
            if ".." in path or path.startswith("/"):
                line = "print('newFile() blocked due to attempt to reach outside environment')"
            else:
                file_path = line.replace("newFile(","").strip("\r")
                file_path = file_path.strip(")").strip('"')
                line = f"with open('{file_path}','w') as f: pass"
            
        elif "open(" in line:
            path = line.split("open(")[1].strip("\r").strip(")").strip('"')
            if ".." in path or path.startswith("/"):
                line = "print('File open() blocked due to attempt to reach outside environment')"

        elif ".writeLine(" in line:
            indent = ""
            for c in line:
                if c == " ": indent += " "
                else: break
            file_obj = line.strip("\r").split(".writeLine")[0]
            to_write = line.strip("\r").split(".writeLine")[1].strip("(").strip(")").strip('"')
            counter = line_count
            path = ""
            while counter >= 0:
                if "open(" in lines[counter] and file_obj+"=" in lines[counter] or file_obj+" =" in lines[counter]:
                    path = lines[counter].split("=")[1].strip("\r").strip().replace("open(","").strip(")").strip('"')
                    break
                else:
                    counter -= 1
            line = [f"{indent}with open('{path}', 'a') as f: f.writelines('{to_write}')"]
            if path != "": line.insert(0, f"{indent}{file_obj}.close()")

        elif "function " in line or "while " in line:
            line = line.strip("{").strip()
            line += ": " + ("{" if brackets else "")
            if "function " in line: function_count += 1
            if "while " in line: while_count += 1

        elif "if " in line: if_count += 1

        elif line.strip() == "do":
            do_count += 1
            indent = 0
            for c in line:
                if c == " ":
                    indent += 1
                else: break
            for l in lines:
                l_indent = 0
                for c in l:
                    if c == " ":
                        l_indent += 1
                    else: break
                if l_indent == indent and l.strip().startswith("until"): break
            condition = l.strip().replace("until ", "")
            i_num = 0
            for i in lines:
                while "i"+str(i_num) in i: i_num += 1
            for i in codelines:
                while "i"+str(i_num) in i: i_num += 1
            i_var = "i"+str(i_num)
            next_line = lines[line_count+1] if line_count+1 in range(len(lines)) else ""
            next_line_indent = 0
            for c in next_line:
                if c == " ": next_line_indent += 1
                else: break
            line = [f"{' '*indent}{i_var} = True", f"{' '*indent}while {i_var} is True or not {condition}:", f"{' '*next_line_indent}{i_var} = False"]
        elif line.strip().startswith("for "):
            for_count += 1
            indent = 0
            for c in line:
                if c == " ":
                    indent += 1
                else: break
            line = line.strip("}").strip("{").strip().split() if brackets else line.split()
            if "step" in line:
                keyword, start, to, end, step, stepper = line
            else:
                keyword, start, to, end = line
                step = stepper = None
            start = start.strip().split("=")
            i_var, starter = start
            stepper = f",{stepper}" if stepper else ""
            py_line = " "*indent + f"for {i_var} in range({starter},{end}{stepper})" + ": " + ("{" if brackets else "")
            line = py_line

        elif "next " in line: endfor_count += 1; continue
        elif "until " in line: continue

        elif ".length" in line:
            og_line = line
            line = line.split(".length")
            for i, t in enumerate(line):
                line[i] = t.split("(")[-1].split(",")[-1].split("=")[-1].strip(",").strip("return")
            for i, t in enumerate(line):
                to_replace = t+".length"
                replacement = "len("+t+")"
                og_line = og_line.replace(to_replace, replacement)
            line = og_line

        if type(line) == str: line = [line]
        for i in range(len(line)):
            l = line[i]
            if brackets:
                codelines.append(("    "*indent_lvl)+l.strip("{").strip("}"))
            else:
                codelines.append(l)

            if brackets:
                if l.endswith("{"):
                    indent_lvl += 1
                elif l.endswith("}"):
                    indent_lvl = indent_lvl - 1 if indent_lvl-1 >= 0 else 0

    messages = []
    if function_count != endfunction_count: messages.append(f"'function/endfunction' count doesn't match ({function_count}/{endfunction_count})")
    if if_count != endif_count: messages.append(f"'if/endif' count doesn't match ({if_count}/{endif_count})")
    if for_count != endfor_count: messages.append(f"'for/next var' count doesn't match ({for_count}/{endfor_count})")
    if while_count != endwhile_count: messages.append(f"while/endwhile count doesn't match ({while_count}/{endwhile_count})")
    if do_count != until_count: messages.append(f"do/until count doesn't match ({do_count}/{until_count})")
    if messages != []: messages.insert(0, "Server message: note that python accepts lack of 'end' statements however this isn't necessarily correct:")

    codelines.insert(0, f"os.chdir('./code{process_i}')")
    codelines.insert(0, "import os")

    lines = "\n".join(codelines).replace("\r", "")
    for k in keywords:
        lines = lines.replace(k, keywords[k])

    try:
        os.mkdir("code"+str(process_i))
        with open(f"code{process_i}/code_to_run.txt", "w") as f: f.write(lines)

        # result = subprocess.run("py code_to_run.txt", capture_output=True, text=True, shell=True, timeout=10)
        result = subprocess.check_output(f"py code{process_i}/code_to_run.txt", stderr=subprocess.STDOUT, timeout=iteration_timeout)

        with open(f"code{process_i}/code_to_run.txt") as f:
            code_run = [i.replace("\n", "") for i in f.readlines()]

        for i in range(len(code_run)):
            if code_run[i].strip() != "":
                spaces = 0
                chars = code_run[i]
                for char in chars:
                    if char == " ":
                        spaces += 4
                    else: break
            else:
                code_run[i] = ""
                spaces = 0
            code_run[i] = [code_run[i], spaces]

        code_run.pop(0)  # import os, os.chdir (remove)
        code_run.pop(0)

        shutil.rmtree(f"./code{process_i}")

        if hasattr(result, "stderr") and result.stderr != "":
            """err = str(result.stderr)
            err = err.split("line")[1:]
            err = "line"+" ".join(err)
            return str(err)"""
            return [str("\n".join(result.stderr.split("\n")[1:])), code_run]
        
        # return result.stdout.strip()
        return [bytes.decode(result)+"\n\n"+"\n-".join(messages), code_run]
    
    except subprocess.TimeoutExpired:
        shutil.rmtree(f"./code{process_i}")
        return [f"Server message: Iteration timeout (>{iteration_timeout}s)"+"\n\n"+"\n-".join(messages), ""]
    except subprocess.CalledProcessError as e:
        shutil.rmtree(f"./code{process_i}")
        return [bytes.decode(e.output)+"\n\n"+"\n-".join(messages), ""]
    except Exception as e:
        shutil.rmtree(f"./code{process_i}")
        if type(e) == SyntaxError:
            return [str(e)+"\n\n"+"\n-".join(messages), code_run]
        else:
            raise e


app = flask.Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if flask.request.method == "POST":
        if "textareaValue" in flask.request.form:
            textareaValue = flask.request.form["textareaValue"]
            codeValue = flask.request.form["codeValue"]

            if type(textareaValue) == list:
                textareaValue = [value.decode('utf-8').replace("\\r","") if type(value) != str else value for value in textareaValue]
            else:
                textareaValue = textareaValue.replace("\\r","").replace("\r","")
            if type(codeValue) == list:
                codeValue = [value.decode('utf-8') if type(value) != str else value for value in codeValue]
            else:
                codeValue = codeValue.replace("\\r","").replace("\r","")

            with open("reports.json") as f: reports = json.load(f)
            key = int(max([i for i in reports.keys()] if len(reports.keys()) > 0 else [0])) + 1
            reports[str(key)] = {
                "code" : textareaValue,
                "output" : codeValue
            }
            with open("reports.json", "w") as f:
                json.dump(reports, f, skipkeys=True, indent=4)

            return flask.render_template("index.html", code=textareaValue, output=[], py_lines=None)
        
        elif "code" in flask.request.form:
            code = flask.request.form["code"]
            if "input(" in code:
                return flask.render_template("index.html", code=code, output=["Server message: Inputs not compatible"], py_lines=[])
            output, py_equiv = run_code(code)
            return flask.render_template("index.html", code=code, output=output.split("\n"), py_lines=py_equiv)
        else:
            return flask.render_template("index.html", code="", output=[], py_lines=None)    
    else:
        return flask.render_template("index.html", code=placeholder, output=[], py_lines=None)


app.run()