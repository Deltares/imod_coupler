package IMODCollector.buildTypes

import Templates.GitHubIntegrationTemplate
import _Self.buildTypes.Lint
import _Self.buildTypes.MyPy
import _Self.buildTypes.TwineCheck
import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.FailureAction
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object IMODCollector_X64development : BuildType({
    name = "x64_development"
    description = "Collect all Release_x64 kernels in the iMOD6 suite"

    templates(GitHubIntegrationTemplate)

    artifactRules = """
        coupler/dist/ => imod_collector.zip!/
        .imod_collector/develop/modflow6/ => imod_collector.zip!/modflow6/
        .imod_collector/develop/metaswap/ => imod_collector.zip!/metaswap/
        .imod_collector/develop/ribasim/ => imod_collector.zip!/ribasim/
    """.trimIndent()

    vcs {
        root(ImodCoupler, "+:. => ./coupler")

        cleanCheckout = true
    }

    steps {
        script {
            name = "Set up pixi"
            workingDir = "coupler"
            scriptContent = """
                pixi --version
                pixi install -e dev
                pixi list
            """.trimIndent()
        }
        script {
            name = "Get coupler dependencies"
            workingDir = "coupler"
            scriptContent = """
                pixi run -e dev install-imod-collector
            """.trimIndent()
        }
        script {
            name = "Create executable with pyinstaller"
            workingDir = "coupler"
            scriptContent = """
                pixi run -e dev build-imod-coupler
            """.trimIndent()
        }
        script {
            name = "Get version from imod coupler"
            workingDir = "coupler"
            scriptContent = """call dist\imodc --version"""
        }
    }

    dependencies {
        snapshot(Lint){
            onDependencyFailure = FailureAction.FAIL_TO_START
        }

        snapshot(MyPy){
            onDependencyFailure = FailureAction.FAIL_TO_START
        }

        snapshot(TwineCheck){
            onDependencyFailure = FailureAction.FAIL_TO_START
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
