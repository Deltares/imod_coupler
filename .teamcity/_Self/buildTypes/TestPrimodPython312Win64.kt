package _Self.buildTypes

import jetbrains.buildServer.configs.kotlin.*

object TestPrimodPython312Win64 : BuildType({
    templates(TestPrimodWin64)
    name = "Test Primod Python 3.12 Win64"
    description = "Win64 Regression testbench for MODFLOW6/MetaSWAP coupler"

    params {
        param("pixi-environment", "py312")
    }
})
