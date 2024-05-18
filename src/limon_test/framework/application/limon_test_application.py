import os                                                           as _os

from conway.application.application                                 import Application
from conway.observability.logger                                    import Logger
from conway.util.path_utils                                         import PathUtils

from conway_acceptance.util.test_statics                            import TestStatics

class Test_Logger(Logger):
    '''
    This is a mock logger, needed in order to run the tests of the :class:`limon_test`.

    Specifically, it is needed by the :class:`Chassis_Test_Application`. Please refer to its
    documentation as to why these mock classes are needed in order to run the tests.
    '''


class Limon_Test_Application(Application):

    '''
    This is a mock application, which is needed in order to run the tests of the :class:`limon_test`.

    This is needed because the :class:`conway` requires that any business logic be run under
    the context of a global :class:`Application` object, which is normally the case for real applications, or 
    for tests of real applications.

    But for testing the :class:`conway` itself without a real application, the tests cases in 
    :class:`limon_test` wouldn't run unless there is (mock) Application as a global context.

    Hence this class, which is initialized in ``limon_test.__init__.py``
    '''
    def __init__(self):

        APP_NAME                                        = "LimonTestApp"

        # __file__ is something like
        #
        #       /home/alex/consultant1@CCL/dev/scratch_fork/scratch.test/src/limon_test/framework/application/chassis_test_application.py
        #
        # In that example, the config folder for the Conway test harness would be in 
        #
        #       /home/alex/consultant1@CCL/dev/scratch_fork/scratch.test/config
        #
        # So we can get that folder by navigating from __file__ the right number of parent directories up
        #
        config_path                                     = PathUtils().n_directories_up(__file__, 4) + "/config"

        logger                                          = Test_Logger(activation_level=Logger.LEVEL_INFO)

        # For ease of use, we want the test harness to be as "auto-configurable" as possible. So we want it
        # to be able to "discover" the location of the test scenarios repo, which normally is under the same
        # parent folder as the repo containing this file. So if the caller has not independently set up the
        # environment variable `TestStatics.SCENARIOS_REPO`, we give it a plausible default value
        # so that tests don't fail to run due to a missing environment variable.
        #
        # This way the caller still has the flexibility of choosing to deploy the scenarios repo 
        # in an unorthodox location and set `TestStatics.SCENARIOS_REPO` to point there. But for
        # most situations, where the scenarios repo is deployed in the "usual place" (i.e., under the same parent folder
        # as the repo containing this file), the default below will forgive callers for "forgetting" to set the environment
        # variable.
        #
        scenarios_repo                                  = _os.environ.get(TestStatics.SCENARIOS_REPO)
        if scenarios_repo is None:
            scenarios_repo                              = PathUtils().n_directories_up(__file__, 5) + "/scratch.scenarios"
            logger.log(f"${TestStatics.SCENARIOS_REPO} is not set - defaulting it to {scenarios_repo}",
                       log_level                = 1,
                       stack_level_increase     = 0)
            _os.environ[TestStatics.SCENARIOS_REPO] = scenarios_repo

          
        super().__init__(app_name=APP_NAME, config_path=config_path, logger=logger)

