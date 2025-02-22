"""Test symmetrization of Wannier models"""
from wannierberri.symmetry.sym_wann import _dict_to_matrix, _matrix_to_dict, _get_H_select, _rotate_matrix
import numpy as np
import pytest
from pytest import approx

import wannierberri as wberri
from wannierberri import calculators as calc

from .common_systems import (
    Efermi_GaAs,
    Efermi_Fe,
    Efermi_Mn3Sn,
    Efermi_Te_sparse,
)


from .test_run import (
    calculators_GaAs_internal,
    calculators_Te,
)




@pytest.fixture
def check_symmetry(check_run):
    def _inner(system,
            calculators={},
            precision=1e-7,
            extra_precision={},
            **kwargs,
            ):
        kwargs['do_not_compare'] = True
        result_irr_k = check_run(system, use_symmetry=True, calculators=calculators, suffix="irr_k", **kwargs)
        result_full_k = check_run(system, use_symmetry=False, calculators=calculators, suffix="full_k", **kwargs)
        print(calculators.keys(), result_irr_k.results.keys(), result_full_k.results.keys())

        for quant in calculators.keys():
            diff = abs(result_full_k.results[quant].data - result_irr_k.results[quant].data).max()
            try:
                prec = extra_precision[quant]
            except KeyError:
                prec = precision
            if prec < 0:
                req_precision = -prec * (abs(result_full_k.results[quant].data) + abs(result_irr_k.results[quant].data)).max() / 2
            else:
                req_precision = prec
            assert diff <= req_precision, (
                f"data of {quant} with and without symmetries give a maximal "
                f"absolute difference of {diff} greater than the required precision {req_precision}"
            )
    return _inner




def test_shiftcurrent_symmetry(check_symmetry, system_GaAs_sym_tb_wcc):
    """Test shift current with and without symmetry is the same for a symmetrized system"""
    param = dict(
        Efermi=Efermi_GaAs,
        omega=np.arange(1.0, 5.1, 0.5),
        smr_fixed_width=0.2,
        smr_type='Gaussian',
        kBT=0.01,
    )
    calculators = dict(
        shift_current=calc.dynamic.ShiftCurrent(sc_eta=0.1, **param),
    )

    check_symmetry(system=system_GaAs_sym_tb_wcc,
                   grid_param=dict(NK=6, NKFFT=3),
                   calculators=calculators,
                   precision=1e-6
                    )




def test_Mn3Sn_sym_tb(check_symmetry, system_Mn3Sn_sym_tb_wcc):
    param = {'Efermi': Efermi_Mn3Sn}
    calculators = {}
    calculators.update({k: v(**param) for k, v in calculators_GaAs_internal.items()})
    calculators.update({
        'ahc_int': calc.static.AHC(Efermi=Efermi_Mn3Sn, kwargs_formula={"external_terms": False}),
        'ahc_ext': calc.static.AHC(Efermi=Efermi_Mn3Sn, kwargs_formula={"internal_terms": False}),
        'ahc': calc.static.AHC(Efermi=Efermi_Mn3Sn, kwargs_formula={"external_terms": True}),
    })
    check_symmetry(system=system_Mn3Sn_sym_tb_wcc, calculators=calculators)


@pytest.mark.parametrize("use_k_sym", [False, True])
@pytest.mark.parametrize("sym_method", ["old", "new"])
def test_Fe_sym_W90(check_run, system_Fe_sym_W90_wcc, system_Fe_sym_W90_wcc_new, compare_any_result, use_k_sym, sym_method):
    if sym_method == "old":
        system = system_Fe_sym_W90_wcc
    elif sym_method == "new":
        system = system_Fe_sym_W90_wcc_new
    else:
        raise ValueError("sym_method should be 'old' or 'new'")
    param = {'Efermi': Efermi_Fe}
    cals = {'ahc': calc.static.AHC,
            'Morb': calc.static.Morb,
            'spin': calc.static.Spin}
    calculators = {k: v(**param) for k, v in cals.items()}

    check_run(
        system,
        calculators,
        fout_name="berry_Fe_sym_W90",
        suffix="-run",
        use_symmetry=use_k_sym
    )
    cals = {'gyrotropic_Korb': calc.static.GME_orb_FermiSea,
            'berry_dipole': calc.static.BerryDipole_FermiSea,
            'gyrotropic_Kspin': calc.static.GME_spin_FermiSea}
    calculators = {k: v(**param) for k, v in cals.items()}
    check_run(
        system,
        calculators,
        fout_name="berry_Fe_sym_W90",
        precision=1e-8,
        suffix="-run",
        compare_zero=True,
        use_symmetry=use_k_sym
    )


