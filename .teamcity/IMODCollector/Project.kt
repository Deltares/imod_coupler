package IMODCollector

import IMODCollector.buildTypes.Coupler_Regression_Binaries
import IMODCollector.buildTypes.IMODCollector_X64development
import IMODCollector.buildTypes.Ribasim_binaries
import jetbrains.buildServer.configs.kotlin.Project

object Project : Project({
    id("IMODCollector")
    name = "iMOD_Collector"
    description = "Collect iMOD6 coupled components + coupler into a single package"

    buildType(IMODCollector_X64development)
    buildType(Ribasim_binaries)
    buildType(Coupler_Regression_Binaries)
})

