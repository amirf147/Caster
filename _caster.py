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
    from castervoice.lib.ctrl.mgr.loading.load.content_loader import ContentLoader
    from castervoice.lib.ctrl.mgr.loading.load.content_request_generator import ContentRequestGenerator
    from castervoice.lib.ctrl.mgr.loading.load.reload_fn_provider import ReloadFunctionProvider
    from castervoice.lib.ctrl.mgr.loading.load.modules_access import SysModulesAccessor
    _crg = ContentRequestGenerator()
    _rp = ReloadFunctionProvider()
    _sma = SysModulesAccessor()
    _content_loader = ContentLoader(_crg, importlib.import_module, _rp.get_reload_fn(), _sma)
    control.init_nexus(_content_loader)
    EngineConfigLate() # Requires grammars to be loaded and nexus

from castervoice.lib.ctrl.mgr.plugin_manager import PluginManager

_plugin_manager = PluginManager(nexus=control.nexus(), settings_dict=settings.SETTINGS)
_plugin_manager.load_plugins()
_plugin_manager.start_plugins()

printer.out("\n") # Force update to display text
