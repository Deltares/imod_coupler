package _Self.buildTypes

import IMODCollector.buildTypes.IMODCollector_X64Release55
import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildFeatures.XmlReport
import jetbrains.buildServer.configs.kotlin.buildFeatures.commitStatusPublisher
import jetbrains.buildServer.configs.kotlin.buildFeatures.xmlReport
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.finishBuildTrigger
import jetbrains.buildServer.configs.kotlin.triggers.retryBuild
import jetbrains.buildServer.configs.kotlin.triggers.vcs

object TestbenchCouplerWin64Release56 : BuildType({
    name = "Testbench Coupler Win64 Release 5.6"
    description = "Win64 Regression testbench for MODFLOW6/MetaSWAP coupler"

    artifactRules = """
        imod_coupler\tests\temp => test_output.zip
        imod_coupler\imod_coupler => imod_coupler\imod_coupler_code.zip
        conda_list.txt
    """.trimIndent()

    params {
        param("conda_env_path", "%system.teamcity.build.checkoutDir%/imod_coupler_testbench_env")
        param("env.METASWAP_DLL_DEP_DIR_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression")
        param("env.METASWAP_DLL_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/MetaSWAP.dll")
        param("env.METASWAP_DLL_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/MetaSWAP.dll")
        param("env.METASWAP_DLL_DEP_DIR_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel")
        param("env.IMOD_COUPLER_EXEC_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/imodc.exe")
        param("env.IMOD_COUPLER_EXEC_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/imodc.exe")
        param("env.MODFLOW_DLL_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/libmf6.dll")
        param("env.MODFLOW_DLL_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/libmf6.dll")
        param("env.METASWAP_LOOKUP_TABLE", "%system.teamcity.build.checkoutDir%/lookup_table")
    }

    vcs {
        root(_Self.vcsRoots.MetaSwapLookupTable, ". => lookup_table")
        root(_Self.vcsRoots.ImodCouplerImod56, ". => imod_coupler")
    }

    steps {
        script {
            name = "Set up virtual environment"
            workingDir = "imod_coupler"
            scriptContent = """
                if exist "%conda_env_path%" rd /q /s "%conda_env_path%"
                call conda env create --file environment.yml -p "%conda_env_path%"
            """.trimIndent()
        }
        script {
            name = "Install iMOD Coupler"
            workingDir = "imod_coupler"
            scriptContent = """
                call conda activate "%conda_env_path%"
                call pip install -e "."
            """.trimIndent()
        }
        script {
            name = "Run tests"
            workingDir = "imod_coupler"
            scriptContent = """
                call conda activate "%conda_env_path%"
                conda list > ..\conda_list.txt
                call pytest tests -n=auto --basetemp=tests/temp --junitxml="report.xml"
            """.trimIndent()
        }
    }

    triggers {
        finishBuildTrigger {
            buildType = "${IMODCollector_X64Release55.id}"
            successfulOnly = true
        }
        vcs {
            triggerRules = "+:root=${ImodCoupler.id}:**"

        }
        retryBuild {
            attempts = 1
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
        xmlReport {
            reportType = XmlReport.XmlReportType.JUNIT
            rules = "imod_coupler/report.xml"
            verbose = true
        }
    }

    dependencies {
        dependency(IMODCollector.buildTypes.IMODCollector_X64Release56) {
            snapshot {
                onDependencyFailure = FailureAction.FAIL_TO_START
            }

            artifacts {
                cleanDestination = true
                artifactRules = """
                    imod_coupler.zip!** =>imod_collector_devel
                """.trimIndent()
            }
            artifacts {
                cleanDestination = true
                artifactRules = "imod_coupler.zip!** =>imod_collector_regression"
            }
        }
    }

    requirements {
        equals("teamcity.agent.jvm.os.name", "Windows 10")
        doesNotEqual("system.agent.name", "c-teamcity0358")
    }
})
