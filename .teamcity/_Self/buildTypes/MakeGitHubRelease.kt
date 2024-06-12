package _Self.buildTypes

import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.vcs

object MakeGitHubRelease : BuildType({
    name = "Make GitHub Release"

    params {
        param("env.GITHUB_TOKEN", "%github_deltares-service-account_access_token%")
    }

    vcs {
        root(_Self.vcsRoots.ImodCoupler)
    }

    steps {
        script {
            name = "Push release to GitHub"
            scriptContent = """
                #!/usr/bin/env bash
                set -euxo pipefail
                . /usr/share/Modules/init/bash
                
                module load github
                # Get the name of the currently checked out tag
                tag_name=${'$'}(git describe --tags --exact-match 2>/dev/null)
                
                # Check if a tag is checked out
                if [ -n "${'$'}tag_name" ]; then
                    echo "Currently checked out tag: ${'$'}tag_name"
                
                    # Create a release using gh
                    gh release create "${'$'}tag_name" \
                        --generate-notes \
                        imod_coupler_windows.zip \
                
                    echo "Release created successfully."
                
                else
                    echo "No tag is currently checked out."
                fi
            """.trimIndent()
        }
    }

    triggers {
        vcs {
            branchFilter = "+:v20*"
        }
    }

    dependencies {
        dependency(IMODCollector.buildTypes.IMODCollector_X64development) {
            snapshot {
                onDependencyFailure = FailureAction.FAIL_TO_START
            }

            artifacts {
                artifactRules = "imod_coupler_windows.zip"
            }
        }
        snapshot(TestbenchCouplerWin64_2) {
            onDependencyFailure = FailureAction.FAIL_TO_START
        }
    }

    requirements {
        equals("teamcity.agent.jvm.os.name", "Linux")
    }

    cleanup {
        keepRule {
            id = "KEEP_RULE_10"
            keepAtLeast = allBuilds()
            applyToBuilds {
                withStatus = successful()
            }
            dataToKeep = everything()
            applyPerEachBranch = true
            preserveArtifactsDependencies = true
        }
        baseRule {
            option("disableCleanupPolicies", true)
        }
    }
})
