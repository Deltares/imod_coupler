package _Self.buildTypes

import Templates.GitHubIntegrationTemplate
import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.buildFeatures.XmlReport
import jetbrains.buildServer.configs.kotlin.buildFeatures.xmlReport
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.failureConditions.BuildFailureOnMetric
import jetbrains.buildServer.configs.kotlin.failureConditions.failOnMetricChange

object MyPy : BuildType({
    name = "MyPy"

    templates(GitHubIntegrationTemplate)

    vcs {
        root(ImodCoupler, ". => imod_coupler")
        cleanCheckout = true
    }

    steps {
        script {
            name = "Run mypy on imodc"
            id = "Run_mypy_on_imodc"
            workingDir = "imod_coupler"
            scriptContent = """
                    pixi run --environment dev --frozen mypy-imodc-report
                    pixi run --environment dev --frozen mypy-imodc
                """.trimIndent()
            formatStderrAsError = true
        }
        script {
            name = "Run mypy on primod"
            id = "Run_mypy_on_primod"
            workingDir = "imod_coupler"
            scriptContent = """
                    pixi run --environment dev --frozen mypy-primod-report
                    pixi run --environment dev --frozen mypy-primod
                """.trimIndent()
            formatStderrAsError = true
        }
    }

    failureConditions {
        nonZeroExitCode = false
        testFailure = false
        failOnMetricChange {
            metric = BuildFailureOnMetric.MetricType.TEST_FAILED_COUNT
            threshold = 0
            units = BuildFailureOnMetric.MetricUnit.DEFAULT_UNIT
            comparison = BuildFailureOnMetric.MetricComparison.MORE
            compareTo = value()
        }
    }

    features {
        xmlReport {
            reportType = XmlReport.XmlReportType.JUNIT
            rules = "imod_coupler/*.xml"
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})