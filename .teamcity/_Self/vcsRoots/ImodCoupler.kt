package _Self.vcsRoots

import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.vcs.GitVcsRoot

object ImodCoupler : GitVcsRoot({
    name = "imod_coupler"
    url = "https://github.com/Deltares/imod_coupler"
    branch = "main"
    branchSpec = """
        +:refs/heads/*
        +:refs/tags/*
        -:refs/heads/gh-pages
    """.trimIndent()
    useTagsAsBranches = true
    checkoutPolicy = GitVcsRoot.AgentCheckoutPolicy.USE_MIRRORS
    authMethod = password {
        userName = "teamcity-deltares"
        password = "credentialsJSON:abf605ce-e382-4b10-b5de-8a7640dc58d9"
    }
})
