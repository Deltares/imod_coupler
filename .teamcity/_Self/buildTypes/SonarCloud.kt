package _Self.buildTypes

import Templates.GitHubIntegrationTemplate
import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.*

object SonarCloud : BuildType({
    name = "SonarCloud"
    description = "Runs SonarCloud static analysis"

    templates(GitHubIntegrationTemplate)

    vcs {
        root(ImodCoupler, ". => imod_coupler")
        cleanCheckout = true
    }

    steps {
        step {
            name = "SonarCloud analysis"
            id = "Sonar_analysis"
            type = "sonar-plugin"            
            param("sonarServer", "54d6c253-800e-4025-870b-cb760324147b")
            param("sonarProjectName", "imod_coupler")
            param("sonarProjectKey", "Deltares_imod_coupler")
            param("sonarProjectVersion", "%build.number%")

            param("teamcity.build.workingDir", "imod_coupler")
            param("sonarProjectSources", "imod_coupler,pre-processing/primod")
            param("sonarProjectTests", "tests")
            param("additionalParameters", """
                    -Dsonar.organization=deltares
                    -Dsonar.python.version=3.10
                    -Dsonar.token=%sonar_token%
                """.trimIndent())
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
