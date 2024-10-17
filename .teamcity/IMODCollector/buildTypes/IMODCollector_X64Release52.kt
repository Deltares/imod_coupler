package IMODCollector.buildTypes

import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildSteps.PowerShellStep
import jetbrains.buildServer.configs.kotlin.buildSteps.powerShell
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.finishBuildTrigger
import jetbrains.buildServer.configs.kotlin.triggers.schedule

object IMODCollector_X64Release52 : BuildType({
    name = "x64_Release5.2"
    description = "Collect all Release_x64 kernels in the iMOD6 suite"
    paused = true

    artifactRules = """
        dist/imodc.exe => imod_coupler.zip
        fmpich2.dll => imod_coupler.zip
        libmf6.dll => imod_coupler.zip
        MetaSWAP.dll => imod_coupler.zip
        mpich2mpi.dll => imod_coupler.zip
        mpich2nemesis.dll => imod_coupler.zip
        TRANSOL.dll => imod_coupler.zip
    """.trimIndent()

    vcs {
        root(IMODCollector.vcsRoots.IMODCollector_ImodCouplerReleaseImod52, "+:. => ./coupler")
    }

    steps {
        script {
            name = "Create imod_collector conda environment"
            scriptContent = """
                call conda env remove -n imod_collector 
                call conda create -n imod_collector -y python=3.8
            """.trimIndent()
        }
        script {
            name = "Install imod_coupler"
            workingDir = "coupler"
            scriptContent = """
                call conda activate imod_collector
                call pip install -e .
            """.trimIndent()
        }
        script {
            name = "Install pyinstaller"
            scriptContent = """
                call conda activate imod_collector
                pip install pyinstaller
            """.trimIndent()
        }
        script {
            name = "Create executable with pyinstaller"
            scriptContent = """
                call conda activate imod_collector
                pyinstaller --onefile coupler/imod_coupler/__main__.py --name imodc
            """.trimIndent()
        }
        script {
            name = "Remove conda virtualenv"
            scriptContent = "call conda env remove -n imod_collector"
        }
        powerShell {
            name = "Get MODFLOW6 dll"
            enabled = false
            platform = PowerShellStep.Platform.x64
            edition = PowerShellStep.Edition.Desktop
            scriptMode = script {
                content = """
                    ${'$'}URI = 'https://github.com/MODFLOW-USGS/executables/releases/download/5.0/win64.zip'
                    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                    Invoke-WebRequest -Uri ${'$'}URI -OutFile win64.zip
                    Microsoft.PowerShell.Archive\Expand-Archive -Path 'win64.zip' -DestinationPath '.\modflow_win64'
                    Copy-Item ".\modflow_win64\*.dll" -Destination "."
                    Remove-Item ".\win64.zip" -Force
                    Remove-Item ".\modflow_win64" -Force -Recurse
                """.trimIndent()
            }
        }
    }

    triggers {
        schedule {
            schedulingPolicy = daily {
                hour = 22
            }
            branchFilter = ""
            triggerBuild = always()
            param("revisionRuleBuildBranch", "<default>")
        }
        finishBuildTrigger {
            buildType = "MSWMOD_MetaSWAP_MetaSWAPBuildWin64fixedModFlowSimgro"
            successfulOnly = true
        }
        finishBuildTrigger {
            buildType = "MetaSWAP_Modflow_Modflow6ReleaseImod52"
            successfulOnly = true
        }
    }

    dependencies {
        dependency(AbsoluteId("MSWMOD_MetaSWAP_MetaSWAPBuildWin64fixedModFlowSimgro")) {
            snapshot {
            }

            artifacts {
                artifactRules = """
                    MetaSWAP.zip!/x64/Release/MetaSWAP.dll
                    MetaSWAP.zip!/x64/Release/fmpich2.dll
                    MetaSWAP.zip!/x64/Release/mpich2mpi.dll
                    MetaSWAP.zip!/x64/Release/mpich2nemesis.dll
                    MetaSWAP.zip!/x64/Release/TRANSOL.dll
                """.trimIndent()
            }
        }
        artifacts(AbsoluteId("MetaSWAP_Modflow_Modflow6ReleaseImod52")) {
            buildRule = lastSuccessful()
            artifactRules = "bin/libmf6.dll"
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
