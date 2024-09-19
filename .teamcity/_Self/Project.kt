package _Self

import _Self.buildTypes.*
import _Self.vcsRoots.*
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.Project

object Project : Project({
    description = "Python scripts coupling components"

    vcsRoot(MetaSwapLookupTable)
    vcsRoot(ImodCoupler)

    buildType(TestbenchCouplerWin64Develop)

    subProject(Primod.Project)
    subProject(IMODCollector.Project)
})
