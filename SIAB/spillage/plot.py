from SIAB.spillage.orbio import read_nao
import numpy as np
import matplotlib.pyplot as plt
import argparse
from matplotlib import rc
rc('font',**{'family':'sans-serif'})
#rc('text', usetex=True)

def plot_chi(chi, r, save=None):
    lmax = len(chi)-1
    nzeta = [len(chi_l) for chi_l in chi]

    fig, ax = plt.subplots(nrows=1, ncols=lmax+1, figsize=((lmax+1)*5, 4),
                           layout='tight', squeeze=False)
    
    for l, chi_l in enumerate(chi):
        for zeta, chi_lz in enumerate(chi_l):
            # adjust the sign so that the largest value is positive
            if chi_lz[np.argmax(np.abs(chi_lz))] < 0:
                chi_lz *= -1
    
            ax[0, l].plot(r, chi_lz, label='$\zeta=%i$'%(zeta))
    
        ax[0, l].legend(fontsize=16)
        ax[0, l].axhline(0, color='black', linestyle=':')
        ax[0, l].set_title('$l=%d$'%(l), fontsize=20)
        ax[0, l].set_xlim([0, r[-1]])

    if save is not None:
        plt.savefig(save)


def plot_orbfile(orbfile, save=None):
    nao = read_nao(orbfile)
    r = nao['dr'] * np.arange(nao['nr'])
    chi = nao['chi']
    plot_chi(chi, r, save=save)

def main():
    # parse command line arguments, the -i accepts the filename of the orbital
    parser = argparse.ArgumentParser(description='Plot the radial functions of an orbital')
    parser.add_argument('-i', '--input', help='The filename of the orbital')
    parser.add_argument('-o', '--output', help='The filename of the output plot')
    args = parser.parse_args()

    plot_orbfile(args.input, save=args.output)
    plt.show()

if __name__ == '__main__':

    #plot_orbfile('/home/zuxin/tmp/nao/v2.0/SG15-Version1p0__AllOrbitals-Version2p0/73_Ta_TZDP/Ta_gga_10au_100Ry_6s3p3d3f2g.orb')
    #plot_orbfile('./Fe_gga_10au_100Ry_4s2p2d1f.orb')
    #plot_orbfile('/home/zuxin/tmp/nao/v2.0/SG15-Version1p0__AllOrbitals-Version2p0/26_Fe_DZP/Fe_gga_10au_100Ry_4s2p2d1f.orb')
    #plot_orbfile('/home/zuxin/abacus-community/abacus_orbital_generation/SIAB/spillage/jy_normalized_7au_10Ry_7s6p6d.orb')
    #plot_orbfile('/home/zuxin/tmp/jy_vs_pw/jy/Si_gga_10au_100Ry_31s31p30d.orb')
    #plot_orbfile('/home/zuxin/abacus-community/abacus_orbital_generation/SIAB/spillage/jy_normalized_10au_10Ry_10s9p9d.orb')
    #plot_orbfile('/home/zuxin/abacus-community/abacus_orbital_generation/Si/Si_2s2p1d/7au_40Ry/Si_gga_40Ry_7au_2s2p1d.orb')
    #plot_orbfile('/home/zuxin/abacus-community/abacus_orbital_generation/Si/Si_3s3p2d/7au_40Ry/Si_gga_40Ry_7au_3s3p2d.orb')
    #plot_orbfile('/root/documents/simulation/orbgen/v3p0-test/Si_gga_10au_60Ry_2s2p1d.orb')
    plot_orbfile('/root/abacus-develop/numerical_orbitals/SG15-Version1p0__AllOrbitals-Version2p1/20240714/In_3s3p3d2f/10au_300.0Ry/In_gga_10au_300.0Ry_3s3p3d2f.orb')
    plt.show()

    pass

