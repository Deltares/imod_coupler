package IMODCollector.vcsRoots

import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.vcs.GitVcsRoot

object IMODCollector_ImodCouplerReleaseImod53 : GitVcsRoot({
    name = "imod_coupler_release_imod53"
    url = "https://github.com/Deltares/imod_coupler"
    branch = "refs/heads/release_imod53"
    useTagsAsBranches = true
    checkoutPolicy = GitVcsRoot.AgentCheckoutPolicy.USE_MIRRORS
})
