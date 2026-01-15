package _Self.buildTypes

import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object Lint : BuildType({
    name = "Lint"

    vcs {
        root(_Self.vcsRoots.ImodCoupler, ". => imod_coupler")
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
        }
        script {
            name = "Run ruff"
            id = "Run_ruff"
            workingDir = "imod_coupler"
            scriptContent = """
                    pixi run --environment dev --frozen ruff
                """.trimIndent()
            formatStderrAsError = true
        }
    }
})