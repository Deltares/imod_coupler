package IMODCollector.buildTypes

import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.finishBuildTrigger
import jetbrains.buildServer.configs.kotlin.triggers.schedule

object IMODCollector_X64Release53 : BuildType({
    name = "x64_Release5.3"
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
        root(IMODCollector.vcsRoots.IMODCollector_ImodCouplerReleaseImod53, "+:. => ./coupler")
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
        dependency(AbsoluteId("MSWMOD_MetaSWAP_MetaSWAPReleaseImod53")) {
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
        dependency(AbsoluteId("MetaSWAP_Modflow_Modflow6ReleaseImod53")) {
            snapshot {
            }

            artifacts {
                artifactRules = "bin/libmf6.dll"
            }
        }
    }

    requirements {
        equals("env.OS", "Windows_NT")
    }
})
