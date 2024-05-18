import abc

from conway.application.application                                 import Application
from conway.util.json_utils                                         import JSON_Utils

from conway_acceptance.test_logic.acceptance_test_case              import AcceptanceTestCase

from conway_ops.onboarding.user_profile                             import UserProfile
from conway_ops.util.git_branches                                   import GitBranches
from conway_ops.util.github_client                                  import GitHub_Client

# GOTCHA
#
# Multiple inheritance is not ideal, and here we use it only in a "soft way". The "real parent class" for us is
# AcceptanceTestCase, and abc.ABC we only use as a way to tag some methods as abstract.
#
# Since Python does support multiple inheritance, this is allowed, but Python also has method resolution order (MRO)
# semantics whereby if there are multiple parent classes and a parent class's method is called, it will first try to
# match a method signature in the parent that was declared first (when reading left to right)
# 
# So it is essential that we put the AcceptanceTestCase parent *before* the abc.ABC parent in the declaration.
#
class RepoManipulationTestCase(AcceptanceTestCase, abc.ABC):
    '''
    This class serves as a parent class for test cases that create, modify, delete or examine GIT repos.

    It implements some useful methods that such tests cases usually need.
    '''

    def setUp(self):
        '''
        '''
        super().setUp()

        self.profile_name                           = "TestRobot@CCL"

    def _create_github_repos(self, ctx):
        '''
        Creates a collection of GitHub repos for the test case identified by `ctx.scenario_id`, 
        as per standard Conway semantics for projects.

        For example, if `ctx.scenario_id = 8002`, then under normal configuration this method would create
        these 5 repos in GitHub:

        * scenario_8002.docs, scenario_8002.ops, scenario_8002.scenarios, scenario_8002.svc, scenario_8002.test
        
        The configuration required to do this is taken from a user profile specific to the test case in question.
        That user profile defines things like:

        * GitHub account and credentials (expected to be set to a test account)
        * The repos to create for the project. In the above example, if `ctx.scenario_id = 8002`, then the project
          would be `scenario_8002` and the profile is expected to define what repos belong to that project.

        The user configuration is identified by the name `self.profile_name` and it must reside in the local 
        file system under a folder defined by `ctx.manifest.path_to_seed()`.

        :param Chassis_TestContext ctx: context manager controlling the environmental settings under which a particular
            test is running.

        :returns: the status from GitHub, as a JSON dictionary, on the attempt to create the GitRepo `repo_name`.
        :rtype: dict
        '''
        sdlc_root                                   = f"{ctx.manifest.path_to_seed()}/sdlc_root"
        profile_path                                = f"{sdlc_root}/sdlc.profiles/{self.profile_name}/profile.toml" 
        P                                           = UserProfile(profile_path)  

        project_name                                = f"scenario_{ctx.scenario_id}"  

        # Inspector objects to connect to GitHub, but not tied to any specific repo. 
        #
        # NB: Here P.REMOTE_ROOT is something like
        #
        #   https://{OWNER}@github.com/{OWNER}".
        #
        # GOTCHA: P.REMOTE_ROOT is not used to create the URL of HTTP requests. It is only used to extract the
        #       owner of the repo.
        #
        github                                      = GitHub_Client(github_owner = P.GH_ORGANIZATION)

        # GitHub HTTP call is something like
        #
        #   'GET https://api.github.com/users/testrobot-ccl/repos'
        #
        pre_existing_repos                          = [r["name"] for r in github.GET(resource = "users", 
                                                                                     sub_path = "/repos")]

        for repo_name in P.REPO_LIST(project_name):
             

            if repo_name in pre_existing_repos:

                # Must delete this old repo, so that we can subsequently create it fresh. We do a
                #
                #   DELETE https://api.github.com/repos/testrobot-ccl/{repo_name}
                #
                removal_data                        = github.DELETE(resource = "repos",
                                                                    sub_path = f"/{repo_name}")
                nice_removal_data                   = JSON_Utils.nice(removal_data)
                Application.app().log(f"Removed pre-existing repo '{repo_name}' so we can re-create it - response was {nice_removal_data}")
                #raise ValueError(f"Can't create repo '{repo_name}' because it already exists in '{P.REMOTE_ROOT}'")

            # Create the repo. We do 
            #
            #       POST https://api.github.com/user/repos
            #
            # GOTCHA: the "user" resource is treated differenty by the GitHub_RepoInspector because the
            #           {owner} is not added to the URL
            #
            repo_creation_result                    = github.POST(
                                                            resource        = "user",
                                                            sub_path        = "/repos",
                                                            body            = 
                                                                {"name":            repo_name,
                                                                "description":      "Repo used as a fixture by Conway tests",
                                                                "auto_init":        True, # So a first commit with empty README is done
                                                                })
            
            #nice_data                               = JSON_Utils.nice(data) # This will show a lot of information
            repo_url                                = repo_creation_result["html_url"]
            Application.app().log(f"Created repo '{repo_name}' with URL {repo_url}")


            # We need to create the integration branch, but for that we first need to get the
            # the sha for the last commit on the master branch. For that we do:
            #
            #       GET https://api.github.com/repos/testrobot-ccl/{repo_name}/git/refs/heads
            #
            heads_data                                  = github.GET(
                                                            resource        = "repos",
                                                            sub_path        = f"/{repo_name}/git/refs/heads",
                                                            )
            # heads_data is something like
            #
            #    [
            #        {
            #            "ref": "refs/heads/master",
            #            "node_id": "REF_kwDOL6SBFbFyZWZzL2hlYWRzL21hc3Rlcg",
            #            "url": "https://api.github.com/repos/testrobot-ccl/scenario_8002.svc/git/refs/heads/master",
            #            "object": {
            #                "sha": "3f69985b23cf38dca098b3b867e28bf06a8a0aa5",
            #                "type": "commit",
            #                "url": "https://api.github.com/repos/testrobot-ccl/scenario_8002.svc/git/commits/3f69985b23cf38dca098b3b867e28bf06a8a0aa5"
            #            }
            #        },
            #           ...
            #    ]     
            #
            # So we extract the master branch, and from it get the SHA of interest
            #       
            master                                  = [elt for elt in heads_data if elt["ref"]  == "refs/heads/master"][0]
            sha                                     = master["object"]["sha"]

            # Now create the integration branch on the repo. We will do a 
            #
            #       POST https://api.github.com/repos/testrobot-ccl/{repo_name}/git/refs
            #
            integration                             = GitBranches.INTEGRATION_BRANCH.value
            branch_creation_result                  = github.POST(
                                                            resource        = "repos",
                                                            sub_path        = f"/{repo_name}/git/refs",
                                                            body            = {
                                                                "ref":      f"refs/heads/{integration}",
                                                                "sha":      f"{sha}"
                                                            })
            
            #nice_data                               = JSON_Utils.nice(data) # For debugging - will show all data returned
            branch_url                               = branch_creation_result["url"]
            Application.app().log(f"Created '{integration}' branch in '{repo_name}' with URL {branch_url}")
        
        

    def _get_files(self, root_folder):
        '''
        Overwrites parent to ignore files inside a ".git" folder, since GIT appears to use a non-deterministic
        way to hash objects

        @param root_folder A string representing the root of a folder structure
        '''
        all_files_l                                     = super()._get_files(root_folder)

        files_l                                         = [f for f in all_files_l if not ".git" in f.split("/")]

        return files_l