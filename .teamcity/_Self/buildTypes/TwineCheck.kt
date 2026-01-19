package _Self.buildTypes

import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.buildFeatures.commitStatusPublisher
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object TwineCheck : BuildType({
    name = "Twine"

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
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})