package IMODCollector.buildTypes

import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildFeatures.PullRequests
import jetbrains.buildServer.configs.kotlin.buildFeatures.commitStatusPublisher
import jetbrains.buildServer.configs.kotlin.buildFeatures.pullRequests
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object IMODCollector_X64development : BuildType({
    name = "x64_development"
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
        script {
            name = "Download Release MODFLOW 6.5.0"
            scriptContent = """
                mkdir modflow6
                curl -O https://water.usgs.gov/water-resources/software/MODFLOW-6/mf6.5.0_win64.zip
                unzip  -j "mf6.5.0_win64.zip" -d modflow6 mf6.5.0_win64/bin/libmf6.dll
            """.trimIndent()
        }
        script {
            name = "Download Release Ribasim v2024.11.0"
            scriptContent = """
                mkdir modflow6
                curl -L -o ribasim_windows.zip https://github.com/Deltares/Ribasim/releases/download/v2024.11.0/ribasim_windows.zip
                unzip  "ribasim_windows.zip"
            """.trimIndent()
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
        artifacts(AbsoluteId("MSWMOD_MetaSWAP_MetaSWAPBuildWin64trunk")) {
           cleanDestination = true
           buildRule = tag("release_2410")
           artifactRules = "MetaSWAP.zip!/x64/Release => metaswap"
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
