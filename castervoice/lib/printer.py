class _DelegatingPrinterMessageHandler(object):

    def __init__(self):
        self._queued_messages = []
        self._handlers = []
        self._error_handler = SimplePrintMessageHandler()

    def register_handler(self, handler):
        if handler in self._handlers:
            return
        self._handlers.append(handler)

    def unregister_handler(self, handler):
        if handler in self._handlers:
            self._handlers.remove(handler)
        else:
            for h in list(self._handlers):
                if type(h) is handler or (isinstance(handler, type) and isinstance(h, handler)):
                    self._handlers.remove(h)

    def has_handler(self, handler_type_or_instance):
        if handler_type_or_instance in self._handlers:
            return True
        if isinstance(handler_type_or_instance, type):
            return any(isinstance(h, handler_type_or_instance) for h in self._handlers)
        return any(type(h) is type(handler_type_or_instance) for h in self._handlers)

    def handle_message(self, items):
        self._queued_messages.append(items)
        if len(self._handlers) > 0:
            # transfer all messages to a temporary list for processing
            messages = self._queued_messages[:]
            # empty out the saved messages
            del self._queued_messages[:]

            for message in messages:
                for handler in self._handlers:
                    try:
                        handler.handle_message(message)
                    except:
                        self._error_handler.handle_message(message)


class BaseMessageHandler(object):

    def handle_message(self, items):
        """
        Child classes should implement this,
        doing something with the 'items' list.
        Each 'item' in the list is an object which
        was passed to printer.out as one of its *args.
        """
        from castervoice.lib.ctrl.mgr.errors.base_class_error import DontUseBaseClassError
        raise DontUseBaseClassError(self)


class SimplePrintMessageHandler(BaseMessageHandler):
    """
    A simple message handler which only prints messages to the console,
    newline-delimited.
    """

    def __init__(self):
        super(SimplePrintMessageHandler, self).__init__()
        self._print = print

    def handle_message(self, items):
        self._print("\n".join([str(m) for m in items]))


_DELEGATING_HANDLER = _DelegatingPrinterMessageHandler()


def out(*args):
    """
    Queues up a message to be printed or otherwise handled.
    """
    _DELEGATING_HANDLER.handle_message(args)


def get_delegating_handler():
    return _DELEGATING_HANDLER
