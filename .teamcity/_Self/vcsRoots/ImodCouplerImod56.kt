package _Self.vcsRoots

import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.vcs.GitVcsRoot

object ImodCouplerImod56 : GitVcsRoot({
    name = "imod_coupler_imod56"
    pollInterval = 30
    url = "https://github.com/Deltares/imod_coupler"
    branch = "release_imod56"
    checkoutPolicy = GitVcsRoot.AgentCheckoutPolicy.USE_MIRRORS
})
