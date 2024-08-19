package IMODCollector.buildTypes

import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildFeatures.PullRequests
import jetbrains.buildServer.configs.kotlin.buildFeatures.commitStatusPublisher
import jetbrains.buildServer.configs.kotlin.buildFeatures.pullRequests
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.finishBuildTrigger

object IMODCollector_X64release : BuildType({
    name = "x64_release"
    description = "Collect all Release_x64 kernels in the iMOD6 suite"

    artifactRules = """
        coupler/dist/ => imod_coupler_windows.zip!/imod_coupler/
        modflow6/ => imod_coupler_windows.zip!/modflow6/
        metaswap/ => imod_coupler_windows.zip!/metaswap/
        ribasim/ => imod_coupler_windows.zip!/ribasim/
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
            name = "Create imod_collector conda environment"
            id = "Create_imod_collector_conda_environment"
            enabled = false
            scriptContent = """
                if exist "%conda_env_path%" rd /q /s "%conda_env_path%"
                conda env create --file coupler/environment-minimal.yml -p "%conda_env_path%"
            """.trimIndent()
        }
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
        script {
            name = "Download Release MODFLOW6"
            workingDir = "coupler"
            scriptContent = """
                mkdir modflow6
                curl -O https://water.usgs.gov/water-resources/software/MODFLOW-6/mf6.5.0_win64.zip
                unzip  -j "mf6.5.0_win64.zip" -d modflow6 mf6.5.0_win64/bin/libmf6.dll
            """.trimIndent()
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
            artifactRules = "ribasim_windows.zip!** => ribasim"
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