@pytest.fixture
def checksym_Fe(check_run, compare_any_result, check_symmetry):
    def _inner(system, extra_calculators={}):
        param = {'Efermi': Efermi_Fe}
        cals = {'dos': calc.static.DOS,
                'cumdos': calc.static.CumDOS,
            'conductivity_ohmic': calc.static.Ohmic_FermiSea,
            'conductivity_ohmic_fsurf': calc.static.Ohmic_FermiSurf,
            'ahc': calc.static.AHC,
            'Morb': calc.static.Morb,
            'spin': calc.static.Spin}
        calculators = {k: v(**param) for k, v in cals.items()}
        calculators.update({
            'ahc_int': calc.static.AHC(Efermi=Efermi_Fe, kwargs_formula={"external_terms": False}),
            'ahc_ext': calc.static.AHC(Efermi=Efermi_Fe, kwargs_formula={"internal_terms": False}),
            'SHCryoo_static': calc.static.SHC(Efermi=Efermi_Fe, kwargs_formula={'spin_current_type': 'ryoo'})
        })
        calculators.update(extra_calculators)
        check_symmetry(system=system,
                       grid_param=dict(NK=6, NKFFT=3),
                   calculators=calculators,
                   precision=-1e-8
                    )
    return _inner


def test_Fe_new_wcc(system_Fe_sym_W90_wcc, checksym_Fe):
    checksym_Fe(system_Fe_sym_W90_wcc)


def test_Fe_new_wccFD(system_Fe_sym_W90_wcc_fd, checksym_Fe):
    extra_calculators = {}
    extra_calculators['SHCqiao_static'] = \
        wberri.calculators.static.SHC(Efermi=Efermi_Fe, kwargs_formula={'spin_current_type': 'qiao'})
    extra_calculators['SHCryoo_static'] = \
        wberri.calculators.static.SHC(Efermi=Efermi_Fe, kwargs_formula={'spin_current_type': 'ryoo'})
    extra_calculators['SHCryoo_simple'] = \
        wberri.calculators.static.SHC(Efermi=Efermi_Fe, kwargs_formula={'spin_current_type': 'simple'})
    checksym_Fe(system_Fe_sym_W90_wcc_fd, extra_calculators=extra_calculators)


def test_GaAs_sym_tb_zero(check_symmetry, check_run, system_GaAs_sym_tb_wcc, compare_any_result):
    param = {'Efermi': Efermi_GaAs}
    calculators = {}
    calculators.update({
        'berry_dipole': calc.static.BerryDipole_FermiSea(**param, kwargs_formula={"external_terms": True}),
        'gyrotropic_Korb': calc.static.GME_orb_FermiSea(Efermi=Efermi_GaAs, kwargs_formula={"external_terms": True}),
        'gyrotropic_Kspin': calc.static.GME_spin_FermiSea(Efermi=Efermi_GaAs),
        # 'gyrotropic_Kspin_fsurf':calc.static.GME_spin_FermiSurf(Efermi=Efermi_GaAs),
        # 'gyrotropic_Korb_test':calc.static.GME_orb_FermiSea_test(Efermi=Efermi_GaAs),
    })

    check_run(
        system_GaAs_sym_tb_wcc,
        {'ahc': calc.static.AHC(Efermi=Efermi_GaAs)},
        fout_name="berry_GaAs_sym_tb",
        precision=1e-5,
        compare_zero=True,
        suffix="sym-zero",
    )


def test_GaAs_random_zero(check_symmetry, check_run, system_random_GaAs_load_ws_sym, compare_any_result):
    param = {'Efermi': Efermi_GaAs}
    calculators = {}
    calculators.update({
        'berry_dipole': calc.static.BerryDipole_FermiSea(**param, kwargs_formula={"external_terms": True}),
        # 'gyrotropic_Korb': calc.static.GME_orb_FermiSea(Efermi=Efermi_GaAs, kwargs_formula={"external_terms": True}),
        'gyrotropic_Kspin': calc.static.GME_spin_FermiSea(Efermi=Efermi_GaAs),
        'ahc': calc.static.AHC(Efermi=Efermi_GaAs),
        # 'gyrotropic_Kspin_fsurf':calc.static.GME_spin_FermiSurf(Efermi=Efermi_GaAs),
        # 'gyrotropic_Korb_test':calc.static.GME_orb_FermiSea_test(Efermi=Efermi_GaAs),
    })

    check_run(
        system_random_GaAs_load_ws_sym,
        calculators,
        fout_name="berry_GaAs_sym_random",
        precision=2e-5,
        compare_zero=True,
        suffix="sym-zero",
    )


