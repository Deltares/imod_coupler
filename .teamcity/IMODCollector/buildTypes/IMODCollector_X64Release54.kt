package IMODCollector.buildTypes

import _Self.vcsRoots.ImodCouplerImod54
import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.finishBuildTrigger
import jetbrains.buildServer.configs.kotlin.triggers.vcs

object IMODCollector_X64Release54 : BuildType({
    name = "x64_Release5.4"
    description = "Collect all Release_x64 kernels in the iMOD6 suite"

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
        root(_Self.vcsRoots.ImodCouplerImod54, "+:. => ./coupler")
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
    }

    triggers {
        finishBuildTrigger {
            buildType = "MSWMOD_MetaSWAP_MetaSWAPReleaseImod54"
            successfulOnly = true
        }
        finishBuildTrigger {
            buildType = "MetaSWAP_Modflow_Modflow6ReleaseImod54"
            successfulOnly = true
        }
        vcs {
            triggerRules = "+:root=${ImodCouplerImod54.id}:**"

            branchFilter = ""
        }
    }

    dependencies {
        dependency(AbsoluteId("MSWMOD_MetaSWAP_MetaSWAPReleaseImod54")) {
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
        dependency(AbsoluteId("MetaSWAP_Modflow_Modflow6ReleaseImod54")) {
            snapshot {
            }

            artifacts {
                artifactRules = "srcbmi/libmf6.dll"
            }
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
