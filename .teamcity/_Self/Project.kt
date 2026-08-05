package _Self

import Deploy.DeployProject
import Pixi.PixiProject
import Templates.GitHubIntegrationTemplate
import _Self.buildTypes.TestPrimodWin64
import _Self.buildTypes.SonarCloud
import _Self.buildTypes.*
import _Self.vcsRoots.*
import Weekly.WeeklyProject
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.Project
import jetbrains.buildServer.configs.kotlin.buildFeatures.PullRequests
import jetbrains.buildServer.configs.kotlin.buildFeatures.pullRequests
import jetbrains.buildServer.configs.kotlin.triggers.vcs
import jetbrains.buildServer.configs.kotlin.projectFeatures.dockerRegistry

object Project : Project({
    description = "Python scripts coupling components"

    params {
        param("DockerContainer", "containers.deltares.nl/hydrology_product_line_imod/windows-pixi")
        param("DockerVersion", "v0.69.0")
    }

    vcsRoot(MetaSwapLookupTable)
    vcsRoot(ImodCoupler)

    template(GitHubIntegrationTemplate)

    features {
        dockerRegistry {
            id = "PROJECT_EXT_342"
            name = "Hydrology"
            url = "https://containers.deltares.nl/"
            userName = "robot${'$'}hydrology_product_line_imod+coupler"
            password = "credentialsJSON:64b319c1-8310-4f16-bc84-bda637763af1"
        }
    }

    buildType(Lint)
    buildType(MyPy)
    buildType(TwineCheck)
    buildType(TestbenchCouplerWin64)
    buildType(TestPrimodWin64)
    buildType(SonarCloud)
    buildType(Main)

    subProject(IMODCollector.Project)
    subProject(PixiProject)
    subProject(WeeklyProject)
    subProject(DeployProject)
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

        snapshot(SonarCloud) {
            onDependencyFailure = FailureAction.ADD_PROBLEM
        }
    }
})
