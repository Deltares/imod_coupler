package _Self.buildTypes

import Templates.GitHubIntegrationTemplate
import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object TwineCheck : BuildType({
    name = "Twine"

    templates(GitHubIntegrationTemplate)

    vcs {
        root(ImodCoupler, ". => imod_coupler")
        cleanCheckout = true
    }

    steps {
        script {
            name = "Run twine check on primod"
            id = "Run_twine_check_on_primod"
            workingDir = "imod_coupler"
            scriptContent = """
                    pixi run check-package-primod
                """.trimIndent()
            formatStderrAsError = true
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})