import importlib


class ConfigLoader:
    def __init__(self):
        self.config = {}

    def load_from_file(self, filename, objname=None):
        m = importlib.import_module(filename)
        if objname:
            self.load_from_object(getattr(m, objname))
        else:
            self.load_from_object(m)

    def load_from_object(self, obj):
        self.config.update({key: getattr(obj, key) for key in filter(
            lambda x: not callable(getattr(obj, x)) and not x.startswith("_"), dir(obj))
                            })

    def __getattr__(self, item):
        if item not in dir(self):
            return self.config.get(item)
        else:
            return super().__getattribute__(item)


config = ConfigLoader()
