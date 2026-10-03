'''
main Caster module
Created on Jun 29, 2014
'''
import logging
import importlib
from dragonfly import get_engine, get_current_engine
from castervoice.lib import control
from castervoice.lib import settings
from castervoice.lib import printer
from castervoice.lib.ctrl.configure_engine import EngineConfigEarly, EngineConfigLate
from castervoice.lib.ctrl.dependencies import DependencyMan
from castervoice.lib.ctrl.updatecheck import UpdateChecker

printer.out("@ - Starting {} with `{}` Engine -\n".format(settings.SOFTWARE_NAME, get_engine().name))

DependencyMan().initialize()  # requires nothing
settings.initialize()
UpdateChecker().initialize()  # requires settings/dependencies
EngineConfigEarly() # requires settings/dependencies


if control.nexus() is None:
    _plugins_enabled = settings.SETTINGS.get("plugins_config", {}).get("enabled", True)
    _plugin_manager = None

    if _plugins_enabled:
        from castervoice.lib.ctrl.mgr.plugin_manager import PluginManager, get_plugin_manager
        PluginManager.prepare_environment(settings.SETTINGS)

    from castervoice.lib.ctrl.mgr.loading.load.content_loader import ContentLoader
    from castervoice.lib.ctrl.mgr.loading.load.content_request_generator import ContentRequestGenerator
    from castervoice.lib.ctrl.mgr.loading.load.reload_fn_provider import ReloadFunctionProvider
    from castervoice.lib.ctrl.mgr.loading.load.modules_access import SysModulesAccessor
    _crg = ContentRequestGenerator()
    _rp = ReloadFunctionProvider()
    _sma = SysModulesAccessor()
    _content_loader = ContentLoader(_crg, importlib.import_module, _rp.get_reload_fn(), _sma)
    control.init_nexus(_content_loader)

    if settings.SETTINGS.get("sikuli", {}).get("enabled", False):
        from castervoice.asynch.sikuli import sikuli_controller
        sikuli_controller.get_instance().bootstrap_start_server_proxy()

    if _plugins_enabled:
        _plugin_manager = get_plugin_manager(nexus=control.nexus(), settings_dict=settings.SETTINGS)
        _plugin_manager.load_plugins()

    if get_current_engine().name != "text":
        from castervoice.asynch import hud_support
        dh = printer.get_delegating_handler()
        if not dh.has_handler(hud_support.HudPrintMessageHandler):
            dh.register_handler(hud_support.HudPrintMessageHandler())
        replaces_hud = False
        if _plugin_manager:
            replaces_hud = any(getattr(p, "replaces_hud", False) for p in _plugin_manager.get_loaded_plugins())
        if not replaces_hud and settings.SETTINGS.get("hud", {}).get("enabled", True):
            hud_support.start_hud()

    EngineConfigLate() # Requires grammars to be loaded and nexus
    if _plugin_manager:
        _plugin_manager.start_plugins()

    import atexit
    import ctypes

    def _shutdown_caster():
        try:
            from castervoice.lib.ctrl.mgr.plugin_manager import get_plugin_manager
            pm = get_plugin_manager()
            if pm:
                pm.stop_plugins()
        except Exception:
            pass
        try:
            from castervoice.asynch import hud_support
            hud_support.stop_hud()
        except Exception:
            pass

    atexit.register(_shutdown_caster)

    # Windows Console Close Event Hook (X button, Ctrl+C, logoff, terminal shutdown)
    if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "kernel32"):
        try:
            HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
            def _console_ctrl_handler(ctrl_type):
                _shutdown_caster()
                return False  # Let OS proceed with terminal closing

            _global_ctrl_handler = HandlerRoutine(_console_ctrl_handler)
            ctypes.windll.kernel32.SetConsoleCtrlHandler(_global_ctrl_handler, True)
        except Exception:
            pass

    # Cross-platform POSIX signal handlers (Linux / macOS / terminal)
    try:
        import signal

        def _signal_handler(signum, frame):
            _shutdown_caster()

        for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
            if sig is not None:
                try:
                    signal.signal(sig, _signal_handler)
                except Exception:
                    pass
    except Exception:
        pass

printer.out("\n") # Force update to display text
