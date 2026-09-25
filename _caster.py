'''
main Caster module
Created on Jun 29, 2014
'''
import atexit
import logging
import importlib
from dragonfly import get_engine, get_current_engine
from castervoice.lib import control
from castervoice.lib import settings
from castervoice.lib import printer
from castervoice.lib.ctrl.configure_engine import EngineConfigEarly, EngineConfigLate
from castervoice.lib.ctrl.dependencies import DependencyMan
from castervoice.lib.ctrl.updatecheck import UpdateChecker
from castervoice.asynch import hud_support

printer.out("@ - Starting {} with `{}` Engine -\n".format(settings.SOFTWARE_NAME, get_engine().name))

DependencyMan().initialize()  # requires nothing
settings.initialize()
UpdateChecker().initialize()  # requires settings/dependencies
EngineConfigEarly() # requires settings/dependencies


if control.nexus() is None:
    from castervoice.lib.ctrl.mgr.plugin_manager import PluginManager
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

    from castervoice.lib.ctrl.mgr.plugin_manager import get_plugin_manager
    _plugin_manager = get_plugin_manager(nexus=control.nexus(), settings_dict=settings.SETTINGS)
    _plugin_manager.load_plugins()

    if get_current_engine().name != "text" and settings.SETTINGS.get("hud", {}).get("enabled", True):
        from castervoice.asynch import hud_support
        dh = printer.get_delegating_handler()
        if not dh.has_handler(hud_support.HudPrintMessageHandler):
            dh.register_handler(hud_support.HudPrintMessageHandler())
        if not any(getattr(p, "replaces_hud", False) for p in _plugin_manager.get_loaded_plugins()):
            hud_support.start_hud()

    EngineConfigLate() # Requires grammars to be loaded and nexus
    _plugin_manager.start_plugins()

    import atexit

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

printer.out("\n") # Force update to display text
