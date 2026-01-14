package _Self.buildTypes

import IMODCollector.buildTypes.IMODCollector_X64development
import _Self.vcsRoots.ImodCoupler
import _Self.vcsRoots.MetaSwapLookupTable
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildFeatures.XmlReport
import jetbrains.buildServer.configs.kotlin.buildFeatures.commitStatusPublisher
import jetbrains.buildServer.configs.kotlin.buildFeatures.xmlReport
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object TestPrimodWin64 : BuildType({
    name = "Test Primod Win64"
    description = "Win64 Regression testbench for MODFLOW6/MetaSWAP coupler"

    publishArtifacts = PublishMode.ALWAYS

    params {
        param("env.METASWAP_DLL_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/metaswap/MetaSWAP.dll")
        param("env.IMOD_COUPLER_EXEC_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/imod_coupler/imodc.exe")
        param("env.MODFLOW_DLL_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/modflow6/libmf6.dll")
        param("env.MODFLOW_DLL_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/modflow6/libmf6.dll")
        param("env.RIBASIM_DLL_DEP_DIR_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/ribasim/bin")
        param("env.RIBASIM_DLL_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/ribasim/bin/libribasim.dll")
        param("conda_env_path", "%system.teamcity.build.checkoutDir%/imod_coupler_testbench_env")
        param("env.METASWAP_DLL_DEP_DIR_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/metaswap")
        param("env.METASWAP_DLL_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/metaswap/MetaSWAP.dll")
        param("env.METASWAP_DLL_DEP_DIR_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/metaswap")
        param("env.IMOD_COUPLER_EXEC_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/imodc.exe")
        param("env.RIBASIM_DLL_DEP_DIR_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/ribasim/bin")
        param("env.METASWAP_LOOKUP_TABLE", "%system.teamcity.build.checkoutDir%/lookup_table")
        param("env.RIBASIM_DLL_REGRESSION", "%system.teamcity.build.checkoutDir%/imod_collector_regression/ribasim/bin/libribasim.dll")

        param("pixi-environment", "py312")
    }

    vcs {
        root(ImodCoupler, ". => imod_coupler")
        root(MetaSwapLookupTable, ". => lookup_table")

        cleanCheckout = true
        branchFilter = """
            +:*
            -:release_imod56
        """.trimIndent()
    }

    steps {
        script {
            name = "Run tests"
            id = "RUNNER_1503"
            workingDir = "imod_coupler"
            scriptContent = "pixi run --environment %pixi-environment% test-primod"
        }
    }

    features {
        commitStatusPublisher {
            id = "BUILD_EXT_142"
            vcsRootExtId = "${ImodCoupler.id}"
            publisher = github {
                githubUrl = "https://api.github.com"
                authType = personalToken {
                    token = "credentialsJSON:6b37af71-1f2f-4611-8856-db07965445c0"
                }
            }
        }
        xmlReport {
            id = "BUILD_EXT_145"
            reportType = XmlReport.XmlReportType.JUNIT
            rules = "imod_coupler/report.xml"
            verbose = true
        }
    }

    dependencies {
        dependency(IMODCollector_X64development) {
            snapshot {
                onDependencyFailure = FailureAction.FAIL_TO_START
            }

            artifacts {
                cleanDestination = true
                artifactRules = """
                    imod_collector.zip!** => imod_collector_devel
                """.trimIndent()
            }
            artifacts {
                buildRule = tag("regression")
                cleanDestination = true
                artifactRules = "imod_coupler_windows.zip!** => imod_collector_regression"
            }
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
