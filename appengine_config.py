# appengine_config.py
import os
from google.appengine.ext import vendor

# libraries are in the 'libs' folder
vendor.add(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'libs'))
