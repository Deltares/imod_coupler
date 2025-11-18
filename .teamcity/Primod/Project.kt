package Primod

import Primod.buildTypes.*
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.Project

object Project : Project({
    id("Primod")
    name = "Primod"

    buildType(Primod_TestPrimodPython312Win64)

    template(Primod_TestPrimodWin64)
})
