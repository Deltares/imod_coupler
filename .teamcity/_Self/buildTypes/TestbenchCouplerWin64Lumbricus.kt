package _Self.buildTypes

import IMODCollector.buildTypes.IMODCollector_X64development
import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildFeatures.XmlReport
import jetbrains.buildServer.configs.kotlin.buildFeatures.xmlReport
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.finishBuildTrigger
import jetbrains.buildServer.configs.kotlin.triggers.vcs

object TestbenchCouplerWin64Lumbricus : BuildType({
    name = "Testbench Coupler Win64 Lumbricus"
    description = "Win64 testbench for MODFLOW6/MetaSWAP/DflowFM coupler aka Lumbricus"
    paused = true

    artifactRules = """imod_coupler\tests\temp => test_output.zip"""

    params {
        param("npar", "1")
        param("env.DFLOWFM_DLL_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/dflowfm/dflowfm.dll")
        param("env.METASWAP_DLL_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/metaswap/MetaSWAP.dll")
        param("env.IMOD_COUPLER_EXEC_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/imod_coupler/imodc.exe")
        param("env.MODFLOW_DLL_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/modflow6/libmf6.dll")
        param("env.MODFLOW_DLL_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/modflow6/libmf6.dll")
        param("conda_env_path", "%system.teamcity.build.checkoutDir%/imod_coupler_testbench_env")
        param("env.METASWAP_DLL_DEP_DIR_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/metaswap")
        param("env.DFLOWFM_DLL_DEP_DIR_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/dflowfm")
        param("env.DFLOWFM_DLL_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/dflowfm/dflowfm.dll")
        param("env.METASWAP_DLL_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/metaswap/MetaSWAP.dll")
        param("env.METASWAP_DLL_DEP_DIR_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/metaswap")
        param("env.IMOD_COUPLER_EXEC_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/imod_coupler/imodc.exe")
        param("env.DFLOWFM_DLL_DEP_DIR_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/dflowfm")
        param("env.METASWAP_LOOKUP_TABLE", "%system.teamcity.build.checkoutDir%/lookup_table")
    }

    vcs {
        root(_Self.vcsRoots.ImodCoupler, ". => imod_coupler")
        root(_Self.vcsRoots.MetaSwapLookupTable, ". => lookup_table")

        branchFilter = "+:lumbricus"
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
                call pytest tests -s -n=%npar% --basetemp=tests/temp --junitxml="report.xml"
            """.trimIndent()
        }
    }

    triggers {
        finishBuildTrigger {
            buildType = "${IMODCollector_X64development.id}"
            successfulOnly = true
        }
        vcs {
            triggerRules = "+:root=${ImodCoupler.id}:**"

        }
    }

    features {
        xmlReport {
            reportType = XmlReport.XmlReportType.JUNIT
            rules = "imod_coupler/report.xml"
            verbose = true
        }
    }

    dependencies {
        dependency(IMODCollector.buildTypes.IMODCollector_X64lumbricus) {
            snapshot {
                onDependencyFailure = FailureAction.FAIL_TO_START
            }

            artifacts {
                cleanDestination = true
                artifactRules = """
                    imod_collector.zip!** =>imod_collector_devel
                """.trimIndent()
            }
        }
        artifacts(IMODCollector.buildTypes.IMODCollector_X64development) {
            buildRule = tag("regression")
            cleanDestination = true
            artifactRules = "imod_collector.zip!** =>imod_collector_regression"
        }
    }

    requirements {
        equals("teamcity.agent.jvm.os.name", "Windows 10")
        doesNotEqual("system.agent.name", "c-teamcity0358")
    }
})