def test_GaAs_sym_tb(check_symmetry, system_GaAs_sym_tb_wcc):
    param = {'Efermi': Efermi_GaAs}
    calculators = {}
    calculators.update({k: v(**param) for k, v in calculators_GaAs_internal.items()})
    check_symmetry(system=system_GaAs_sym_tb_wcc, calculators=calculators)


def test_GaAs_random(check_symmetry, system_random_GaAs_load_ws_sym):
    system = system_random_GaAs_load_ws_sym
    param = {'Efermi': Efermi_GaAs}
    calculators = {}
    calculators.update({k: v(**param) for k, v in calculators_GaAs_internal.items()})
    param = dict(
        Efermi=Efermi_GaAs,
        omega=np.arange(1.0, 5.1, 0.5),
        smr_fixed_width=0.2,
        smr_type='Gaussian',
        kBT=0.01,
    )
    calculators.update({'SHC-ryoo': calc.dynamic.SHC(SHC_type='ryoo', **param)})
    check_symmetry(system=system, calculators=calculators,
                   extra_precision={"SHC-ryoo": 2e-7})


def test_GaAs_sym_tb_fail_convII(check_symmetry, system_GaAs_tb):
    with pytest.raises(NotImplementedError, match="Symmetrization is implemented only for convention I"):
        system_GaAs_tb.symmetrize(
            positions=np.array([[0.0, 0.0, 0.0], [0.25, 0.25, 0.25]]),
            atom_name=['Ga', 'As'],
            proj=['Ga:sp3', 'As:sp3'],
            soc=True,
            spin_ordering="block",
            method="old",)


def test_GaAs_dynamic_sym(check_run, system_GaAs_sym_tb_wcc, compare_any_result):
    "Test shift current and injection current"

    param = dict(
        Efermi=Efermi_GaAs,
        omega=np.arange(1.0, 5.1, 0.5),
        smr_fixed_width=0.2,
        smr_type='Gaussian',
        kBT=0.01,
    )
    calculators = dict(
        shift_current=calc.dynamic.ShiftCurrent(sc_eta=0.1, **param),
        injection_current=calc.dynamic.InjectionCurrent(**param),
        opt_conductivity=calc.dynamic.OpticalConductivity(**param)
    )

    result_full_k = check_run(
        system_GaAs_sym_tb_wcc,
        calculators,
        fout_name="dynamic_GaAs_sym",
        grid_param={
            'NK': [6, 6, 6],
            'NKFFT': [3, 3, 3]
        },
        use_symmetry=False,
        do_not_compare=True,
    )

    result_irr_k = check_run(
        system_GaAs_sym_tb_wcc,
        calculators,
        fout_name="dynamic_GaAs_sym",
        suffix="sym",
        suffix_ref="",
        grid_param={
            'NK': [6, 6, 6],
            'NKFFT': [3, 3, 3]
        },
        use_symmetry=True,
        do_not_compare=True,
    )


    assert result_full_k.results["shift_current"].data == approx(
        result_irr_k.results["shift_current"].data, abs=1e-6)

    assert result_full_k.results["injection_current"].data == approx(
        result_irr_k.results["injection_current"].data, abs=1e-6)

    assert result_full_k.results["opt_conductivity"].data == approx(
        result_irr_k.results["opt_conductivity"].data, abs=1e-7)



def test_Te_sparse(check_symmetry, system_Te_sparse):
    param = {'Efermi': Efermi_Te_sparse, 'Emax': 6.15, 'hole_like': True}
    calculators = {}
    for k, v in calculators_Te.items():
        par = {}
        par.update(param)
        if k not in ["dos", "cumdos"]:
            par["kwargs_formula"] = {"external_terms": False}
        calculators[k] = v(**par)


        check_symmetry(system=system_Te_sparse,
                       grid_param=dict(NK=(6, 6, 4), NKFFT=(3, 3, 2)),
                       calculators=calculators,
                       precision=-1e-8,
                extra_precision={"berry_dipole": 5e-7},
                    )


