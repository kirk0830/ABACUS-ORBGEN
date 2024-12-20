'''
Concepts
--------
this module defines ABACUS related (input and output) operations.
'''
import re
from SIAB.supercomputing.op import op as envop
from SIAB.data.structures import monomer, dimer, trimer, tetrahedron,\
    square, triangular_bipyramid, octahedron, cube

BLSCAN_WARNMSG = """
WARNING: since SIAB version 2.1(2024.6.3), the original functionality invoked by value \"auto\" is replaced by 
        \"scan\", and for dimer the \"auto\" now will directly use in-built dimer database if available, otherwise will 
         fall back to \"scan\". This warning will be print everytime if \"auto\" is used. To disable this warning, specify 
         directly the \"bond_lengths\" in any one of following ways:
         1. a list of floats, e.g. [2.0, 2.5, 3.0]
         2. a string \"default\", which will use default bond length for dimer, and scan for other shapes, for other shapes, will
            fall back to \"scan\".
         3. a string \"scan\", which will scan bond lengths for present shape.
"""
##############################################
#         input files preparation            #
##############################################

def STRU(shape: str, element: str, mass: float, fpseudo: str, 
         lattice_constant: float, bond_length: float, nspin: int,
         forb = None):
    """generate structure"""
    if shape == "monomer":
        return monomer(element, mass, fpseudo, lattice_constant, nspin, forb), 1
    elif shape == "dimer":
        return dimer(element, mass, fpseudo, lattice_constant, bond_length, nspin, forb), 2
    elif shape == "trimer":
        return trimer(element, mass, fpseudo, lattice_constant, bond_length, nspin, forb), 3
    elif shape == "tetrahedron":
        return tetrahedron(element, mass, fpseudo, lattice_constant, bond_length, nspin, forb), 4
    elif shape == "square":
        return square(element, mass, fpseudo, lattice_constant, bond_length, nspin, forb), 4
    elif shape == "triangular_bipyramid":
        return triangular_bipyramid(element, mass, fpseudo, lattice_constant, bond_length, nspin, forb), 5
    elif shape == "octahedron":
        return octahedron(element, mass, fpseudo, lattice_constant, bond_length, nspin, forb), 6
    elif shape == "cube":
        return cube(element, mass, fpseudo, lattice_constant, bond_length, nspin, forb), 8
    else:
        raise NotImplementedError("Unknown shape %s"%shape)

def KPOINTS():
    """For ABACUS-orbitals numerical orbitals generation workflow specifically"""
    return "K_POINTS\n0\nGamma\n1 1 1 0 0 0\n"

def INPUT(calculation_setting: dict,
          suffix: str = "") -> str:
    """generate INPUT file for orbital generation task. This function is designed with following
    logic:
    1. user will not use keywords more than this function's consideration
    2. user may define different values for some keywords, if that happens, overwrite the default
    3. write to INPUT from the inbuilt_template
    """
    inbuilt_template = {
        "suffix": "ABACUS", "stru_file": "STRU", "kpoint_file": "KPT", 
        "wannier_card": "INPUTw", # wannier_card is deprecated
        "pseudo_dir": "./",
        "calculation": "scf",     # calculation, definitely to be scf for orbital generation
        "basis_type": "pw", "ecutwfc": "100",
        "ks_solver": "dav", "nbands": "auto", "scf_thr": "1.0e-7", "scf_nmax": "9000", # scf control
        "ntype": "1", "nspin": "1", # system info
        "lmaxmax": "4", "bessel_nao_rcut": "10", # orbital generation control
        "smearing_method": "gauss", "smearing_sigma": "0.015", # for improving convergence
        "mixing_type": "broyden", "mixing_beta": "0.8", "mixing_ndim": "8", "mixing_gg0": "0", # mixing control
        "gamma_only": "1", # force gamma point only calculation
        "printe": "1" # print energy
    }
    if calculation_setting.get('basis_type', 'lcao') != 'pw':
        inbuilt_template.update({'ks_solver': 'genelpa'})

    if "nspin" in calculation_setting.keys():
        if calculation_setting["nspin"] == 2:
            inbuilt_template["nspin"] = 2
            inbuilt_template["mixing_beta"] = 0.4
            inbuilt_template["mixing_beta_mag"] = 0.4
            
    all_params = abacus_params()
    result = "INPUT_PARAMETERS"
    for key, val in calculation_setting.items():
        if val is None:
            continue
        if key in all_params:
            val = " ".join([str(v) for v in val]) if isinstance(val, list) else val
            inbuilt_template[key] = val
        else:
            print("WARNING: keyword %s might be unknown."%key, flush=True)

    if suffix != "":
        inbuilt_template["suffix"] = suffix
        inbuilt_template["stru_file"] += "-"+suffix
        inbuilt_template["kpoint_file"] += "-"+suffix

    if inbuilt_template["basis_type"] != "pw":
        inbuilt_template.update({
            "out_mat_hs": "1 12",
            "out_mat_tk": "1 12",
            "out_wfc_lcao": 1
        })
    inbuilt_template.update({"out_chg": -1}) # disable the out_chg or set init_chg auto?
    # write
    for key, value in inbuilt_template.items():
        result += "\n%-20s %s"%(key, value)

    return result

