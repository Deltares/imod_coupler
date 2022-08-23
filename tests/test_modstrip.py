import shutil
import subprocess


def fill_para_sim_template(msw_folder, path_unsat_dbase):
    """
    Fill para_sim.inp template in the folder with the path to the unsaturated
    zone database.
    """
    with open(msw_folder / "para_sim_template.inp") as f:
        para_sim_text = f.read()

    para_sim_text = para_sim_text.replace("{{unsat_path}}", f"{path_unsat_dbase}\\")

    with open(msw_folder / "para_sim.inp", mode="w") as f:
        f.write(para_sim_text)


def test_modstrip_model(
    modstrip_loc, tmp_path, metaswap_lookup_table, imod_coupler_exec_devel
):
    """
    Run modstrip model
    """

    shutil.copytree(modstrip_loc, tmp_path, dirs_exist_ok=True)

    fill_para_sim_template(tmp_path / "msw", metaswap_lookup_table)

    subprocess.run(
        [imod_coupler_exec_devel, tmp_path / "imod_coupler.toml"], check=True
    )