def test_Te_sparse_tetragrid(check_run, system_Te_sparse, compare_any_result):
    param = {'Efermi': Efermi_Te_sparse, "tetra": True, 'use_factor': False, 'Emax': 6.15, 'hole_like': True}
    calculators = {}
    for k, v in calculators_Te.items():
        par = {}
        par.update(param)
        if k not in ["dos", "cumdos"]:
            par["kwargs_formula"] = {"external_terms": False}
        calculators[k] = v(**par)

    grid = wberri.grid.GridTrigonal(system_Te_sparse, length=50, NKFFT=[3, 3, 2])

    check_run(
        system_Te_sparse,
        calculators,
        fout_name="berry_Te_sparse_tetragrid",
        use_symmetry=True,
        grid=grid,
        # temporarily weakened precision here. Will restrict it later with new data
        extra_precision={"berry_dipole": 3e-7},
        parameters_K={
            '_FF_antisym': True,
            '_CCab_antisym': True
        },
    )


def test_Te_sparse_tetragridH(check_run, system_Te_sparse, compare_any_result):
    param = {'Efermi': Efermi_Te_sparse, "tetra": True, 'use_factor': False}
    calculators = {}
    for k, v in calculators_Te.items():
        par = {}
        par.update(param)
        if k not in ["dos", "cumdos"]:
            par["kwargs_formula"] = {"external_terms": False}
        calculators[k] = v(**par)

    grid = wberri.grid.GridTrigonalH(system_Te_sparse, length=50, NKFFT=1, x=0.6)

    check_run(
        system_Te_sparse,
        calculators,
        fout_name="berry_Te_sparse_tetragridH",
        use_symmetry=True,
        grid=grid,
        # temporarily weakened precision here. Will restrict it later with new data
        extra_precision={"berry_dipole": 3e-7, "dos": 2e-8},
        parameters_K={
            '_FF_antisym': True,
            '_CCab_antisym': True
        },
    )


def test_KaneMele_sym(check_symmetry, system_KaneMele_odd_PythTB):
    param = {'Efermi': np.linspace(-4., 4., 21)}
    calculators = {}
    calculators.update({k: v(**param) for k, v in calculators_GaAs_internal.items()})
    calculators.update({
        'berry_dipole': calc.static.BerryDipole_FermiSea(**param, kwargs_formula={"external_terms": False}),
        'gyrotropic_Korb': calc.static.GME_orb_FermiSea(**param, kwargs_formula={"external_terms": False}),
        'gyrotropic_Kspin': calc.static.GME_spin_FermiSea(**param),
    })

    check_symmetry(system=system_KaneMele_odd_PythTB,
                   grid_param=dict(NK=(6, 6, 1), NKFFT=(3, 3, 1)),
                   calculators=calculators)



class AtomInfo():
    """fake AtomInfo for test"""

    def __init__(self, orbital_index):
        self.num_wann = sum(len(oi) for oi in orbital_index)
        self.orbital_index = orbital_index


def test_matrix_to_dict():
    wann_atom_info = [AtomInfo(n) for n in ([[1, 3], [5, 6]], [[0, 2, 4]])]
    num_wann = sum((at.num_wann for at in wann_atom_info))
    num_wann_atom = len(wann_atom_info)
    nRvec = 8
    ndimv = 2
    mat = np.random.random((num_wann, num_wann, nRvec) + (3,) * ndimv)
    H_select = _get_H_select(num_wann, num_wann_atom, wann_atom_info)
    dic = _matrix_to_dict(mat, H_select, wann_atom_info)
    mat_new = _dict_to_matrix(dic, H_select, nRvec, ndimv)
    assert mat_new == approx(mat, abs=1e-8)


def test_rotate_matrix():
    num_wann = 5
    L = np.random.random((num_wann, num_wann)) + 1j * np.random.random((num_wann, num_wann))
    R = np.random.random((num_wann, num_wann)) + 1j * np.random.random((num_wann, num_wann))
    for ndim in range(4):
        shape = (num_wann,) * 2 + (3,) * ndim
        X = np.random.random(shape) + 1j * np.random.random(shape)
        assert _rotate_matrix(X, L, R) == approx(np.einsum("lm,mn...,np->lp...", L, X, R))
