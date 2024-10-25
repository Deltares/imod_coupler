package IMODCollector.buildTypes

import _Self.vcsRoots.ImodCoupler
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildFeatures.PullRequests
import jetbrains.buildServer.configs.kotlin.buildFeatures.commitStatusPublisher
import jetbrains.buildServer.configs.kotlin.buildFeatures.pullRequests
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.finishBuildTrigger

object IMODCollector_X64ReleaseLnx64 : BuildType({
    name = "x64_Release_lnx64"
    description = "Collect all Release_x64 kernels in the iMOD6 suite"

    artifactRules = """
        coupler/dist/ => imod_collector.zip!/
        modflow6/ => imod_collector.zip!/modflow6/
        metaswap/ => imod_collector.zip!/metaswap/
        ribasim/  => imod_collector.zip!/ribasim/
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
            name = "Create executable with pyinstaller"
            workingDir = "./coupler"
            scriptContent = """
                #!/bin/bash
                source  /usr/share/Modules/init/profile.sh
                module load pixi
                rm -rf dist
                pixi run -e dev install-minimal
                pixi run -e dev pyinstaller --onefile imod_coupler/__main__.py --name imodc
            """.trimIndent()
        }
        script {
            name = "Get version from imod coupler"
            id = "RUNNER_1232"
            scriptContent = "./coupler/dist/imodc --version"
        }
        script {
            name = "Download Release MODFLOW 6.5.0"
            scriptContent = """
                curl -L -o mf6.5.0_linux.zip  https://github.com/MODFLOW-USGS/modflow6/releases/download/6.5.0/mf6.5.0_linux.zip
                unzip  -j "mf6.5.0_linux.zip" -d modflow6 mf6.5.0_linux/bin/libmf6.so
            """.trimIndent()
        }
        script {
            name = "Download Release Ribasim v2024.11.0"
            scriptContent = """
                curl -L -o ribasim_linux.zip https://github.com/Deltares/Ribasim/releases/download/v2024.11.0/ribasim_linux.zip
                unzip  "ribasim_linux.zip"
            """.trimIndent()
        }
    }

    dependencies {
        artifacts(AbsoluteId("MSWMOD_MetaSWAP_MetaSWAPDevelopLnx64")) {
            cleanDestination = true
            buildRule = tag("release_2410")
            artifactRules = "libmsw.so => metaswap/"
        }
    }

    requirements {
        equals("env.OS", "Linux", "RQ_341")
    }
})
