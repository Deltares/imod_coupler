package _Self.buildTypes

import IMODCollector.buildTypes.IMODCollector_X64Release54
import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildSteps.exec
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.finishBuildTrigger
import jetbrains.buildServer.configs.kotlin.triggers.vcs

object TestbenchCouplerWin64Release54 : BuildType({
    name = "Testbench Coupler Win64 Release 5.4"
    description = "Win64 Regression testbench for MODFLOW6/MetaSWAP coupler"

    artifactRules = """
        environment_vars.txt
        failed\** => failed_cases.zip
        logs\testbench.log
        failed\list.txt => failed_cases.zip
        data\cases\e150_metaswap\f01_basic_tests => test_data.zip
    """.trimIndent()

    params {
        param("env.IMODC__KERNELS__METASWAP__DLL", """%system.teamcity.build.checkoutDir%\imod_coupler\MetaSWAP.dll""")
        param("env.PATH", """%system.teamcity.build.checkoutDir%\imod_coupler;%system.teamcity.build.checkoutDir%\c00_common\scripts;%env.PATH%""")
        param("copy_cases", "no")
        param("env.IMODC__KERNELS__METASWAP__DLL_DEPENDENCY", """%system.teamcity.build.checkoutDir%\imod_coupler""")
        param("env.IMODC__KERNELS__MODFLOW6__DLL", """%system.teamcity.build.checkoutDir%\imod_coupler\libmf6.dll""")
    }

    vcs {
        root(AbsoluteId("DSCTestbench"))
        root(AbsoluteId("ReposDSCTestbenchRoot"), """+:trunk\cases\e150_metaswap\f00_common\c00_common\scripts => scripts_e150""", """+:trunk\cases\e150_metaswap\f00_common\c00_common\LHM2016_v01vrz => data\cases\e150_metaswap\f00_common\c00_common\LHM2016_v01vrz""")

        cleanCheckout = true
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
            arguments = """TestBench.py --username %svn_buildserver_username% --password %svn_buildserver_password% --compare --config configs\ModMf6Coupler\ModMf6Coupler_win64_iMOD-5.4.xml --teamcity"""
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
            arguments = """.\scripts_e150\failed_tests.py"""
        }
        script {
            name = "Disconnect NHI network location"
            enabled = false
            executionMode = BuildStep.ExecutionMode.ALWAYS
            scriptContent = "net use Q: /DELETE"
        }
    }

    triggers {
        finishBuildTrigger {
            buildType = "${IMODCollector_X64Release54.id}"
            successfulOnly = true
        }
        vcs {
            enabled = false
            triggerRules = "+:root=${ImodCoupler.id}:**"

        }
    }

    dependencies {
        dependency(IMODCollector.buildTypes.IMODCollector_X64Release54) {
            snapshot {
            }

            artifacts {
                artifactRules = """
                    imod_coupler.zip!*.*=>imod_coupler
                """.trimIndent()
            }
        }
    }

    requirements {
        equals("teamcity.agent.jvm.os.name", "Windows 10")
        doesNotEqual("system.agent.name", "c-teamcity0358")
    }
})
