package _Self.buildTypes

import Templates.GitHubIntegrationTemplate
import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.buildFeatures.dockerRegistryConnections
import jetbrains.buildServer.configs.kotlin.buildSteps.ScriptBuildStep
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object Lint : BuildType({
    name = "Lint"

    templates(GitHubIntegrationTemplate)

    vcs {
        root(ImodCoupler, ". => imod_coupler")
        cleanCheckout = true
    }

    steps {
        script {
            name = "Run ruff format check"
            id = "Run_ruff_format_check"
            workingDir = "imod_coupler"
            scriptContent = """
                    pixi run --environment dev --frozen format-check 
                """.trimIndent()
            formatStderrAsError = true
            dockerImage = "%DockerContainer%:%DockerVersion%"
            dockerImagePlatform = ScriptBuildStep.ImagePlatform.Windows
            dockerRunParameters = """--cpus=4 --memory=16g"""
            dockerPull = false
        }
        script {
            name = "Run ruff"
            id = "Run_ruff"
            workingDir = "imod_coupler"
            scriptContent = """
                    pixi run --environment dev --frozen ruff
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