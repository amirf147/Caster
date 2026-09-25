import json
import subprocess
import sys
import time
import queue
import threading

from dragonfly import CompoundRule, MappingRule, get_current_engine, Function
from pathlib import Path

try:  # Style C -- may be imported into Caster, or externally
    BASE_PATH = str(Path(__file__).resolve().parent.parent)
    if BASE_PATH not in sys.path:
        sys.path.append(BASE_PATH)
finally:
    from castervoice.lib import settings

from castervoice.lib import printer, control, utilities
from castervoice.lib.rules_collection import get_instance


from castervoice.asynch.process_lifecycle import get_process_strategy

_HUD_PROCESS = None
_CURRENT_HUD_PATH = None
_IS_STARTING = False
_PROCESS_STRATEGY = get_process_strategy()


def _wait_for_port_release(port=8338, timeout=2.0):
    import socket
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                time.sleep(0.1)
        except (socket.error, ConnectionRefusedError, OSError):
            return True
    return False


def start_hud(hud_path=None):
    """
    Starts the external HUD process.
    If hud_path is None, launches the default standard HUD configured in settings.
    Binds the child process using cross-platform OS lifecycle strategies.
    """
    global _HUD_PROCESS, _CURRENT_HUD_PATH, _IS_STARTING
    if hud_path is None:
        try:
            hud_path = settings.SETTINGS["paths"]["HUD_PATH"]
        except Exception:
            hud_path = "hud.py"
    _CURRENT_HUD_PATH = hud_path

    if _IS_STARTING:
        return
    _IS_STARTING = True
    try:
        if _HUD_PROCESS is not None and _HUD_PROCESS.poll() is None:
            try:
                hud = control.nexus().comm.get_com("hud")
                hud.show_hud()
            except Exception:
                pass
            return

        hud = control.nexus().comm.get_com("hud")
        try:
            hud.ping()
            hud.show_hud()
            return
        except Exception:
            pass

        try:
            pythonw = settings.SETTINGS["paths"]["PYTHONW"]
        except Exception:
            pythonw = sys.executable

        popen_kwargs = _PROCESS_STRATEGY.get_popen_kwargs()
        _HUD_PROCESS = subprocess.Popen([pythonw, hud_path], **popen_kwargs)
        _PROCESS_STRATEGY.bind_process(_HUD_PROCESS)
    finally:
        _IS_STARTING = False


def stop_hud():
    """Signals the external HUD process to gracefully shut down and ensures port release."""
    global _HUD_PROCESS
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.kill()
    except Exception:
        pass
    if _HUD_PROCESS is not None:
        try:
            _HUD_PROCESS.wait(timeout=1.5)
        except Exception:
            _PROCESS_STRATEGY.terminate_process(_HUD_PROCESS)
        _HUD_PROCESS = None
    _wait_for_port_release(8338, timeout=1.0)


def restart_hud():
    """Gracefully terminates the HUD process and restarts it cleanly."""
    global _CURRENT_HUD_PATH
    path_to_restart = _CURRENT_HUD_PATH
    stop_hud()
    time.sleep(0.5)
    start_hud(path_to_restart)


def show_hud():
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.show_hud()
    except Exception:
        try:
            start_hud()
        except Exception as e:
            printer.out("Unable to show hud. Hud not available. \n{}".format(e))


def hide_hud():
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.hide_hud()
    except Exception as e:
        printer.out("Unable to hide hud. Hud not available. \n{}".format(e))


def clear_hud():
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.clear_hud()
    except Exception as e:
        printer.out("Unable to clear hud. Hud not available. \n{}".format(e))
        Function(utilities.clear_log).execute()


def show_rules():
    """
    Get a list of active grammars loaded into the current engine,
    including active rules and their attributes. Send the list
    to HUD GUI for display.
    """
    grammars = []
    engine = get_current_engine()
    if engine and hasattr(engine, "grammars"):
        for grammar in engine.grammars:
            if any([r.active for r in grammar.rules]):
                rules = []
                for rule in grammar.rules:
                    if rule.active and not rule.name.startswith('_'):
                        if isinstance(rule, CompoundRule):
                            specs = [rule.spec]
                        elif isinstance(rule, MappingRule):
                            specs = sorted(["{}::{}".format(x, rule._mapping[x]) for x in rule._mapping])
                        else:
                            specs = [rule.element.gstring()]
                        rules.append({
                            "name": rule.name,
                            "exported": rule.exported,
                            "specs": specs
                        })
                grammars.append({"name": grammar.name, "rules": rules})
    grammars.extend(get_instance().serialize())
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.show_rules(json.dumps(grammars))
    except Exception as e:
        printer.out("Unable to show hud. Hud not available. \n{}".format(e))


def hide_rules():
    """
    Instruct HUD to hide the frame with the list of rules.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.hide_rules()
    except Exception as e:
        printer.out("Unable to show hud. Hud not available. \n{}".format(e))


class HudPrintMessageHandler(printer.BaseMessageHandler):
    """
    Asynchronous, non-blocking HUD message handler.
    Queues messages in-memory so the Dragonfly speech recognition loop
    never blocks on XML-RPC network timeouts or HUD downtime.

    @ Purple arrow - Bold Text - Important Info
    # Red arrow - Plain text - Caster Info
    $ Blue arrow - Plain text - Commands/Dictation
    """

    def __init__(self):
        super(HudPrintMessageHandler, self).__init__()
        try:
            self.hud = control.nexus().comm.get_com("hud")
        except Exception:
            self.hud = None
        self._queue = queue.Queue(maxsize=500)
        self._worker = threading.Thread(target=self._process_queue, name="HudPrintWorker")
        self._worker.daemon = True
        self._worker.start()

    def handle_message(self, items):
        text = "\n".join([str(m) for m in items])
        try:
            self._queue.put_nowait(text)
        except Exception:
            pass

    def _process_queue(self):
        while True:
            try:
                text = self._queue.get()
                try:
                    if self.hud is None:
                        self.hud = control.nexus().comm.get_com("hud")
                    if self.hud is not None:
                        self.hud.send(text)
                except Exception:
                    # HUD is closed or not responding; sleep briefly in background thread
                    time.sleep(1.0)
            except Exception:
                time.sleep(0.5)