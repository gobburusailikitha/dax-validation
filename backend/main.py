import os
import tempfile
import subprocess
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests
from fastapi.middleware.cors import CORSMiddleware

TABULAR_EDITOR_EXE = r"C:\Program Files (x86)\Tabular Editor\TabularEditor.exe"
MODEL_BIM = r"C:\Users\LENOVO\Downloads\dax_validation\backend\model.bim"

VALID_FUNCTIONS = {"SUM", "AVERAGE", "COUNTROWS", "CALCULATE", "MIN", "MAX"}

app = FastAPI(title="DAX Validator API (TE2 + DAX Formatter)", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DaxRequest(BaseModel):
    dax: str
    table: Optional[str] = "Sales"


def basic_dax_check(dax: str) -> (bool, str):
    if dax.count("(") != dax.count(")"):
        return False, "Unbalanced parentheses"
    if dax.count("[") != dax.count("]"):
        return False, "Unbalanced brackets"
    functions = re.findall(r"([A-Z_0-9]+)\s*\(", dax)
    for f in functions:
        if f and f.upper() not in VALID_FUNCTIONS:
            return False, f"Unknown function (quick-check): {f}"
    return True, "Quick-sanity OK"


def dax_formatter_validate(dax: str):
    """Validate DAX using daxformatter.com API."""
    url = "https://www.daxformatter.com/api/daxformatter/DaxText"
    payload = {"Dax": dax, "ServersideError": True}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)

        if response.status_code != 200:
            return {"valid": False, "error": f"HTTP {response.status_code}", "raw": response.text}

        try:
            result = response.json()
        except Exception:
            return {"valid": False, "error": "Invalid JSON returned", "raw": response.text}

        if "Errors" in result and result["Errors"]:
            return {"valid": False, "errors": result["Errors"]}
        return {"valid": True, "formattedDax": result.get("Formatted", "")}

    except Exception as e:
        return {"valid": False, "error": str(e)}


@app.post("/validate")
def validate_dax(req: DaxRequest):
    ok, msg = basic_dax_check(req.dax)
    if not ok:
        return {"valid": False, "error": msg}

    if not os.path.exists(TABULAR_EDITOR_EXE) or not os.path.exists(MODEL_BIM):
        # Fallback to daxformatter.com
        return dax_formatter_validate(req.dax)

    dax_escaped = req.dax.replace('"', '""')
    table_escaped = req.table.replace('\\', '\\\\').replace('"', '\\"')

    script = f"""
    try
    {{
        var table = Model.Tables["{table_escaped}"];
        var dax = @\"{dax_escaped}\";

        if (dax.StartsWith("=")) dax = dax.Substring(1);

        var existing = table.Measures.FirstOrDefault(m => m.Name == "__TempMeasure__");
        if (existing != null) existing.Delete();

        var temp = table.AddMeasure("__TempMeasure__", dax, "");

        if (string.IsNullOrEmpty(temp.Expression))
        {{
            Error("EMPTY_EXPRESSION");
        }}
        else
        {{
            Info("DAX_OK");
        }}

        temp.Delete();
    }}
    catch(Exception ex)
    {{
        Error("EXCEPTION: " + ex.Message);
    }}
    """

    fd, script_path = tempfile.mkstemp(suffix=".cs", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(script)

        proc = subprocess.run(
            [TABULAR_EDITOR_EXE, MODEL_BIM, "-S", script_path],
            capture_output=True,
            text=True,
            timeout=60
        )

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        combined = stdout + ("\n---stderr---\n" + stderr if stderr else "")

        debug = {
            "returncode": proc.returncode,
            "stdout_head": "\n".join(stdout.splitlines()[:30]),
            "stderr_head": "\n".join(stderr.splitlines()[:30])
        }

        if "DAX_OK" in combined:
            return {"valid": True, "output": combined.strip(), "debug": debug}
        if "EXCEPTION:" in combined or "EMPTY_EXPRESSION" in combined:
            return {"valid": False, "output": combined.strip(), "debug": debug}
        if "Script compilation error" in combined:
            return {"valid": False, "output": combined.strip(), "debug": debug}

        return {"valid": False, "output": combined.strip(), "debug": debug}

    finally:
        try:
            os.remove(script_path)
        except Exception:
            pass