package IMODCollector.buildTypes

import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildFeatures.PullRequests
import jetbrains.buildServer.configs.kotlin.buildFeatures.pullRequests
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.finishBuildTrigger

object IMODCollector_X64lumbricus : BuildType({
    name = "x64_lumbricus"
    description = "Collect all Release_x64 kernels in the iMOD6 suite"

    artifactRules = """
        dist/ => imod_collector.zip!/imod_coupler/
        modflow6/ => imod_collector.zip!/modflow6/
        metaswap/ => imod_collector.zip!/metaswap/
        dflowfm/ => imod_collector.zip!/dflowfm/
    """.trimIndent()

    params {
        param("conda_env_path", "%system.teamcity.build.checkoutDir%/imod_collector_env")
    }

    vcs {
        root(_Self.vcsRoots.ImodCoupler, "+:. => ./coupler")

        branchFilter = """
            +:lumbricus
            +:lumbricus_test2D_dfm2msw
        """.trimIndent()
    }

    steps {
        script {
            name = "Create imod_collector conda environment"
            scriptContent = """
                tree
                if exist "%conda_env_path%" rd /q /s "%conda_env_path%"
                conda env create --file coupler\environment-minimal.yml -p "%conda_env_path%"
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
            name = "Install pyinstaller"
            scriptContent = """
                call conda activate %conda_env_path%
                rmdir dist /s /q
                pyinstaller coupler/imod_coupler/__main__.py --name imodc
            """.trimIndent()
        }
        script {
            name = "Create executable with pyinstaller"
            scriptContent = """
                call conda activate %conda_env_path%
                pyinstaller --onefile coupler/imod_coupler/__main__.py --name imodc
            """.trimIndent()
        }
        script {
            name = "Get version from imod coupler"
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
        dependency(AbsoluteId("iMOD6_Modflow6buildWin64")) {
            snapshot {
            }

            artifacts {
                cleanDestination = true
                artifactRules = "srcbmi/libmf6.dll => modflow6/"
            }
        }
        artifacts(AbsoluteId("Dimr_DimrCollector")) {
            buildRule = tag("DIMRset_2.22.04")
            cleanDestination = true
            artifactRules = """
                dimrset_x64_171.zip!/x64/dflowfm/bin => dflowfm
                dimrset_x64_171.zip!/x64/share/bin => dflowfm
            """.trimIndent()
        }
        artifacts(AbsoluteId("MSWMOD_MetaSWAP_MetaSWAPBuildWin64trunk")) {
            buildRule = tag("lumbricus")
            artifactRules = "MetaSWAP.zip!/x64/Release => metaswap"
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