##############################################
#              file operations               #
##############################################
def configure(input_setting: dict,
              stru_setting: dict):
    """generate input files for orbital generation in present folder
    
    input_settings: dict, INPUT settings for ABACUS
    stru_settings: dict, structure settings for ABACUS

    Return:
        folder: str, a string used to distinguish different orbital generation tasks
    Details:
        in `stru_settings`, at least contain `shape`, `element`, `fpseudo` and `bond_length`
        information.
    """
    import os
    # CHECK
    necessary_keys = ["element", "shape", "fpseudo", "bond_length"]
    for necessary_key in necessary_keys:
        if necessary_key not in stru_setting.keys():
            raise ValueError("key %s is not specified"%necessary_key)
    
    # mostly value will not be None, except the case the monomer is included to be referred
    # in initial guess of coefficients of sphbes
    keys_in_foldername = ["element", "shape"]
    keys_in_foldername.append("bond_length") if stru_setting["shape"] != "monomer" else None
    # because bond_length is not necessary for monomer

    def write(suffix, inp, stru):
        inp = INPUT(inp, suffix)
        stru = STRU(**stru)
        with open("INPUT-"+suffix, "w") as f:
            f.write(inp)
        with open("STRU-"+suffix, "w") as f:
            f.write(stru[0])
        with open("KPT-"+suffix, "w") as f:
            f.write(KPOINTS())
        with open("INPUTw", "w") as f:
            f.write("WANNIER_PARAMETERS\n")
            f.write("out_spillage 2\n")
        return suffix

    folder = f"{stru_setting['element']}-{stru_setting['shape']}"
    folder += "-%3.2f"%stru_setting["bond_length"] if stru_setting["shape"] != "monomer" else ""
    orbital_dir = input_setting.get("orbital_dir")
    if orbital_dir is not None:
        forbs = [os.path.basename(f) for f in orbital_dir]
        dirs = [os.path.dirname(d) for d in orbital_dir]
        assert len(set(dirs)) == 1, "all temporary jybasis files is set to the same directory"
        assert len(forbs) == len(input_setting["bessel_nao_rcut"]), "number of forbs should be the same as bessel_nao_rcut"
        
        for forb, rcut in zip(forbs, input_setting["bessel_nao_rcut"]):
            inp = input_setting.copy()
            inp.update({"bessel_nao_rcut": rcut, "orbital_dir": dirs[0]})
            stru_setting["forb"] = forb
            folder_rcut = "-".join([folder, str(rcut) + "au"])
            yield write(folder_rcut, inp, stru_setting)
    else:
        yield write(folder, input_setting, stru_setting)

def archive(footer: str = "", env: str = "local"):

    """mkdir and move correspnding input files to folder"""
    headers = ["INPUT", "STRU", "KPT"]
    if footer != "":
        envop("mkdir", footer, additional_args=["-p"], env=env)
        for header in headers:
            if header == "INPUT":
                envop("mv", "%s-%s"%(header, footer), "%s/INPUT"%(footer), env=env)
            else:
                envop("mv", "%s-%s"%(header, footer), "%s/"%(footer), env=env)
        envop("mv", "INPUTw", "%s/INPUTw"%(footer), env=env)
    else:
        raise ValueError("footer is not specified")

def read_INPUT(folder: str = "") -> dict:
    """parse ABACUS INPUT file, return a dict"""
    if folder.startswith("INPUT_PARAMETERS"):
        lines = folder.split("\n")
    else:
        with open(folder+"/INPUT", "r") as f:
            lines = f.readlines()

    pattern = r"^(\s*)([\w_]+)(\s+)([^\#]+)(.*)$"
    result = {}
    for line in lines:
        if line == "INPUT_PARAMETERS":
            continue
        else:
            match = re.match(pattern, line.strip())
            if match is not None:
                result[match.group(2)] = match.group(4)
    return result

def abacus_params():
    return list(read_INPUT(ABACUS_INPUT_TEMPLATE).keys())

