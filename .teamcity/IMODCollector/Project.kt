package IMODCollector

import IMODCollector.buildTypes.*
import IMODCollector.vcsRoots.*
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.Project

object Project : Project({
    id("IMODCollector")
    name = "iMOD_Collector"
    description = "Collect iMOD6 coupled components + coupler into a single package"

    buildType(IMODCollector_x64_Release)
    buildType(IMODCollector_x64_development)
    buildType(IMODCollector_x64_developmentLnx64)
})
