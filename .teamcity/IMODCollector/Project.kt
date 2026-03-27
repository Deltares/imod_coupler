package IMODCollector

import IMODCollector.buildTypes.Coupler_Regression_Binaries
import IMODCollector.buildTypes.IMODCollector_X64development
import jetbrains.buildServer.configs.kotlin.Project

object Project : Project({
    id("IMODCollector")
    name = "iMOD_Collector"
    description = "Collect iMOD6 coupled components + coupler into a single package"

    buildType(IMODCollector_X64development)
    buildType(Coupler_Regression_Binaries)
})

