package IMODCollector.buildTypes

import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildFeatures.PullRequests
import jetbrains.buildServer.configs.kotlin.buildFeatures.commitStatusPublisher
import jetbrains.buildServer.configs.kotlin.buildFeatures.pullRequests
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.finishBuildTrigger

object IMODCollector_X64Release561 : BuildType({
    name = "x64_Release5.6.1"
    description = "Collect all Release_x64 kernels in the iMOD6 suite"

    artifactRules = """
        dist\imodc.exe => imod_coupler.zip
        metaswap\fmpich2.dll => imod_coupler.zip
        modflow6\libmf6.dll => imod_coupler.zip
        metaswap\MetaSWAP.dll => imod_coupler.zip
        metaswap\mpich2mpi.dll => imod_coupler.zip
        metaswap\mpich2nemesis.dll => imod_coupler.zip
    """.trimIndent()

    params {
        param("conda_env_path", "%system.teamcity.build.checkoutDir%/imod_collector_env")
    }

    vcs {
        root(_Self.vcsRoots.ImodCouplerImod56, "+:. => ./coupler")

        cleanCheckout = true
    }

    steps {
        script {
            name = "Create imod_collector conda environment"
            scriptContent = """
                if exist "%conda_env_path%" rd /q /s "%conda_env_path%"
                conda env create --file coupler/environment-minimal.yml -p "%conda_env_path%"
            """.trimIndent()
        }
        script {
            name = "Install imod_coupler"
            workingDir = "coupler"
            scriptContent = """
                call conda activate %conda_env_path%
                call pip install -e .
            """.trimIndent()
        }
        script {
            name = "Create executable with pyinstaller"
            scriptContent = """
                call conda activate %conda_env_path%
                rmdir dist /s /q
                pyinstaller --onefile coupler/imod_coupler/__main__.py --name imodc
            """.trimIndent()
        }
        script {
            name = "Get version from imod coupler"
            scriptContent = """call dist\imodc.exe --version"""
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
                    token = "credentialsJSON:71420214-373c-4ccd-ba32-2ea886843f62"
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
        dependency(AbsoluteId("MSWMOD_MetaSWAP_MetaSWAPReleaseImod561")) {
            snapshot {
            }

            artifacts {
                cleanDestination = true
                artifactRules = "MetaSWAP.zip!/x64/Release => metaswap"
            }
        }
        dependency(AbsoluteId("MetaSWAP_Modflow_Modflow6Release642")) {
            snapshot {
            }

            artifacts {
                cleanDestination = true
                artifactRules = """
                    MODFLOW6.zip!/* => modflow6/
                """.trimIndent()
            }
        }
        artifacts(AbsoluteId("Ribasim_Windows_BuildRibasim")) {
            buildRule = lastSuccessful()
            artifactRules = "libribasim.zip!** => ribasim"
            enabled = false
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
