package IMODCollector.vcsRoots

import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.vcs.GitVcsRoot

object IMODCollector_ImodCouplerReleaseImod52 : GitVcsRoot({
    name = "imod_coupler_release_imod52"
    url = "https://github.com/Deltares/imod_coupler"
    branch = "refs/tags/v0.9.0"
    useTagsAsBranches = true
    checkoutPolicy = GitVcsRoot.AgentCheckoutPolicy.USE_MIRRORS
})
