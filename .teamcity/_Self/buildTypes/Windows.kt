package _Self.buildTypes

import jetbrains.buildServer.configs.kotlin.*

object Windows : Template({
    name = "Windows"
    description = "Template for agent that uses Windows OS"

    requirements {
        contains("teamcity.agent.jvm.os.name", "Windows", "RQ_448")
    }
})
