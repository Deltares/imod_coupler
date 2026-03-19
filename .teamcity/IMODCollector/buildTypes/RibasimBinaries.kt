package IMODCollector.buildTypes

import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object Ribasim_binaries : BuildType({
    name = "Ribasim binaries"
    description = "Download Ribasim release binaries"

    artifactRules = """
        ribasim/** => ribasim.zip!
    """.trimIndent()

    params {
        select("RIBASIM_Platform", "",
            options = listOf("windows", "linux"))
        select("RIBASIM_Version", "v2026.1.0-rc2",
            options = listOf("v2025.6.0", "v2025.5.0", "v2025.4.0", "v2025.3.0", "v2026.1.0-rc2"))
    }

    vcs {
    }

    steps {
        script {
            name = "Download Ribasim"
            scriptContent = """
                wget https://github.com/Deltares/Ribasim/releases/download/%RIBASIM_Version%/ribasim_%RIBASIM_Platform%.zip -O ribasim.zip
                unzip  "ribasim.zip"
            """.trimIndent()
        }
    }

    requirements {
        equals("teamcity.agent.jvm.os.name", "Linux")
    }
})