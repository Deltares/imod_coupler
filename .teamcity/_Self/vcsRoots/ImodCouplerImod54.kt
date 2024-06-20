package _Self.vcsRoots

import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.vcs.GitVcsRoot

object ImodCouplerImod54 : GitVcsRoot({
    name = "imod_coupler_imod54"
    pollInterval = 30
    url = "https://github.com/Deltares/imod_coupler"
    branch = "release_imod54"
    checkoutPolicy = GitVcsRoot.AgentCheckoutPolicy.USE_MIRRORS
})