DEFAULT_BOND_LENGTH = {
"dimer": {'H': [0.6, 0.75, 0.9, 1.2, 1.5], 'He': [1.25, 1.75, 2.4, 3.25], 
'Li': [1.5, 2.1, 2.5, 2.8, 3.2, 3.5, 4.2], 'Be': [1.75, 2.0, 2.375, 3.0, 4.0], 'B': [1.25, 1.625, 2.5, 3.5], 
'C': [1.0, 1.25, 1.5, 2.0, 3.0], 'N': [1.0, 1.1, 1.5, 2.0, 3.0], 'O': [1.0, 1.208, 1.5, 2.0, 3.0], 
'F': [1.2, 1.418, 1.75, 2.25, 3.25], 'Fm': [1.98, 2.375, 2.75, 3.25, 4.25], 'Md': [2.08, 2.5, 3.0, 3.43, 4.25], 
'No': [2.6, 3.125, 3.75, 4.27, 5.0], 'Ne': [1.5, 1.75, 2.25, 2.625, 3.0, 3.5], 'Na': [2.05, 2.4, 2.8, 3.1, 3.3, 3.8, 4.3], 
'Mg': [2.125, 2.375, 2.875, 3.375, 4.5], 'Al': [2.0, 2.5, 3.0, 3.75, 4.5], 'Si': [1.75, 2.0, 2.25, 2.75, 3.75], 
'P': [1.625, 1.875, 2.5, 3.25, 4.0], 'S': [1.6, 1.9, 2.5, 3.25, 4.0], 'Cl': [1.65, 2.0, 2.5, 3.25, 4.0], 
'Ar': [2.25, 2.625, 3.0, 3.375, 4.0], 'K': [1.8, 2.6, 3.4, 3.8, 4.0, 4.4, 4.8], 'Ca': [2.5, 3.0, 3.5, 4.0, 5.0], 
'Sc': [1.75, 2.15, 2.75, 3.5, 4.5], 'Ti': [1.6, 1.85, 2.5, 3.25, 4.25], 'V': [1.45, 1.65, 2.25, 3.0, 4.0], 
'Cr': [1.375, 1.55, 2.0, 2.75, 3.75], 'Mn': [1.4, 1.6, 2.1, 2.75, 3.75], 'Fe': [1.45, 1.725, 2.25, 3.0, 4.0], 
'Co': [1.8, 2.0, 2.5, 3.5], 'Ni': [1.65, 2.0, 2.5, 3.0, 4.0], 'Cu': [1.8, 2.2, 3.0, 4.0], 
'Zn': [2.0, 2.3, 2.85, 3.5, 4.25], 'Ga': [1.85, 2.1, 2.45, 3.0, 4.0], 'Ge': [1.8, 2.0, 2.35, 3.0, 4.0], 
'As': [1.75, 2.1, 2.5, 3.0, 4.0], 'Se': [1.85, 2.15, 2.5, 3.0, 4.0], 'Br': [1.9, 2.25, 2.75, 3.25, 4.0], 
'Kr': [2.4, 3.0, 3.675, 4.25, 5.0], 'Rb': [2.45, 3.0, 4.0, 5.0], 'Sr': [2.75, 3.5, 4.4, 5.0], 
'Y': [2.125, 2.5, 2.875, 3.25, 4.0, 5.0], 'Zr': [1.9, 2.25, 3.0, 4.0], 'Nb': [1.75, 2.05, 2.4, 3.0, 4.0], 
'Mo': [1.675, 1.9, 2.375, 3.0, 4.0], 'Tc': [1.7, 1.915, 2.375, 3.0, 4.0], 'Ru': [1.725, 1.925, 2.375, 3.0, 4.0], 
'Rh': [1.8, 2.1, 2.5, 3.0, 4.0], 'Pd': [2.0, 2.275, 2.75, 3.75], 'Ag': [2.1, 2.45, 3.0, 4.0], 
'Cd': [2.15, 2.5, 3.1, 4.0, 5.0], 'In': [2.15, 2.5, 3.0, 3.75, 4.75], 'Sn': [2.1, 2.4, 3.75, 3.5, 4.5], 
'Sb': [2.1, 2.5, 3.0, 3.5, 4.5], 'Te': [2.15, 2.55, 3.1, 3.6, 4.5], 'I': [2.22, 2.65, 3.25, 4.25], 
'Xe': [3.0, 3.5, 4.06, 4.5, 5.25], 'Cs': [2.7, 3.5, 4.5, 5.5], 'Ba': [2.65, 3.0, 3.5, 4.4, 5.5], 
'La': [2.2, 2.6, 3.25, 4.0, 5.0], 'Ce': [2.0, 2.375, 2.875, 3.5, 4.5], 'Pr': [1.9, 2.25, 2.75, 3.5, 4.5], 
'Nd': [1.8, 2.125, 2.625, 3.375, 4.5], 'Pm': [1.775, 2.05, 2.5, 3.25, 4.25], 'Sm': [1.775, 2.05, 2.5, 3.25, 4.25], 
'Eu': [1.775, 2.075, 2.5, 3.25, 4.25], 'Gd': [1.8, 2.11, 2.625, 3.375, 4.1, 5.0], 'Tb': [1.825, 2.16, 2.625, 3.375, 4.1, 5.0], 
'Dy': [1.85, 2.24, 2.625, 3.375, 4.1, 5.0], 'Ho': [1.93, 2.375, 3.0, 4.1, 5.0], 'Er': [2.025, 2.5, 3.125, 4.1, 5.0], 
'Tm': [2.2, 2.625, 3.25, 4.1, 5.0], 'Yb': [2.5, 3.0, 3.5, 4.1, 5.0], 'Lu': [2.2, 2.5, 3.04, 4.0, 5.0], 
'Hf': [1.975, 2.49, 3.25, 4.5], 'Ta': [1.85, 2.12, 2.625, 3.25, 4.5], 'W': [1.775, 1.99, 2.5, 3.25, 4.5], 
'Re': [1.775, 2.01, 2.5, 3.25, 4.25], 'Os': [1.8, 2.04, 2.5, 3.25, 4.5], 'Ir': [1.85, 2.125, 2.5, 3.25, 4.25], 
'Pt': [2.0, 2.275, 2.75, 3.75], 'Au': [2.1, 2.45, 3.0, 4.0], 'Hg': [2.225, 2.5, 3.04, 4.0, 5.0], 
'Tl': [2.21, 2.6, 3.11, 3.75, 4.75], 'Pb': [2.225, 2.5, 2.88, 3.625, 4.5], 'Bi': [2.225, 2.61, 3.125, 3.75, 4.75], 
'Po': [2.3, 2.72, 3.25, 3.875, 4.75], 'At': [2.375, 2.83, 3.5, 4.5], 'Rn': [2.8, 3.5, 4.17, 4.75, 5.5], 
'Fr': [2.85, 3.5, 4.43, 5.5], 'Ra': [3.15, 3.5, 4.25, 5.12, 6.0], 'Ac': [2.48, 3.1, 3.72, 4.25, 5.0], 
'Th': [2.25, 2.65, 3.25, 4.0, 5.0], 'Pa': [2.04, 2.3, 3.0, 3.75, 4.75], 'U': [1.89, 2.09, 2.75, 3.5, 4.5], 
'Np': [1.84, 2.05, 2.625, 3.375, 4.5], 'Pu': [1.81, 2.02, 2.5, 3.25, 4.25], 'Am': [1.81, 2.03, 2.5, 3.25, 4.25], 
'Cm': [1.83, 2.07, 2.5, 3.25, 4.25], 'Bk': [1.86, 2.12, 2.5, 3.0, 4.0], 'Cf': [1.89, 2.19, 2.625, 3.125, 4.0], 
'Es': [1.93, 2.29, 2.625, 3.125, 4.0]},
"trimer": {'S': [1.7, 2.2, 2.8], 'Pd': [2.2, 2.6, 3.2], 'Si': [1.9, 2.1, 2.6], 
'Te': [2.4, 2.8, 3.4], 'Sn': [2.3, 2.6, 3.1], 'Xe': [3.8, 4.3, 5.0], 'Mo': [1.8, 2.1, 2.7], 'In': [2.3, 2.8, 3.4], 
'Nb': [1.6, 1.9, 2.7], 'Ga': [2.3, 2.7, 3.4], 'Br': [2.1, 2.5, 3.0], 'Ir': [2.0, 2.3, 3.8], 'Be': [2.2, 2.7, 3.4], 
'W': [1.7, 1.9, 2.2], 'Mg': [2.7, 3.2, 3.9], 'Sb': [2.2, 2.7, 3.3], 'Re': [1.9, 2.2, 2.8], 'Ba': [3.2, 3.9, 4.7], 
'Rb': [3.9, 4.7, 5.5], 'Ag': [2.3, 2.7, 3.2], 'Hg': [2.7, 3.5, 4.3], 'Zn': [2.5, 3.2, 3.8], 'Cr': [1.5, 1.8, 2.3], 
'Os': [1.9, 2.2, 2.8], 'Na': [2.8, 3.4, 4.1], 'H': [0.7, 0.9, 1.3], 'Sc': [2.0, 2.5, 3.1], 'Zr': [2.1, 2.5, 3.1], 
'Se': [2.1, 2.3, 2.7], 'Al': [2.3, 2.8, 3.4], 'Rh': [2.0, 2.3, 2.7], 'Y': [2.4, 2.9, 3.6], 'B': [1.2, 1.5, 2.1], 
'Ca': [2.8, 3.6, 4.6], 'Fe': [1.6, 2.0, 2.9], 'Tc': [1.5, 1.8, 2.2], 'Cs': [4.3, 5.0, 5.8], 'Ne': [2.0, 2.7, 3.3], 
'C': [1.1, 1.4, 2.1], 'Ar': [2.8, 3.2, 3.7], 'He': [1.5, 2.0, 2.6], 'N': [0.9, 1.2, 1.6], 'Au': [2.3, 2.7, 3.2], 
'Pt': [2.2, 2.6, 3.2], 'F': [1.3, 1.6, 2.1], 'Ge': [1.9, 2.2, 2.8], 'Co': [2.0, 2.4, 2.9], 'Cl': [1.6, 1.8, 2.2], 
'Ti': [1.7, 2.2, 2.9], 'K': [3.0, 3.8, 4.6], 'V': [1.6, 1.9, 2.6], 'Cu': [2.0, 2.4, 3.0], 'Pb': [2.3, 2.7, 3.3], 
'O': [1.1, 1.4, 2.1], 'As': [2.0, 2.3, 2.7], 'Li': [1.9, 2.4, 3.3], 'Bi': [2.4, 2.9, 3.5], 'Ru': [1.8, 2.1, 2.7], 
'Sr': [3.5, 4.1, 4.7], 'Kr': [3.3, 4.0, 4.7], 'I': [2.4, 2.9, 3.5], 'Ta': [1.7, 2.0, 2.3], 'Mn': [1.5, 1.8, 2.5], 
'Tl': [2.4, 3.3, 4.3], 'Ni': [1.9, 2.3, 2.8], 'P': [1.7, 2.2, 2.8], 'Hf': [2.3, 2.8, 3.4], 'Cd': [2.7, 3.6, 4.5]}}

