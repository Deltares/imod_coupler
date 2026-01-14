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
        coupler/dist/ => imod_collector.zip!/
        modflow6/ => imod_collector.zip!/modflow6/
        metaswap/ => imod_collector.zip!/metaswap/
        ribasim/ => imod_collector.zip!/ribasim/
    """.trimIndent()

    params {
        param("conda_env_path", "%system.teamcity.build.checkoutDir%/imod_collector_env")
        param("reverse.dep.Modflow_Modflow6Release.MODFLOW6_Version", "6.6.3")
        param("reverse.dep.Modflow_Modflow6Release.MODFLOW6_Platform", "win64")
        param("reverse.dep.iMOD6_Coupler_Ribasim_binaries.RIBASIM_Version", "v2025.6.0")
        param("reverse.dep.iMOD6_Coupler_Ribasim_binaries.RIBASIM_Platform", "windows")
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
                pixi run -e dev pyinstaller --onefile imod_coupler/__main__.py --name imodc
            """.trimIndent()
        }
        script {
            name = "Get version from imod coupler"
            workingDir = "coupler"
            scriptContent = """call dist\imodc --version"""
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
        dependency(AbsoluteId("Modflow_Modflow6Release")) {
            snapshot {
                onDependencyFailure = FailureAction.FAIL_TO_START
            }
            artifacts {
                artifactRules = "+:MODFLOW6.zip!** => modflow6"
            }
        }

        dependency(AbsoluteId("iMOD6_Coupler_Ribasim_binaries")) {
            snapshot {
                onDependencyFailure = FailureAction.FAIL_TO_START
            }
            artifacts {
                artifactRules = "+:ribasim.zip!** => ribasim"
            }
        }

        artifacts(AbsoluteId("MSWMOD_MetaSWAP_MetaSWAPBuildWin64")) {
           cleanDestination = true
           buildRule = lastSuccessful("+::branches/update_4210")
           artifactRules = "MetaSWAP.zip!/x64/Release => metaswap"
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
