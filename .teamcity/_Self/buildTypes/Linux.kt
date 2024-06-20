package _Self.buildTypes

import jetbrains.buildServer.configs.kotlin.*

object Linux : Template({
    name = "Linux"
    description = "Template for agent that uses Linux OS"

    requirements {
        contains("teamcity.agent.jvm.os.name", "Linux", "RQ_447")
    }
})
