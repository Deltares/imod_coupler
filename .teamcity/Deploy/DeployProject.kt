package Deploy

import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.Project

object DeployProject : Project({
    name = "Deploy"

    buildType(DeployAll)
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
})