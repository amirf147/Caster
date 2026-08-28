import subprocess
import time
import sys
import json
from xmlrpc.client import ServerProxy

print("Starting HUD process with py -3.10...")
proc = subprocess.Popen(["py", "-3.10", "castervoice/asynch/hud.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

try:
    time.sleep(2.0)
    print("Connecting to XML-RPC on 8338...")
    proxy = ServerProxy("http://127.0.0.1:8338", allow_none=True)
    
    print("1. Pinging HUD...")
    ping_res = proxy.ping()
    print("Ping response:", ping_res)
    
    print("2. Calling toggle_status_bar()...")
    proxy.toggle_status_bar()
    print("toggle_status_bar() returned successfully!")
    
    time.sleep(0.5)
    print("3. Calling toggle_rules_bar()...")
    proxy.toggle_rules_bar()
    print("toggle_rules_bar() returned successfully!")
    
    time.sleep(0.5)
    print("4. Calling toggle_scrollbars()...")
    proxy.toggle_scrollbars()
    print("toggle_scrollbars() returned successfully!")
    
    time.sleep(0.5)
    print("5. Calling show_help()...")
    proxy.show_help()
    print("show_help() returned successfully!")
    
    time.sleep(0.5)
    print("6. Calling show_rules()...")
    sample_rules = [{"name": "CasterRule", "rules": [{"name": "TestRule", "specs": ["show caster hud::show_hud"]}]}]
    proxy.show_rules(json.dumps(sample_rules))
    print("show_rules() returned successfully!")
    
    print("All XML-RPC operations succeeded flawlessly!")

finally:
    proc.terminate()
    try:
        stdout, stderr = proc.communicate(timeout=3)
        if stdout: print("HUD stdout:", stdout)
        if stderr: print("HUD stderr:", stderr)
    except Exception as e:
        print("Error reading proc:", e)
