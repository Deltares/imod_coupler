package _Self.buildTypes

import Templates.GitHubIntegrationTemplate
import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.*

object SonarCloud : BuildType({
    name = "SonarCloud"
    description = "Runs SonarCloud static analysis"

    templates(GitHubIntegrationTemplate)

    params {
        password("sonar_token", "%sonar_token%")
    }

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
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
