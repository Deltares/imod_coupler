package Primod.buildTypes

import jetbrains.buildServer.configs.kotlin.*

object Primod_TestPrimodPython310Win64 : BuildType({
    templates(Primod_TestPrimodWin64)
    name = "Test Primod Python 3.10 Win64"
    description = "Win64 Regression testbench for MODFLOW6/MetaSWAP coupler"

    params {
        param("pixi-environment", "py310")
    }
})
