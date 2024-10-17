package _Self.buildTypes

import IMODCollector.buildTypes.IMODCollector_X64Release53
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildFeatures.PullRequests
import jetbrains.buildServer.configs.kotlin.buildFeatures.commitStatusPublisher
import jetbrains.buildServer.configs.kotlin.buildFeatures.pullRequests
import jetbrains.buildServer.configs.kotlin.buildSteps.exec
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.finishBuildTrigger

object TestbenchCouplerWin64Release53 : BuildType({
    name = "Testbench Coupler Win64 Release 5.3"
    description = "Win64 Regression testbench for MODFLOW6/MetaSWAP coupler"
    paused = true

    artifactRules = """
        environment_vars.txt
        failed\** => failed_cases.zip
        logs\testbench.log
    """.trimIndent()

    params {
        param("env.IMODC__KERNELS__METASWAP__DLL", """%teamcity.build.checkoutDir%\imod_coupler\MetaSWAP.dll""")
        param("env.PATH", """%system.teamcity.build.workingDir%\imod_coupler;%env.PATH%""")
        param("copy_cases", "no")
        param("env.IMODC__KERNELS__METASWAP__DLL_DEPENDENCY", """%teamcity.build.checkoutDir%\imod_coupler""")
        param("env.IMODC__KERNELS__MODFLOW6__DLL", """%teamcity.build.checkoutDir%\imod_coupler\libmf6.dll""")
    }

    vcs {
        root(AbsoluteId("DSCTestbench"))
    }

    steps {
        script {
            name = "check environment"
            executionMode = BuildStep.ExecutionMode.RUN_ON_FAILURE
            scriptContent = "set > environment_vars.txt"
        }
        exec {
            name = "Run regression tests"
            executionMode = BuildStep.ExecutionMode.RUN_ON_FAILURE
            path = """%env.PYTHON_PATH%\python.exe"""
            arguments = """TestBench.py --username %svn_buildserver_username% --password %svn_buildserver_password% --compare --config configs\ModMf6Coupler\ModMf6Coupler_win64.xml --teamcity"""
            param("script.content", """
                Testbench.py --username %svn_buildserver_username% --password %svn_buildserver_password% --compare --config configs\ModMf6Coupler_win64.xml --filter "testcase=e150" --teamcity
                call set
            """.trimIndent())
        }
        exec {
            name = "Gather results of failed tests"
            executionMode = BuildStep.ExecutionMode.RUN_ON_FAILURE

            conditions {
                equals("copy_cases", "yes")
            }
            path = """%env.PYTHON_PATH%\python.exe"""
            arguments = """scripts_e150\failed_tests.py"""
        }
    }

    triggers {
        finishBuildTrigger {
            buildType = "${IMODCollector_X64Release53.id}"
            successfulOnly = true
        }
    }

    features {
        pullRequests {
            enabled = false
            vcsRootExtId = "iMOD6_Coupler_Imod6coupler"
            provider = github {
                authType = token {
                    token = "credentialsJSON:71420214-373c-4ccd-ba32-2ea886843f62"
                }
                filterAuthorRole = PullRequests.GitHubRoleFilter.MEMBER_OR_COLLABORATOR
            }
        }
        commitStatusPublisher {
            enabled = false
            vcsRootExtId = "iMOD6_Coupler_Imod6coupler"
            publisher = github {
                githubUrl = "https://api.github.com"
                authType = personalToken {
                    token = "credentialsJSON:71420214-373c-4ccd-ba32-2ea886843f62"
                }
            }
        }
    }

    dependencies {
        dependency(IMODCollector.buildTypes.IMODCollector_X64Release53) {
            snapshot {
            }

            artifacts {
                artifactRules = "imod_coupler.zip!*.*=>imod_coupler"
            }
        }
    }

    requirements {
        equals("teamcity.agent.jvm.os.name", "Windows 10")
    }
})
