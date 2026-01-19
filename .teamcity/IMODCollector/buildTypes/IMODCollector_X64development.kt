package IMODCollector.buildTypes

import Templates.GitHubIntegrationTemplate
import _Self.buildTypes.Lint
import _Self.buildTypes.MyPy
import _Self.buildTypes.TwineCheck
import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.AbsoluteId
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.FailureAction
import jetbrains.buildServer.configs.kotlin.buildSteps.script

object IMODCollector_X64development : BuildType({
    name = "x64_development"
    description = "Collect all Release_x64 kernels in the iMOD6 suite"

    templates(GitHubIntegrationTemplate)

    artifactRules = """
        coupler/dist/ => imod_collector.zip!/
        modflow6/ => imod_collector.zip!/modflow6/
        metaswap/ => imod_collector.zip!/metaswap/
        ribasim/ => imod_collector.zip!/ribasim/
    """.trimIndent()

    params {
        param("conda_env_path", "%system.teamcity.build.checkoutDir%/imod_collector_env")
        param("reverse.dep.Modflow_Modflow6Release.MODFLOW6_Version", "6.6.3")
        param("reverse.dep.Modflow_Modflow6Release.MODFLOW6_Platform", "win64")
        param("reverse.dep.iMOD6_Coupler_Ribasim_binaries.RIBASIM_Version", "v2025.6.0")
        param("reverse.dep.iMOD6_Coupler_Ribasim_binaries.RIBASIM_Platform", "windows")
    }

    vcs {
        root(ImodCoupler, "+:. => ./coupler")

        cleanCheckout = true
    }

    steps {
        script {
            name = "Install iMOD Coupler"
            enabled = false
            workingDir = "coupler"
            scriptContent = """
                call conda activate %conda_env_path%
                call pip install -e .
            """.trimIndent()
        }
        script {
            name = "Create executable with pyinstaller"
            workingDir = "coupler"
            scriptContent = """
                rmdir dist /s /q
                pixi run -e dev pyinstaller --onefile imod_coupler/__main__.py --name imodc
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

        dependency(AbsoluteId("Modflow_Modflow6Release")) {
            snapshot {
                onDependencyFailure = FailureAction.FAIL_TO_START
            }
            artifacts {
                artifactRules = "+:MODFLOW6.zip!** => modflow6"
            }
        }

        dependency(AbsoluteId("iMOD6_Coupler_Ribasim_binaries")) {
            snapshot {
                onDependencyFailure = FailureAction.FAIL_TO_START
            }
            artifacts {
                artifactRules = "+:ribasim.zip!** => ribasim"
            }
        }

        artifacts(AbsoluteId("MSWMOD_MetaSWAP_MetaSWAPBuildWin64")) {
           cleanDestination = true
           buildRule = lastSuccessful("+::branches/update_4210")
           artifactRules = "MetaSWAP.zip!/x64/Release => metaswap"
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
