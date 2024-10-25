package IMODCollector.buildTypes

import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildFeatures.PullRequests
import jetbrains.buildServer.configs.kotlin.buildFeatures.commitStatusPublisher
import jetbrains.buildServer.configs.kotlin.buildFeatures.pullRequests
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.finishBuildTrigger

object IMODCollector_X64developmentLnx64 : BuildType({
    name = "x64_development_lnx64"
    description = "Collect all Release_x64 kernels in the iMOD6 suite"

    artifactRules = """
        coupler/dist/ => imod_collector.zip!/imod_coupler/
        modflow6/ => imod_collector.zip!/modflow6/
        metaswap/ => imod_collector.zip!/metaswap/
        ribasim/ribasim/ => imod_collector.zip!/ribasim/
    """.trimIndent()

    params {
        param("conda_env_path", "%system.teamcity.build.checkoutDir%/imod_collector_env")
    }

    vcs {
        root(_Self.vcsRoots.ImodCoupler, "+:. => ./coupler")
    }

    steps {
        script {
            name = "Create executable with pyinstaller"
            id = "RUNNER_301"
            workingDir = "./coupler"
            scriptContent = """
                #!/bin/bash
                source  /usr/share/Modules/init/profile.sh
                module load pixi
                rm -rf dist
                pixi run -e dev install-minimal
                pixi run -e dev pyinstaller --onefile imod_coupler/__main__.py --name imodc
            """.trimIndent()
        }
        script {
            name = "Get version from imod coupler"
            id = "RUNNER_1232"
            scriptContent = "./coupler/dist/imodc --version"
        }
    }

    triggers {
        finishBuildTrigger {
            id = "TRIGGER_59"
            enabled = false
            buildType = "iMOD6_Modflow6buildWin64"
            successfulOnly = true
        }
    }

    features {
        commitStatusPublisher {
            id = "BUILD_EXT_139"
            vcsRootExtId = "${ImodCoupler.id}"
            publisher = github {
                githubUrl = "https://api.github.com"
                authType = personalToken {
                    token = "credentialsJSON:71420214-373c-4ccd-ba32-2ea886843f62"
                }
            }
        }
        pullRequests {
            id = "BUILD_EXT_140"
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
        dependency(AbsoluteId("MetaSWAP_Modflow_Modflow6trunkLnx64")) {
            snapshot {
            }

            artifacts {
                id = "ARTIFACT_DEPENDENCY_553"
                cleanDestination = true
                artifactRules = "libmf6.so => modflow6/"
            }
        }
        artifacts(AbsoluteId("MSWMOD_MetaSWAP_MetaSWAPDevelopLnx64")) {
            id = "ARTIFACT_DEPENDENCY_560"
            buildRule = lastSuccessful()
            cleanDestination = true
            artifactRules = "libmsw.so => metaswap/"
        }
        artifacts(AbsoluteId("Ribasim_Linux_BuildRibasim")) {
            id = "ARTIFACT_DEPENDENCY_285"
            buildRule = lastSuccessful()
            artifactRules = "ribasim_linux.zip!** => ."
        }
    }

    requirements {
        equals("teamcity.agent.jvm.os.name", "Linux", "RQ_341")
    }
})
