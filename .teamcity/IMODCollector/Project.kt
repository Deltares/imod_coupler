package IMODCollector

import IMODCollector.buildTypes.*
import IMODCollector.vcsRoots.*
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.Project

object Project : Project({
    id("IMODCollector")
    name = "iMOD_Collector"
    description = "Collect iMOD6 coupled components + coupler into a single package"

    vcsRoot(IMODCollector_ImodCouplerReleaseImod52)
    vcsRoot(IMODCollector_ImodCouplerReleaseImod53)

    buildType(IMODCollector_X64Release561)
    buildType(IMODCollector_X64development)
    buildType(IMODCollector_X64Release55)
    buildType(IMODCollector_X64Release54)
    buildType(IMODCollector_X64Release53)
    buildType(IMODCollector_X64Release52)
    buildType(IMODCollector_X64developmentLnx64)
    buildType(IMODCollector_X64lumbricus)
    buildType(IMODCollector_X64Release561test)
    buildType(IMODCollector_X64Release56)
})
