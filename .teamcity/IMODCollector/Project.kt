package IMODCollector

import IMODCollector.buildTypes.*
import jetbrains.buildServer.configs.kotlin.BuildType

import jetbrains.buildServer.configs.kotlin.Project
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object Project : Project({
    id("IMODCollector")
    name = "iMOD_Collector"
    description = "Collect iMOD6 coupled components + coupler into a single package"
    buildType(IMODCollector_X64development)
    buildType(Ribasim_binaries)
})

object Ribasim_binaries : BuildType({
    name = "Ribasim binaries"
    description = "Download Ribasim release binaries"

    artifactRules = """
        ribasim/* => ribasim.zip!
    """.trimIndent()

    params {
        select("RIBASIM_Platform", "",
            options = listOf("windows", "linux"))
        select("RIBASIM_Platform", "",
            options = listOf("v2025.11.0", "v2024.4.0", "v2024.3.0", "v2024.2.0"))
    }

    vcs {
    }

    steps {
        script {
            name = "Download Ribasim"
            scriptContent = """
                wget https://github.com/Deltares/Ribasim/releases/download/%RIBASIM_Version%/ribasim_/%RIBASIM_Platform%.zip -O ribasim.zip
                unzip  "ribasim.zip"
            """.trimIndent()
        }
    }

    requirements {
        equals("teamcity.agent.jvm.os.name", "Linux")
    }
})