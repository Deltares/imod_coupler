package Deploy

import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.AbsoluteId
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.FailureAction
import jetbrains.buildServer.configs.kotlin.Project
import jetbrains.buildServer.configs.kotlin.buildFeatures.dockerSupport
import jetbrains.buildServer.configs.kotlin.buildSteps.ScriptBuildStep
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object DeployProject : Project({
    name = "Deploy"

    buildType(BuildPrimodPackage)
    buildType(DeployPrimodPackage)

    buildType(DeployAll)
})

object BuildPrimodPackage : BuildType({
    name = "Build Primod package"

    artifactRules = """imod_coupler\pre-processing\dist => dist.zip"""

    vcs {
        root(ImodCoupler, ". => imod_coupler")

        cleanCheckout = true
        branchFilter = """
            +:*
            -:<default>
            -:refs/heads/gh-pages
        """.trimIndent()
        showDependenciesChanges = true
    }

    steps {
        script {
            name = "Create Primod package"
            id = "Create_Primod_package"
            workingDir = "imod_coupler"
            scriptContent = """
                pixi run --environment dev --frozen build-primod
            """.trimIndent()
            formatStderrAsError = true
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }

})

object DeployPrimodPackage : BuildType({
     name = "Deploy Primod Package"

    params {
        param("env.TWINE_USERNAME", "__token__")
        param("env.TWINE_NON_INTERACTIVE", "true")
        password("env.TWINE_PASSWORD", "credentialsJSON:2cea585c-e4f8-4a45-9941-9189daf09ecc")
    }

    vcs {
        root(ImodCoupler, ". => imod_coupler")

        cleanCheckout = true
        branchFilter = """
            +:*
            -:<default>
            -:refs/heads/gh-pages
        """.trimIndent()
        showDependenciesChanges = true
    }

    steps {
        script {
            name = "Deploy Primod to PyPi"
            id = "Deploy_Primod_to_PyPi"
            workingDir = "imod_coupler"
            scriptContent = """
                pixi run --environment dev --frozen publish-primod
            """.trimIndent()
        }
    }

    dependencies {
        dependency(BuildPrimodPackage) {
            snapshot {
                onDependencyFailure = FailureAction.FAIL_TO_START
            }

            artifacts {
                artifactRules = """+:dist.zip!** => imod_coupler\pre-processing\dist"""
            }
        }
    }
})

object DeployAll : BuildType({
    name = "Deploy All"

    type = Type.COMPOSITE
    maxRunningBuilds = 1

    vcs {
        root(ImodCoupler)

        cleanCheckout = true
        branchFilter = """
            +:*
            -:<default>
            -:refs/heads/gh-pages
        """.trimIndent()
        showDependenciesChanges = true
    }

    dependencies {
        snapshot(DeployPrimodPackage) {
        }
    }
})