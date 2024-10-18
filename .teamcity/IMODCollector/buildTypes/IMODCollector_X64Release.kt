package IMODCollector.buildTypes

import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildFeatures.PullRequests
import jetbrains.buildServer.configs.kotlin.buildFeatures.commitStatusPublisher
import jetbrains.buildServer.configs.kotlin.buildFeatures.pullRequests
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.finishBuildTrigger

object IMODCollector_X64Release : BuildType({
    name = "x64_Release"
    description = "Collect all Release_x64 kernels in the iMOD6 suite"

    artifactRules = """
        coupler/dist/ => imod_collector.zip!/
        modflow6/ => imod_collector.zip!/modflow6/
        metaswap/ => imod_collector.zip!/metaswap/
        ribasim/ribasim/ => imod_collector.zip!/ribasim/
    """.trimIndent()

    params {
        param("conda_env_path", "%system.teamcity.build.checkoutDir%/imod_collector_env")
    }

    vcs {
        root(_Self.vcsRoots.ImodCoupler, "+:. => ./coupler")

        cleanCheckout = true
    }

    steps {
        script {
            name = "Create imod_collector conda environment"
            id = "Create_imod_collector_conda_environment"
            enabled = false
            scriptContent = """
                if exist "%conda_env_path%" rd /q /s "%conda_env_path%"
                conda env create --file coupler/environment-minimal.yml -p "%conda_env_path%"
            """.trimIndent()
        }
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
                pixi run -e dev install-minimal
                pixi run -e dev pyinstaller --onefile imod_coupler/__main__.py --name imodc
            """.trimIndent()
        }
        script {
            name = "Get version from imod coupler"
            workingDir = "coupler"
            scriptContent = """call dist\imodc --version"""
        }
        script {
            name = "Download Release MODFLOW 6.5.0"
            scriptContent = """
                mkdir modflow6
                curl -O https://water.usgs.gov/water-resources/software/MODFLOW-6/mf6.5.0_win64.zip
                unzip  -j "mf6.5.0_win64.zip" -d modflow6 mf6.5.0_win64/bin/libmf6.dll
            """.trimIndent()
        }
        script {
            name = "Download Release Ribasim v2024.11.0"
            scriptContent = """
                mkdir modflow6
                curl -O https://github.com/Deltares/Ribasim/releases/download/v2024.11.0/ribasim_windows.zip
                unzip  "ribasim_windows.zip"
            """.trimIndent()
        }
    }

    dependencies {
        artifacts(AbsoluteId("MSWMOD_MetaSWAP_MetaSWAPBuildWin64trunk")) {
           cleanDestination = true
           buildRule = tag("release_2410")
           artifactRules = "MetaSWAP.zip!/x64/Release => metaswap"
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
