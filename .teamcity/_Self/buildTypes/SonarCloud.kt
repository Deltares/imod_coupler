package _Self.buildTypes

import Templates.GitHubIntegrationTemplate
import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object SonarCloud : BuildType({
    name = "SonarCloud"
    description = "Runs SonarCloud static analysis"

    templates(GitHubIntegrationTemplate)

    params {
        param("sonar_scanner_version", "8.0.1.6346")
    }

    vcs {
        root(ImodCoupler, ". => imod_coupler")
        cleanCheckout = true
    }

    steps {
        script {
            name = "SonarCloud analysis"
            id = "Sonar_analysis"
            workingDir = "imod_coupler"
            scriptContent = """
                curl -sSL "https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-%sonar_scanner_version%-windows-x64.zip" -o sonar-cli.zip
                tar -xf sonar-cli.zip
                sonar-scanner-%sonar_scanner_version%-windows-x64\bin\sonar-scanner.bat "-Dsonar.token=%sonar_token%"
            """.trimIndent()
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
