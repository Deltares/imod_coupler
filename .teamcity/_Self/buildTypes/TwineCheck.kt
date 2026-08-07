package _Self.buildTypes

import Templates.GitHubIntegrationTemplate
import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.buildFeatures.dockerRegistryConnections
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.buildSteps.ScriptBuildStep

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
                    pixi config set --local detached-environments "C:\pixi_envs"
                    pixi run check-package-primod
                """.trimIndent()
            formatStderrAsError = true
            dockerImage = "%DockerContainer%:%DockerVersion%"
            dockerImagePlatform = ScriptBuildStep.ImagePlatform.Windows
            dockerRunParameters = """--cpus=4 --memory=16g"""
            dockerPull = false
        }
    }

    features {
        dockerRegistryConnections {
            loginToRegistry = on {
                dockerRegistryId = "PROJECT_EXT_342"
            }
        }
    }
})