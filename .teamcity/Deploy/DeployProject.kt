package Deploy

import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.AbsoluteId
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.Project
import jetbrains.buildServer.configs.kotlin.buildFeatures.dockerSupport
import jetbrains.buildServer.configs.kotlin.buildSteps.ScriptBuildStep
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object DeployProject : Project({
    name = "Deploy"

    buildType(BuildPrimodPackage)

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
                SET TEMP=%system.teamcity.build.checkoutDir%\tmpdir
                SET TMPDIR=%system.teamcity.build.checkoutDir%\tmpdir
                SET TMP=%system.teamcity.build.checkoutDir%\tmpdir

                pixi run --environment dev --frozen build-primod
            """.trimIndent()
            formatStderrAsError = true
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
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
        snapshot(BuildPrimodPackage) {
        }
    }
})