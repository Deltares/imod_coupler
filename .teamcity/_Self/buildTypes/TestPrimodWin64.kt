package _Self.buildTypes

import IMODCollector.buildTypes.IMODCollector_X64development
import Templates.GitHubIntegrationTemplate
import _Self.vcsRoots.ImodCoupler
import _Self.vcsRoots.MetaSwapLookupTable
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.FailureAction
import jetbrains.buildServer.configs.kotlin.PublishMode
import jetbrains.buildServer.configs.kotlin.buildFeatures.XmlReport
import jetbrains.buildServer.configs.kotlin.buildFeatures.xmlReport
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object TestPrimodWin64 : BuildType({
    name = "Test Primod Win64"
    description = "Win64 Regression testbench for MODFLOW6/MetaSWAP coupler"

    templates(GitHubIntegrationTemplate)

    publishArtifacts = PublishMode.ALWAYS

    params {
        param("reverse.dep.iMOD6_Coupler_Coupler_Regression_Binaries.COUPLER_Version", "v2024.4.0")
        param("reverse.dep.iMOD6_Coupler_Coupler_Regression_Binaries.COUPLER_Platform", "windows")

        param("pixi-environment", "py312")
        param("conda_env_path", "%system.teamcity.build.checkoutDir%/imod_coupler_testbench_env")

        // Collector binaries parameters
        param("env.IMOD_COUPLER_EXEC_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/imodc.exe")
        param("env.METASWAP_DLL_DEP_DIR_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/metaswap")
        param("env.METASWAP_DLL_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/metaswap/MetaSWAP.dll")
        param("env.MODFLOW_DLL_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/modflow6/libmf6.dll")
        param("env.RIBASIM_DLL_DEP_DIR_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/ribasim/bin")
        param("env.RIBASIM_DLL_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/ribasim/bin/libribasim.dll")
        
        param("env.METASWAP_LOOKUP_TABLE", "%system.teamcity.build.checkoutDir%/lookup_table")
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
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
