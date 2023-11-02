# -*- coding: utf-8 -*-
import os

if os.name == "nt":
    os.environ["PYTHONMALLOC"] = "malloc"

pyaedt_path = os.path.dirname(__file__)

__version__ = "0.8.dev0"

version = __version__

try:
    pass
except:
    pass

