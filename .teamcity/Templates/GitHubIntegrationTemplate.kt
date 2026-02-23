package Templates

import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.Template
import jetbrains.buildServer.configs.kotlin.buildFeatures.commitStatusPublisher

object GitHubIntegrationTemplate : Template({
    name = "GitHubIntegrationTemplate"

    features {
        commitStatusPublisher {
            vcsRootExtId = "${ImodCoupler.id}"
            publisher = github {
                githubUrl = "https://api.github.com"
                authType = personalToken {
                    token = "credentialsJSON:6b37af71-1f2f-4611-8856-db07965445c0"
                }
            }
        }
    }
})