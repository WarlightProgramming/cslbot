# appengine_config.py
import os
from google.appengine.ext import vendor

# libraries are folder created by virtualenv
vendor.add(os.path.join(os.path.dirname(os.path.realpath(__file__)),
           'lib', 'python2.7', 'site-packages'))
