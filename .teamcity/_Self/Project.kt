package _Self

import _Self.buildTypes.TestPrimodWin64
import _Self.buildTypes.*
import _Self.vcsRoots.*
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.Project
import jetbrains.buildServer.configs.kotlin.buildFeatures.PullRequests
import jetbrains.buildServer.configs.kotlin.buildFeatures.pullRequests
import jetbrains.buildServer.configs.kotlin.triggers.vcs

object Project : Project({
    description = "Python scripts coupling components"

    vcsRoot(MetaSwapLookupTable)
    vcsRoot(ImodCoupler)

    buildType(MyPy)
    buildType(TestbenchCouplerWin64)
    buildType(TestPrimodWin64)
    buildType(Main)

    subProject(IMODCollector.Project)
})

object Main : BuildType({
    name = "Main"

    type = Type.COMPOSITE

    vcs {
        root(ImodCoupler)

        cleanCheckout = true
        branchFilter = """
            +:*
            -:release_imod56
        """.trimIndent()
    }

    triggers {
        vcs {
        }
    }

    features {
        pullRequests {
            vcsRootExtId = "${ImodCoupler.id}"
            provider = github {
                authType = token {
                    token = "credentialsJSON:71420214-373c-4ccd-ba32-2ea886843f62"
                }
                filterAuthorRole = PullRequests.GitHubRoleFilter.MEMBER
            }
        }
    }

    dependencies {
        snapshot(TestbenchCouplerWin64) {
            onDependencyFailure = FailureAction.FAIL_TO_START
        }

        snapshot(TestPrimodWin64)
        {
            onDependencyFailure = FailureAction.FAIL_TO_START
        }
    }
})
