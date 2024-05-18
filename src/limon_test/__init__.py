
from conway.application.application                                 import Application
from limon_test.framework.application.limon_test_application        import Limon_Test_Application

# Start the global singleton that represents a (mock) application based on 
# :class:`conway`, so that the tests can run (since anything based on the class:`conway`
# requires a global :class:`Application` object to exist as context)
#
if Application._singleton_app is None:
    Limon_Test_Application()
