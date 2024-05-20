import sys                                                                          as _sys

from conway.database.data_accessor                                                  import DataAccessor
from conway.util.profiler                                                           import Profiler
from conway.util.secrets                                                            import Secrets

from conway_acceptance.test_logic.acceptance_test_notes                             import AcceptanceTestNotes

from conway_ops.onboarding.repo_bundle_subset                                       import RepoBundleSubset
from limon_ops.onboarding.repo_setup                                                import RepoSetup

from limon_ops.repo_admin.branch_lifecycle_manager                                 import BranchLifecycleManager
from conway_ops.util.git_branches                                                   import GitBranches

# Make sure the limon test app is used, by importing *first* the package for limon_test before the conway_test
# packages get imported
import limon_test

from conway_test.framework.test_logic.chassis_test_context                          import Chassis_TestContext
from conway_test.framework.test_logic.chassis_excels_to_compare                     import Chassis_ExcelsToCompare

from limon_test.tests_conway_ops.repo_manipulation_test_case                       import RepoManipulationTestCase
from conway_test.util.conway_test_utils                                             import ConwayTestUtils

class TestRepoSetup(RepoManipulationTestCase):

    def test_repo_setup(self):
        '''
        Checks that the :class:`RepoAdministration` correctly creates a feature branch for all pertinent repos.

        '''
        MY_NAME                                         = "onboarding.test_repo_setup"

        notes                                           = AcceptanceTestNotes("database_structure", self.run_timestamp)

        excels_to_compare                               = Chassis_ExcelsToCompare()
        

        with Chassis_TestContext(MY_NAME, notes=notes) as ctx:

            project                                     = ConwayTestUtils.project_name(ctx.scenario_id)
            excels_to_compare.addXL_RepoStats(project)

            sdlc_root                                   = f"{ctx.manifest.path_to_seed()}/sdlc_root"

            local_repos_root                            = ctx.test_database.local_repos_hub.hub_root()
            remote_repos_root                           = ctx.test_database.remote_repos_hub.hub_root()

            # Pre-flight: create the repos in question
            creation_result                             = self._create_github_repos(ctx)

            # Now we can do the test: setup local repos that are cloned from GitHub
            #
            admin                                       = RepoSetup(sdlc_root       = sdlc_root,
                                                                    profile_name    = self.profile_name)
            
            # Create the local development environment
            admin.setup(project)                

            # Before we create the branch manager, we will need a scenario-specific RepoBundle class
            # to be added, since it will be instantiated when we later call self._branch_manager(ctx)
            #
            # So we copy a previously prepared class to the ops repo:
            #
            with Profiler("Creating branch report"):
                with DataAccessor(url = f"{local_repos_root}") as ax:
                    ax.copy_from(src_url=f"{ctx.manifest.path_to_seed()}/files_to_add")

                branch_manager                          = self._branch_manager(ctx)


                branch_manager.create_repo_report(publications_folder           = ctx.manifest.path_to_actuals(), 
                                                    mask_nondeterministic_data  = True)

            self.assert_database_structure(ctx, excels_to_compare)  

    def _branch_manager(self, ctx):
        '''
        Returns a BranchLifecycleManager instance aligned with the `ctx`

        :param Chassis_TestContext ctx: the context under which a test case is running
        :returns: a BranchLifecycleManager instance
        :rtype: BranchLifecycleManager
        '''
        P                               = ctx.manifest.profile

        PROJECT                         = ConwayTestUtils.project_name(ctx.scenario_id)
  
        GH_ORGANIZATION                 = P.GH_ORGANIZATION
        USER                            = P.USER
        REPO_LIST                       = P.REPO_LIST(PROJECT)

        REMOTE_ROOT                     = P.REMOTE_ROOT

        OPERATE                         = self._is_operate(ctx)

        LOCAL_DEV_ROOT                  = P.LOCAL_ROOT(operate=OPERATE, root_folder=None)


        DEV_PROJECT_ROOT                = f"{LOCAL_DEV_ROOT}/{PROJECT}"

        GH_SECRETS_PATH                 = Secrets.SECRETS_PATH()
 
        REPO_BUNDLE, path               = P.instantiate_repo_bundle(PROJECT, operate=OPERATE)

        PROJECT_LOCAL_BUNDLE            = RepoBundleSubset(REPO_BUNDLE, REPO_LIST)

        DEV_ADMIN                       = BranchLifecycleManager(
                                                    local_root              = DEV_PROJECT_ROOT, 
                                                    remote_root             = REMOTE_ROOT, 
                                                    repo_bundle             = PROJECT_LOCAL_BUNDLE,
                                                    remote_gh_user          = USER, 
                                                    remote_gh_organization  = GH_ORGANIZATION,
                                                    gh_secrets_path         = GH_SECRETS_PATH)
        
        return DEV_ADMIN
    
    def _is_operate(self, ctx):
        '''
        Returns True if we are running tests in an operate branch, as opposed to a development branch

        :param Chassis_TestContext ctx: the context under which a test case is running
        :returns: True if we are in an operate branch, False otherwise.
        :rtype: bool
        '''
        if GitBranches.OPERATE_BRANCH.value in ctx.manifest.scenarios_root_folder:
            return True
        else:
            return False

if __name__ == "__main__":
    # In the debugger, executes only if we have a configuration that takes arguments, and the string
    # corresponding to the test method of interest should be configured in that configuration
    def main(args):
        T                                               = TestRepoSetup()
        T.setUp()
        what_to_do                                      = args[1]
        if what_to_do == "onboarding.test_repo_setup":
            T.test_repo_setup()

    main(_sys.argv)