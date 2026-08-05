package IMODCollector.buildTypes

import Templates.GitHubIntegrationTemplate
import _Self.buildTypes.Lint
import _Self.buildTypes.MyPy
import _Self.buildTypes.TwineCheck
import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.buildFeatures.dockerRegistryConnections
import jetbrains.buildServer.configs.kotlin.FailureAction
import jetbrains.buildServer.configs.kotlin.buildSteps.ScriptBuildStep
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object IMODCollector_X64development : BuildType({
    name = "x64_development"
    description = "Collect all Release_x64 kernels in the iMOD6 suite"

    templates(GitHubIntegrationTemplate)

    artifactRules = """
        coupler/dist/ => imod_collector.zip!/
        coupler/.imod_collector/develop/modflow6/ => imod_collector.zip!/modflow6/
        coupler/.imod_collector/develop/metaswap/ => imod_collector.zip!/metaswap/
        coupler/.imod_collector/develop/ribasim/ => imod_collector.zip!/ribasim/
        coupler/pixi.lock
        coupler/pixi.toml
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
                pixi config set --local detached-environments "C:\pixi_envs"
                pixi install -e dev
                pixi list
                
                echo "Get coupler dependencies"
                pixi run -e dev fetch-imod-collector
                
                echo "Create executable with pyinstaller"
                pixi run -e dev build-imod-coupler
                
                echo "Get version from imod coupler"
                call dist\imodc --version
            """.trimIndent()
            formatStderrAsError = true
            dockerImage = "%DockerContainer%:%DockerVersion%"
            dockerImagePlatform = ScriptBuildStep.ImagePlatform.Windows
            dockerRunParameters = """--cpus=4 --memory=16g"""
            dockerPull = false
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

    features {
        dockerRegistryConnections {
            loginToRegistry = on {
                dockerRegistryId = "PROJECT_EXT_342"
            }
        }
    }
})