ABACUS_INPUT_TEMPLATE = """INPUT_PARAMETERS
#Parameters (1.General)
suffix                         ABACUS #the name of main output directory
latname                        none #the name of lattice name
stru_file                      STRU #the filename of file containing atom positions
kpoint_file                    KPT #the name of file containing k points
pseudo_dir                     ../../../tests/PP_ORB/ #the directory containing pseudo files
orbital_dir                     #the directory containing orbital files
pseudo_rcut                    15 #cut-off radius for radial integration
pseudo_mesh                    0 #0: use our own mesh to do radial renormalization; 1: use mesh as in QE
lmaxmax                        2 #maximum of l channels used
dft_functional                 default #exchange correlation functional
xc_temperature                 0 #temperature for finite temperature functionals
calculation                    scf #test; scf; relax; nscf; get_wf; get_pchg
esolver_type                   ksdft #the energy solver: ksdft, sdft, ofdft, tddft, lj, dp
ntype                          1 #atom species number
nspin                          1 #1: single spin; 2: up and down spin; 4: noncollinear spin
kspacing                       0 0 0  #unit in 1/bohr, should be > 0, default is 0 which means read KPT file
min_dist_coef                  0.2 #factor related to the allowed minimum distance between two atoms
nbands                         0 #number of bands
nbands_sto                     256 #number of stochastic bands
nbands_istate                  5 #number of bands around Fermi level for get_pchg calulation
symmetry                       1 #the control of symmetry
init_vel                       0 #read velocity from STRU or not
symmetry_prec                  1e-06 #accuracy for symmetry
symmetry_autoclose             1 #whether to close symmetry automatically when error occurs in symmetry analysis
nelec                          0 #input number of electrons
nelec_delta                    0 #change in the number of total electrons
out_mul                        0 # mulliken  charge or not
noncolin                       0 #using non-collinear-spin
lspinorb                       0 #consider the spin-orbit interaction
kpar                           1 #devide all processors into kpar groups and k points will be distributed among each group
bndpar                         1 #devide all processors into bndpar groups and bands will be distributed among each group
out_freq_elec                  0 #the frequency ( >= 0) of electronic iter to output charge density and wavefunction. 0: output only when converged
dft_plus_dmft                  0 #true:DFT+DMFT; false: standard DFT calcullation(default)
rpa                            0 #true:generate output files used in rpa calculation; false:(default)
printe                         100 #Print out energy for each band for every printe steps
mem_saver                      0 #Only for nscf calculations. if set to 1, then a memory saving technique will be used for many k point calculations.
diago_proc                     1 #the number of procs used to do diagonalization
nbspline                       -1 #the order of B-spline basis
wannier_card                   none #input card for wannier functions
soc_lambda                     1 #The fraction of averaged SOC pseudopotential is given by (1-soc_lambda)
cal_force                      0 #if calculate the force at the end of the electronic iteration
out_freq_ion                   0 #the frequency ( >= 0 ) of ionic step to output charge density and wavefunction. 0: output only when ion steps are finished
device                         cpu #the computing device for ABACUS
precision                      double #the computing precision for ABACUS

#Parameters (2.PW)
ecutwfc                        60 ##energy cutoff for wave functions
ecutrho                        240 ##energy cutoff for charge density and potential
erf_ecut                       0 ##the value of the constant energy cutoff
erf_height                     0 ##the height of the energy step for reciprocal vectors
erf_sigma                      0.1 ##the width of the energy step for reciprocal vectors
fft_mode                       0 ##mode of FFTW
pw_diag_nmax                   50 #max iteration number for cg
diago_cg_prec                  1 #diago_cg_prec
pw_diag_thr                    0.01 #threshold for eigenvalues is cg electron iterations
scf_thr                        1e-07 #charge density error
scf_thr_type                   1 #type of the criterion of scf_thr, 1: reci drho for pw, 2: real drho for lcao
init_wfc                       atomic #start wave functions are from 'atomic', 'atomic+random', 'random' or 'file'
init_chg                       atomic #start charge is from 'atomic' or file
chg_extrap                     atomic #atomic; first-order; second-order; dm:coefficients of SIA
out_chg                        0 #>0 output charge density for selected electron steps
out_pot                        0 #output realspace potential
out_wfc_pw                     0 #output wave functions
out_wfc_r                      0 #output wave functions in realspace
out_dos                        0 #output energy and dos
out_band                       0 #output energy and band structure (with precision 8)
out_proj_band                  0 #output projected band structure
restart_save                   0 #print to disk every step for restart
restart_load                   0 #restart from disk
read_file_dir                  auto #directory of files for reading
nx                             0 #number of points along x axis for FFT grid
ny                             0 #number of points along y axis for FFT grid
nz                             0 #number of points along z axis for FFT grid
ndx                            0 #number of points along x axis for FFT smooth grid
ndy                            0 #number of points along y axis for FFT smooth grid
ndz                            0 #number of points along z axis for FFT smooth grid
cell_factor                    1.2 #used in the construction of the pseudopotential tables
pw_seed                        1 #random seed for initializing wave functions

#Parameters (3.Stochastic DFT)
method_sto                     2 #1: slow and save memory, 2: fast and waste memory
npart_sto                      1 #Reduce memory when calculating Stochastic DOS
nbands_sto                     256 #number of stochstic orbitals
nche_sto                       100 #Chebyshev expansion orders
emin_sto                       0 #trial energy to guess the lower bound of eigen energies of the Hamitonian operator
emax_sto                       0 #trial energy to guess the upper bound of eigen energies of the Hamitonian operator
seed_sto                       0 #the random seed to generate stochastic orbitals
initsto_ecut                   0 #maximum ecut to init stochastic bands
initsto_freq                   0 #frequency to generate new stochastic orbitals when running md
cal_cond                       0 #calculate electronic conductivities
cond_che_thr                   1e-08 #control the error of Chebyshev expansions for conductivities
cond_dw                        0.1 #frequency interval for conductivities
cond_wcut                      10 #cutoff frequency (omega) for conductivities
cond_dt                        0.02 #t interval to integrate Onsager coefficiencies
cond_dtbatch                   0 #exp(iH*dt*cond_dtbatch) is expanded with Chebyshev expansion.
cond_smear                     1 #Smearing method for conductivities
cond_fwhm                      0.4 #FWHM for conductivities
cond_nonlocal                  1 #Nonlocal effects for conductivities

#Parameters (4.Relaxation)
ks_solver                      cg #cg; dav; lapack; genelpa; scalapack_gvx; cusolver
scf_nmax                       100 ##number of electron iterations
relax_nmax                     1 #number of ion iteration steps
out_stru                       0 #output the structure files after each ion step
force_thr                      0.001 #force threshold, unit: Ry/Bohr
force_thr_ev                   0.0257112 #force threshold, unit: eV/Angstrom
force_thr_ev2                  0 #force invalid threshold, unit: eV/Angstrom
relax_cg_thr                   0.5 #threshold for switching from cg to bfgs, unit: eV/Angstrom
stress_thr                     0.5 #stress threshold
press1                         0 #target pressure, unit: KBar
press2                         0 #target pressure, unit: KBar
press3                         0 #target pressure, unit: KBar
relax_bfgs_w1                  0.01 #wolfe condition 1 for bfgs
relax_bfgs_w2                  0.5 #wolfe condition 2 for bfgs
relax_bfgs_rmax                0.8 #maximal trust radius, unit: Bohr
relax_bfgs_rmin                1e-05 #minimal trust radius, unit: Bohr
relax_bfgs_init                0.5 #initial trust radius, unit: Bohr
cal_stress                     0 #calculate the stress or not
fixed_axes                     None #which axes are fixed
fixed_ibrav                    0 #whether to preseve lattice type during relaxation
fixed_atoms                    0 #whether to preseve direct coordinates of atoms during relaxation
relax_method                   cg #bfgs; sd; cg; cg_bfgs;
relax_new                      1 #whether to use the new relaxation method
relax_scale_force              0.5 #controls the size of the first CG step if relax_new is true
out_level                      ie #ie(for electrons); i(for ions);
out_dm                         0 #>0 output density matrix
out_bandgap                    0 #if true, print out bandgap
use_paw                        0 #whether to use PAW in pw calculation
deepks_out_labels              0 #>0 compute descriptor for deepks
deepks_scf                     0 #>0 add V_delta to Hamiltonian
deepks_bandgap                 0 #>0 for bandgap label
deepks_out_unittest            0 #if set 1, prints intermediate quantities that shall be used for making unit test
deepks_model                    #file dir of traced pytorch model: 'model.ptg

#Parameters (5.LCAO)
basis_type                     pw #PW; LCAO in pw; LCAO
gamma_only                     0 #Only for localized orbitals set and gamma point. If set to 1, a fast algorithm is used
search_radius                  -1 #input search radius (Bohr)
search_pbc                     1 #input periodic boundary condition
lcao_ecut                      0 #energy cutoff for LCAO
lcao_dk                        0.01 #delta k for 1D integration in LCAO
lcao_dr                        0.01 #delta r for 1D integration in LCAO
lcao_rmax                      30 #max R for 1D two-center integration table
out_mat_hs                     0 #output H and S matrix (with precision 8)
out_mat_hs2                    0 #output H(R) and S(R) matrix
out_mat_dh                     0 #output of derivative of H(R) matrix
out_mat_xc                     0 #output exchange-correlation matrix in KS-orbital representation
out_interval                   1 #interval for printing H(R) and S(R) matrix during MD
out_app_flag                   1 #whether output r(R), H(R), S(R), T(R), and dH(R) matrices in an append manner during MD
out_mat_t                      0 #output T(R) matrix
out_element_info               0 #output (projected) wavefunction of each element
out_mat_r                      0 #output r(R) matrix
out_wfc_lcao                   0 #ouput LCAO wave functions, 0, no output 1: text, 2: binary
bx                             1 #division of an element grid in FFT grid along x
by                             1 #division of an element grid in FFT grid along y
bz                             1 #division of an element grid in FFT grid along z

#Parameters (6.Smearing)
smearing_method                gauss #type of smearing_method: gauss; fd; fixed; mp; mp2; mv
smearing_sigma                 0.015 #energy range for smearing

#Parameters (7.Charge Mixing)
mixing_type                    broyden #plain; pulay; broyden
mixing_beta                    0.8 #mixing parameter: 0 means no new charge
mixing_ndim                    8 #mixing dimension in pulay or broyden
mixing_restart                 0 #threshold to restart mixing during SCF
mixing_gg0                     1 #mixing parameter in kerker
mixing_beta_mag                -10 #mixing parameter for magnetic density
mixing_gg0_mag                 0 #mixing parameter in kerker
mixing_gg0_min                 0.1 #the minimum kerker coefficient
mixing_angle                   -10 #angle mixing parameter for non-colinear calculations
mixing_tau                     0 #whether to mix tau in mGGA calculation
mixing_dftu                    0 #whether to mix locale in DFT+U calculation
mixing_dmr                     0 #whether to mix real-space density matrix

#Parameters (8.DOS)
dos_emin_ev                    -15 #minimal range for dos
dos_emax_ev                    15 #maximal range for dos
dos_edelta_ev                  0.01 #delta energy for dos
dos_scale                      0.01 #scale dos range by
dos_sigma                      0.07 #gauss b coefficeinet(default=0.07)
dos_nche                       100 #orders of Chebyshev expansions for dos

#Parameters (9.Molecular dynamics)
md_type                        nvt #choose ensemble
md_thermostat                  nhc #choose thermostat
md_nstep                       10 #md steps
md_dt                          1 #time step
md_tchain                      1 #number of Nose-Hoover chains
md_tfirst                      -1 #temperature first
md_tlast                       -1 #temperature last
md_dumpfreq                    1 #The period to dump MD information
md_restartfreq                 5 #The period to output MD restart information
md_seed                        -1 #random seed for MD
md_prec_level                  0 #precision level for vc-md
ref_cell_factor                1 #construct a reference cell bigger than the initial cell
md_restart                     0 #whether restart
lj_rcut                        8.5 #cutoff radius of LJ potential
lj_epsilon                     0.01032 #the value of epsilon for LJ potential
lj_sigma                       3.405 #the value of sigma for LJ potential
pot_file                       graph.pb #the filename of potential files for CMD such as DP
msst_direction                 2 #the direction of shock wave
msst_vel                       0 #the velocity of shock wave
msst_vis                       0 #artificial viscosity
msst_tscale                    0.01 #reduction in initial temperature
msst_qmass                     -1 #mass of thermostat
md_tfreq                       0 #oscillation frequency, used to determine qmass of NHC
md_damp                        1 #damping parameter (time units) used to add force in Langevin method
md_nraise                      1 #parameters used when md_type=nvt
cal_syns                       0 #calculate asynchronous overlap matrix to output for Hefei-NAMD
dmax                           0.01 #maximum displacement of all atoms in one step (bohr)
md_tolerance                   100 #tolerance for velocity rescaling (K)
md_pmode                       iso #NPT ensemble mode: iso, aniso, tri
md_pcouple                     none #whether couple different components: xyz, xy, yz, xz, none
md_pchain                      1 #num of thermostats coupled with barostat
md_pfirst                      -1 #initial target pressure
md_plast                       -1 #final target pressure
md_pfreq                       0 #oscillation frequency, used to determine qmass of thermostats coupled with barostat
dump_force                     1 #output atomic forces into the file MD_dump or not
dump_vel                       1 #output atomic velocities into the file MD_dump or not
dump_virial                    1 #output lattice virial into the file MD_dump or not

#Parameters (10.Electric field and dipole correction)
efield_flag                    0 #add electric field
dip_cor_flag                   0 #dipole correction
efield_dir                     2 #the direction of the electric field or dipole correction
efield_pos_max                 -1 #position of the maximum of the saw-like potential along crystal axis efield_dir
efield_pos_dec                 -1 #zone in the unit cell where the saw-like potential decreases
efield_amp                     0 #amplitude of the electric field

#Parameters (11.Gate field)
gate_flag                      0 #compensating charge or not
zgate                          0.5 #position of charged plate
relax                          0 #allow relaxation along the specific direction
block                          0 #add a block potential or not
block_down                     0.45 #low bound of the block
block_up                       0.55 #high bound of the block
block_height                   0.1 #height of the block

#Parameters (12.Test)
out_alllog                     0 #output information for each processor, when parallel
nurse                          0 #for coders
colour                         0 #for coders, make their live colourful
t_in_h                         1 #calculate the kinetic energy or not
vl_in_h                        1 #calculate the local potential or not
vnl_in_h                       1 #calculate the nonlocal potential or not
vh_in_h                        1 #calculate the hartree potential or not
vion_in_h                      1 #calculate the local ionic potential or not
test_force                     0 #test the force
test_stress                    0 #test the force
test_skip_ewald                0 #skip ewald energy

#Parameters (13.vdW Correction)
vdw_method                     none #the method of calculating vdw (none ; d2 ; d3_0 ; d3_bj
vdw_s6                         default #scale parameter of d2/d3_0/d3_bj
vdw_s8                         default #scale parameter of d3_0/d3_bj
vdw_a1                         default #damping parameter of d3_0/d3_bj
vdw_a2                         default #damping parameter of d3_bj
vdw_d                          20 #damping parameter of d2
vdw_abc                        0 #third-order term?
vdw_C6_file                    default #filename of C6
vdw_C6_unit                    Jnm6/mol #unit of C6, Jnm6/mol or eVA6
vdw_R0_file                    default #filename of R0
vdw_R0_unit                    A #unit of R0, A or Bohr
vdw_cutoff_type                radius #expression model of periodic structure, radius or period
vdw_cutoff_radius              default #radius cutoff for periodic structure
vdw_radius_unit                Bohr #unit of radius cutoff for periodic structure
vdw_cn_thr                     40 #radius cutoff for cn
vdw_cn_thr_unit                Bohr #unit of cn_thr, Bohr or Angstrom
vdw_cutoff_period   3 3 3 #periods of periodic structure

#Parameters (14.exx)
exx_hybrid_alpha               default #fraction of Fock exchange in hybrid functionals
exx_hse_omega                  0.11 #range-separation parameter in HSE functional
exx_separate_loop              1 #if 1, a two-step method is employed, else it will start with a GGA-Loop, and then Hybrid-Loop
exx_hybrid_step                100 #the maximal electronic iteration number in the evaluation of Fock exchange
exx_mixing_beta                1 #mixing_beta for outer-loop when exx_separate_loop=1
exx_lambda                     0.3 #used to compensate for divergence points at G=0 in the evaluation of Fock exchange using lcao_in_pw method
exx_real_number                0 #exx calculated in real or complex
exx_pca_threshold              0.0001 #threshold to screen on-site ABFs in exx
exx_c_threshold                0.0001 #threshold to screen C matrix in exx
exx_v_threshold                0.1 #threshold to screen C matrix in exx
exx_dm_threshold               0.0001 #threshold to screen density matrix in exx
exx_cauchy_threshold           1e-07 #threshold to screen exx using Cauchy-Schwartz inequality
exx_c_grad_threshold           0.0001 #threshold to screen nabla C matrix in exx
exx_v_grad_threshold           0.1 #threshold to screen nabla V matrix in exx
exx_cauchy_force_threshold     1e-07 #threshold to screen exx force using Cauchy-Schwartz inequality
exx_cauchy_stress_threshold    1e-07 #threshold to screen exx stress using Cauchy-Schwartz inequality
exx_ccp_rmesh_times            default #how many times larger the radial mesh required for calculating Columb potential is to that of atomic orbitals
exx_opt_orb_lmax               0 #the maximum l of the spherical Bessel functions for opt ABFs
exx_opt_orb_ecut               0 #the cut-off of plane wave expansion for opt ABFs
exx_opt_orb_tolerence          0 #the threshold when solving for the zeros of spherical Bessel functions for opt ABFs

#Parameters (16.tddft)
td_force_dt                    0.02 #time of force change
td_vext                        0 #add extern potential or not
td_vext_dire                   1 #extern potential direction
out_dipole                     0 #output dipole or not
out_efield                     0 #output dipole or not
out_current                    0 #output current or not
ocp                            0 #change occupation or not
ocp_set                         #set occupation

#Parameters (17.berry_wannier)
berry_phase                    0 #calculate berry phase or not
gdir                           3 #calculate the polarization in the direction of the lattice vector
towannier90                    0 #use wannier90 code interface or not
nnkpfile                       seedname.nnkp #the wannier90 code nnkp file name
wannier_spin                   up #calculate spin in wannier90 code interface
wannier_method                 1 #different implementation methods under Lcao basis set
out_wannier_mmn                1 #output .mmn file or not
out_wannier_amn                1 #output .amn file or not
out_wannier_unk                0 #output UNK. file or not
out_wannier_eig                1 #output .eig file or not
out_wannier_wvfn_formatted     1 #output UNK. file in text format or in binary format

#Parameters (18.implicit_solvation)
imp_sol                        0 #calculate implicit solvation correction or not
eb_k                           80 #the relative permittivity of the bulk solvent
tau                            1.0798e-05 #the effective surface tension parameter
sigma_k                        0.6 # the width of the diffuse cavity
nc_k                           0.00037 # the cut-off charge density

#Parameters (19.orbital free density functional theory)
of_kinetic                     wt #kinetic energy functional, such as tf, vw, wt
of_method                      tn #optimization method used in OFDFT, including cg1, cg2, tn (default)
of_conv                        energy #the convergence criterion, potential, energy (default), or both
of_tole                        1e-06 #tolerance of the energy change (in Ry) for determining the convergence, default=2e-6 Ry
of_tolp                        1e-05 #tolerance of potential for determining the convergence, default=1e-5 in a.u.
of_tf_weight                   1 #weight of TF KEDF
of_vw_weight                   1 #weight of vW KEDF
of_wt_alpha                    0.833333 #parameter alpha of WT KEDF
of_wt_beta                     0.833333 #parameter beta of WT KEDF
of_wt_rho0                     0 #the average density of system, used in WT KEDF, in Bohr^-3
of_hold_rho0                   0 #If set to 1, the rho0 will be fixed even if the volume of system has changed, it will be set to 1 automaticly if of_wt_rho0 is not zero
of_lkt_a                       1.3 #parameter a of LKT KEDF
of_full_pw                     1 #If set to 1, ecut will be ignored when collect planewaves, so that all planewaves will be used
of_full_pw_dim                 0 #If of_full_pw = true, dimention of FFT is testricted to be (0) either odd or even; (1) odd only; (2) even only
of_read_kernel                 0 #If set to 1, the kernel of WT KEDF will be filled from file of_kernel_file, not from formula. Only usable for WT KEDF
of_kernel_file                 WTkernel.txt #The name of WT kernel file.

#Parameters (20.dft+u)
dft_plus_u                     0 #1/2:new/old DFT+U correction method; 0: standard DFT calcullation(default)
yukawa_lambda                  -1 #default:0.0
yukawa_potential               0 #default: false
omc                            0 #the mode of occupation matrix control
onsite_radius                  0 #radius of the sphere for onsite projection (Bohr)
hubbard_u           0 #Hubbard Coulomb interaction parameter U(ev)
orbital_corr        -1 #which correlated orbitals need corrected ; d:2 ,f:3, do not need correction:-1

#Parameters (21.spherical bessel)
bessel_nao_ecut                60.000000 #energy cutoff for spherical bessel functions(Ry)
bessel_nao_tolerence           1e-12 #tolerence for spherical bessel root
bessel_nao_rcut                6 #radial cutoff for spherical bessel functions(a.u.)
bessel_nao_smooth              1 #spherical bessel smooth or not
bessel_nao_sigma               0.1 #spherical bessel smearing_sigma
bessel_descriptor_lmax         2 #lmax used in generating spherical bessel functions
bessel_descriptor_ecut         60.000000 #energy cutoff for spherical bessel functions(Ry)
bessel_descriptor_tolerence    1e-12 #tolerence for spherical bessel root
bessel_descriptor_rcut         6 #radial cutoff for spherical bessel functions(a.u.)
bessel_descriptor_smooth       1 #spherical bessel smooth or not
bessel_descriptor_sigma        0.1 #spherical bessel smearing_sigma

#Parameters (22.non-collinear spin-constrained DFT)
sc_mag_switch                  0 #0: no spin-constrained DFT; 1: constrain atomic magnetization
decay_grad_switch              0 #switch to control gradient break condition
sc_thr                         1e-06 #Convergence criterion of spin-constrained iteration (RMS) in uB
nsc                            100 #Maximal number of spin-constrained iteration
nsc_min                        2 #Minimum number of spin-constrained iteration
sc_scf_nmin                    2 #Minimum number of outer scf loop before initializing lambda loop
alpha_trial                    0.01 #Initial trial step size for lambda in eV/uB^2
sccut                          3 #Maximal step size for lambda in eV/uB
sc_file                        none #file name for parameters used in non-collinear spin-constrained DFT (json format)

#Parameters (23.Quasiatomic Orbital analysis)
qo_switch                      0 #0: no QO analysis; 1: QO analysis
qo_basis                       szv #type of QO basis function: hydrogen: hydrogen-like basis, pswfc: read basis from pseudopotential
qo_thr                         1e-06 #accuracy for evaluating cutoff radius of QO basis function
"""

