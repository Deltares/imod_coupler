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
            name = "Run ruff format"
            id = "Run_ruff_format"
            workingDir = "imod_coupler"
            scriptContent = """
                    pixi run --environment default --frozen format-check 
                """.trimIndent()
            formatStderrAsError = true
        }
        script {
            name = "Run ruff"
            id = "Run_ruff"
            workingDir = "imod_coupler"
            scriptContent = """
                    pixi run --environment default --frozen ruff
                """.trimIndent()
            formatStderrAsError = true
        }
    }
})