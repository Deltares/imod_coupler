package Deploy

import IMODCollector.buildTypes.IMODCollector_X64development
import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.AbsoluteId
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.FailureAction
import jetbrains.buildServer.configs.kotlin.Project
import jetbrains.buildServer.configs.kotlin.buildSteps.powerShell
import jetbrains.buildServer.configs.kotlin.buildSteps.ScriptBuildStep
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object DeployProject : Project({
    name = "Deploy"

    buildType(BuildPrimodPackage)
    buildType(DeployPrimodPackage)
    buildType(CreateGitHubRelease)


    buildType(DeployAll)
})

object BuildPrimodPackage : BuildType({
    name = "Build Primod package"

    artifactRules = """imod_coupler\pre-processing\dist => dist.zip"""

    vcs {
        root(ImodCoupler, ". => imod_coupler")

        cleanCheckout = true
        branchFilter = """
            +:*
            -:<default>
            -:refs/heads/gh-pages
        """.trimIndent()
        showDependenciesChanges = true
    }

    steps {
        script {
            name = "Create Primod package"
            id = "Create_Primod_package"
            workingDir = "imod_coupler"
            scriptContent = """
                pixi run --environment dev --frozen build-primod
            """.trimIndent()
            formatStderrAsError = true
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }

})

object DeployPrimodPackage : BuildType({
     name = "Deploy Primod Package"

    params {
        param("env.TWINE_USERNAME", "__token__")
        param("env.TWINE_NON_INTERACTIVE", "true")
        password("env.TWINE_PASSWORD", "credentialsJSON:5b785916-d498-4c7f-9dca-e841152a761c")
    }

    vcs {
        root(ImodCoupler, ". => imod_coupler")

        cleanCheckout = true
        branchFilter = """
            +:*
            -:<default>
            -:refs/heads/gh-pages
        """.trimIndent()
        showDependenciesChanges = true
    }

    steps {
        script {
            name = "Deploy Primod to PyPi"
            id = "Deploy_Primod_to_PyPi"
            workingDir = "imod_coupler"
            scriptContent = """
                pixi run --environment dev --frozen publish-primod
            """.trimIndent()
        }
    }

    dependencies {
        dependency(BuildPrimodPackage) {
            snapshot {
                onDependencyFailure = FailureAction.FAIL_TO_START
            }

            artifacts {
                artifactRules = """+:dist.zip!** => imod_coupler\pre-processing\dist"""
            }
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
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
                    pixi run --environment dev --frozen python scripts/extract_changelog_notes.py ${'$'}tag | Set-Content -Path ${'$'}notesFile -Encoding UTF8
                    if (${'$'}LASTEXITCODE -ne 0) { exit ${'$'}LASTEXITCODE }
                    
                    pixi run --environment dev --frozen gh release create ${'$'}tag release/* --verify-tag --notes-file ${'$'}notesFile
                """.trimIndent()
            }
        }
    }

    dependencies {
        dependency(AbsoluteId("SigningAndCertificates_IMOD_SigningCollector")) {
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
        snapshot(DeployPrimodPackage) {
        }
       snapshot(CreateGitHubRelease) {
        }
    }
})