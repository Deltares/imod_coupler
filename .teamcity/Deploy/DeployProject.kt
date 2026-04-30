package Deploy

import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.AbsoluteId
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.FailureAction
import jetbrains.buildServer.configs.kotlin.Project
import jetbrains.buildServer.configs.kotlin.buildSteps.powerShell

object DeployProject : Project({
    name = "Deploy"

    buildType(CreateGitHubRelease)

    buildType(DeployAll)
})

object CreateGitHubRelease : BuildType({
    name = "Create GitHub release"

    type = Type.DEPLOYMENT
    maxRunningBuilds = 1

    params {
        param("env.GH_TOKEN", "%github_deltares-service-account_access_token%")
    }

    vcs {
        root(ImodCoupler)

        cleanCheckout = true
        branchFilter = """
            +:*
            -:<default>
            -:refs/heads/gh-pages
        """.trimIndent()
        showDependenciesChanges = true
    }

    steps {
        powerShell {
            name = "Create GitHub release"
            id = "Create_GitHub_release"
            formatStderrAsError = true
            scriptMode = script {
                content = """
                    ${'$'}tag = git describe --tags --abbrev=0 --exact-match
                    
                    echo "Creating GitHub release for: ${'$'}tag"
                    
                    ${'$'}notesFile = [System.IO.Path]::GetTempFileName()
                    pixi run --environment default --frozen python scripts/extract_changelog_notes.py ${'$'}tag | Set-Content -Path ${'$'}notesFile -Encoding UTF8
                    if (${'$'}LASTEXITCODE -ne 0) { exit ${'$'}LASTEXITCODE }
                    
                    pixi run --environment default --frozen gh release create ${'$'}tag release/* --verify-tag --notes-file ${'$'}notesFile
                """.trimIndent()
            }
        }
    }

    dependencies {
        dependency(AbsoluteId("IMODCollector_X64development")) {
            snapshot {
                onDependencyFailure = FailureAction.FAIL_TO_START
            }

            artifacts {
                buildRule = lastSuccessful()
                artifactRules = "+:**/* => release"
            }
        }
    }
})

object DeployAll : BuildType({
    name = "Deploy All"

    type = Type.COMPOSITE
    maxRunningBuilds = 1

    vcs {
        root(ImodCoupler)

        cleanCheckout = true
        branchFilter = """
            +:*
            -:<default>
            -:refs/heads/gh-pages
        """.trimIndent()
        showDependenciesChanges = true
    }

    dependencies {
        snapshot(CreateGitHubRelease) {
        }
    }
})