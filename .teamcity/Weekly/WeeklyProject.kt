package Weekly

import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildFeatures.notifications
import jetbrains.buildServer.configs.kotlin.triggers.ScheduleTrigger
import jetbrains.buildServer.configs.kotlin.triggers.schedule
import jetbrains.buildServer.configs.kotlin.buildFeatures.XmlReport
import jetbrains.buildServer.configs.kotlin.buildFeatures.xmlReport
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.Dependencies.ReuseBuilds
import _Self.vcsRoots.ImodCoupler

object WeeklyProject : Project({
    name = "Weekly"

    buildType(AcceptanceTests)
    buildType(WeeklyJobs)
})

object AcceptanceTests : BuildType({
    name = "AcceptanceTests"

    params {
        param("env.PIXI_FROZEN", "true")
        param("conda_env_path", "%system.teamcity.build.checkoutDir%/imod_coupler_testbench_env")

        // Collector binaries parameters
        param("env.IMOD_COUPLER_EXEC_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/imodc.exe")
        param("env.METASWAP_DLL_DEP_DIR_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/metaswap")
        param("env.METASWAP_DLL_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/metaswap/MetaSWAP.dll")
        param("env.MODFLOW_DLL_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/modflow6/libmf6.dll")
        param("env.RIBASIM_DLL_DEP_DIR_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/ribasim/bin")
        param("env.RIBASIM_DLL_DEVEL", "%system.teamcity.build.checkoutDir%/imod_collector_devel/ribasim/bin/libribasim.dll")
    }

    vcs {
        root(ImodCoupler, ". => imod_coupler")

        cleanCheckout = true
        branchFilter = """
            +:*
            -:release_imod56
        """.trimIndent()
    }

    steps {
        script {
            name = "Set up pixi"
            workingDir = "imod_coupler"
            scriptContent = """
                pixi --version
                pixi install -e user-acceptance
                pixi list -e user-acceptance
            """.trimIndent()
        }
        script {
            name = "Get test data"
            workingDir = "imod_coupler"
            scriptContent = """
                pixi run -e user-acceptance fetch_lhm
            """.trimIndent()
        }
        script {
            name = "Run tests"
            workingDir = "imod_coupler"
            scriptContent = """
                pixi run -e user-acceptance user_acceptance_test
            """.trimIndent()
        }
    }

    features {
        xmlReport {
            reportType = XmlReport.XmlReportType.JUNIT
            rules = "user_acceptance_report.xml"
            verbose = true
        }
    }

    failureConditions {
        executionTimeoutMin = 120
    }

    dependencies {
        dependency(IMODCollector.buildTypes.IMODCollector_X64development) {
            snapshot {
                onDependencyFailure = FailureAction.FAIL_TO_START
                reuseBuilds = ReuseBuilds.YES
            }

            artifacts {
                cleanDestination = true
                artifactRules = """
                    imod_collector.zip!** => imod_collector_devel
                """.trimIndent()
            }

            branchFilter = "+:refs/heads/main"
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})

object  WeeklyJobs : BuildType({
    name = "WeeklyJobs"

    allowExternalStatus = true
    type = Type.COMPOSITE

    vcs {
        root(ImodCoupler, ". => imod_coupler")

        cleanCheckout = true
        branchFilter = """
            +:*
            -:release_imod56
        """.trimIndent()
        showDependenciesChanges = true
    }


    triggers {
        schedule {
            schedulingPolicy = weekly {
                dayOfWeek = ScheduleTrigger.DAY.Sunday
                hour = 16
                minute = 0
            }
            branchFilter = "+:<default>"
            triggerBuild = always()
            withPendingChangesOnly = false
        }
    }

    failureConditions {
        errorMessage = true
    }

    features {
        notifications {
            notifierSettings = emailNotifier {
                email = """
                joeri.vanengelen@deltares.nl
                robert.leander@deltares.nl
                sunny.titus@deltares.nl
            """.trimIndent()
            }
            buildFailedToStart = true
            buildFailed = true
        }
    }

    dependencies {
        snapshot(AcceptanceTests) {
            onDependencyFailure = FailureAction.FAIL_TO_START
        }
    }
})