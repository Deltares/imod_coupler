package IMODCollector.buildTypes

import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object Coupler_Regression_Binaries : BuildType( {
    name = "Coupler regression binaries"
    description = "Download Coupler release binaries"

    params {
        select("COUPLER_Platform", "",
            options = listOf("windows"))
        select("COUPLER_Version", "",
            options = listOf("v2025.11.0", "v2024.3.0", "v2024.2.0", "v2024.01.2"))
    }

    artifactRules = """
        coupler/** => imod_coupler_release.zip!
    """.trimIndent()

    vcs {
        cleanCheckout = true
    }

    steps {
        script {
            name = "Download iMOD Coupler"
            scriptContent = """
                wget https://github.com/Deltares/imod_coupler/releases/download/%COUPLER_Version%/imod_coupler_%COUPLER_Platform%.zip -O coupler.zip
                unzip  "coupler.zip" -d coupler
            """.trimIndent()
        }
    }

    requirements {
        equals("teamcity.agent.jvm.os.name", "Linux")
    }
})