package _Self.vcsRoots

import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.vcs.SvnVcsRoot

object MetaSwapLookupTable : SvnVcsRoot({
    name = "MetaSwap_LookupTable"
    url = "https://repos.deltares.nl/repos/DSCTestbench/trunk/cases/e150_metaswap/f00_common/c00_common/LHM2016_v01vrz"
    userName = "%svn_buildserver_username%"
    password = "credentialsJSON:4fe21828-8cba-44b7-b969-203d6a5d0a5f"
})
