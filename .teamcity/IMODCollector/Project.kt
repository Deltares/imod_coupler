package IMODCollector

import IMODCollector.buildTypes.*
import IMODCollector.vcsRoots.*
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.Project

object Project : Project({
    id("IMODCollector")
    name = "iMOD_Collector"
    description = "Collect iMOD6 coupled components + coupler into a single package"
    buildType(IMODCollector_X64development)
})
