package IMODCollector.buildTypes

import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildFeatures.PullRequests
import jetbrains.buildServer.configs.kotlin.buildFeatures.commitStatusPublisher
import jetbrains.buildServer.configs.kotlin.buildFeatures.pullRequests
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.finishBuildTrigger

object IMODCollector_X64development : BuildType({
    name = "x64_development"
    description = "Collect all Release_x64 kernels in the iMOD6 suite"

    artifactRules = """
        coupler/dist/ => imod_collector.zip!/
        modflow6/ => imod_collector.zip!/modflow6/
        metaswap/ => imod_collector.zip!/metaswap/
        ribasim/  => imod_collector.zip!/ribasim/
    """.trimIndent()

    params {
        param("conda_env_path", "%system.teamcity.build.checkoutDir%/imod_collector_env")
    }

    vcs {
        root(_Self.vcsRoots.ImodCoupler, "+:. => ./coupler")

        cleanCheckout = true
    }

    steps {
        script {
            name = "Install iMOD Coupler"
            enabled = false
            workingDir = "coupler"
            scriptContent = """
                call conda activate %conda_env_path%
                call pip install -e .
            """.trimIndent()
        }
        script {
            name = "Create executable with pyinstaller"
            workingDir = "coupler"
            scriptContent = """
                rmdir dist /s /q
                pixi run -e dev install-minimal
                pixi run -e dev pyinstaller --onefile imod_coupler/__main__.py --name imodc
            """.trimIndent()
        }
        script {
            name = "Get version from imod coupler"
            workingDir = "coupler"
            scriptContent = """call dist\imodc --version"""
        }
    }

    triggers {
        finishBuildTrigger {
            buildType = "MSWMOD_MetaSWAP_MetaSWAPBuildWin64trunk"
            successfulOnly = true
        }
        finishBuildTrigger {
            buildType = "iMOD6_Modflow6buildWin64"
            successfulOnly = true
        }
    }

    features {
        commitStatusPublisher {
            vcsRootExtId = "${ImodCoupler.id}"
            publisher = github {
                githubUrl = "https://api.github.com"
                authType = personalToken {
                    token = "credentialsJSON:6b37af71-1f2f-4611-8856-db07965445c0"
                }
            }
        }
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
        dependency(AbsoluteId("MSWMOD_MetaSWAP_MetaSWAPBuildWin64trunk")) {
            snapshot {
            }

            artifacts {
                cleanDestination = true
                artifactRules = "MetaSWAP.zip!/x64/Release => metaswap"
            }
        }
        dependency(AbsoluteId("iMOD6_Modflow6buildWin64")) {
            snapshot {
            }

            artifacts {
                cleanDestination = true
                artifactRules = "srcbmi/libmf6.dll => modflow6/"
            }
        }
        artifacts(AbsoluteId("Ribasim_Windows_BuildRibasim")) {
            buildRule = lastSuccessful()
            artifactRules = "ribasim_windows.zip!** => ."
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
