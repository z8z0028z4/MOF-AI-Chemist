"""
XRD Calculator Worker
=====================
Standalone subprocess worker that computes theoretical powder XRD patterns
from CIF files using pymatgen. Designed to run in the pmtransformer tool
environment which has pymatgen installed.

Usage:
  python xrd_calculator.py --cif /path/to/structure.cif \
    [--wavelength 1.54184] [--max_two_theta 80.0] [--fwhm 0.1]

Outputs JSON to stdout on success, JSON error object on failure.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _clean_cif_file(cif_path: Path) -> None:
    """Comment out any leading non-blank, non-comment lines that appear
    before the first 'data_' keyword to prevent CIF parsers from crashing
    on non-standard metadata (e.g. JSON headers in GCMC/CoRE MOF DB CIFs).
    """
    try:
        with open(cif_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        modified = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.lower().startswith("data_"):
                break
            if stripped and not stripped.startswith("#"):
                lines[i] = "# " + line
                modified = True

        if modified:
            with open(cif_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to clean CIF file {cif_path}: {e}\n")


def _gaussian_profile(
    two_theta_values: list[float],
    intensities: list[float],
    fwhm: float,
    num_points: int = 1000,
    theta_min: float = 5.0,
    theta_max: float = 80.0,
) -> tuple[list[float], list[float]]:
    """Generate a continuous Gaussian-broadened XRD profile.

    Returns:
        (two_theta_list, intensity_list) - lists of equal length representing
        the continuous profile suitable for plotting.
    """
    import numpy as np

    sigma = fwhm / (2.0 * (2.0 * np.log(2.0)) ** 0.5)
    theta_range = np.linspace(theta_min, theta_max, num_points)
    profile = np.zeros(num_points)

    for two_theta, intensity in zip(two_theta_values, intensities):
        profile += intensity * np.exp(-0.5 * ((theta_range - two_theta) / sigma) ** 2)

    # Normalise to [0, 100]
    max_val = profile.max()
    if max_val > 0:
        profile = profile / max_val * 100.0

    return theta_range.tolist(), profile.tolist()


def calculate_xrd(
    cif_path: Path,
    wavelength: float = 1.54184,
    max_two_theta: float = 80.0,
    fwhm: float = 0.1,
) -> dict:
    """Calculate theoretical XRD pattern from a CIF file.

    Args:
        cif_path: Path to the CIF file.
        wavelength: X-ray wavelength in Angstroms (default: 1.54184, Cu K-alpha).
        max_two_theta: Maximum 2-theta angle in degrees.
        fwhm: Full Width at Half Maximum for Gaussian broadening.

    Returns:
        dict with keys: space_group, crystal_system, peaks, profile.
    """
    # Clean the CIF file first (handles CoRE MOF DB / GCMC headers)
    _clean_cif_file(cif_path)

    from pymatgen.core import Structure
    from pymatgen.analysis.diffraction.xrd import XRDCalculator
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    structure = Structure.from_file(str(cif_path))

    # Get symmetry information
    try:
        analyzer = SpacegroupAnalyzer(structure, symprec=0.1)
        symmetry_dataset = analyzer.get_symmetry_dataset()
        space_group_symbol = symmetry_dataset.international
        space_group_number = symmetry_dataset.number
        crystal_system = analyzer.get_crystal_system()
    except Exception:
        space_group_symbol = structure.get_space_group_info()[0]
        space_group_number = structure.get_space_group_info()[1]
        crystal_system = "unknown"

    # Calculate XRD pattern
    calc = XRDCalculator(wavelength=wavelength)
    pattern = calc.get_pattern(structure, two_theta_range=(5.0, max_two_theta))

    # Extract peaks
    peaks = []
    two_theta_vals = pattern.x.tolist()
    intensities = pattern.y.tolist()
    # d_hkls is a plain Python list of np.float64 scalars (not a numpy array)
    d_hkl_list = [float(d) for d in pattern.d_hkls]
    for two_theta, intensity, hkl_objs, d_spacing in zip(
        two_theta_vals,
        intensities,
        pattern.hkls,
        d_hkl_list,
    ):
        # hkl_objs is a list of dicts: [{'hkl': (h, k, l), 'multiplicity': n}, ...]
        hkl_labels = []
        for hkl_info in hkl_objs:
            hkl_tuple = hkl_info["hkl"]
            h, k, l = int(hkl_tuple[0]), int(hkl_tuple[1]), int(hkl_tuple[2])
            hkl_labels.append(f"({h}{k}{l})")
        peaks.append(
            {
                "two_theta": round(two_theta, 4),
                "intensity": round(intensity, 2),
                "hkl": ", ".join(hkl_labels),
                "d_spacing": round(d_spacing, 4),
            }
        )

    # Sort by intensity descending
    peaks.sort(key=lambda p: p["intensity"], reverse=True)

    # Generate continuous profile for plotting
    profile_x, profile_y = _gaussian_profile(
        two_theta_vals,
        intensities,
        fwhm=fwhm,
        theta_min=5.0,
        theta_max=max_two_theta,
    )

    return {
        "space_group": space_group_symbol,
        "space_group_number": space_group_number,
        "crystal_system": crystal_system,
        "wavelength": wavelength,
        "num_peaks": len(peaks),
        "peaks": peaks,
        "profile": {
            "two_theta": [round(v, 4) for v in profile_x],
            "intensity": [round(v, 4) for v in profile_y],
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Calculate theoretical XRD pattern from CIF")
    parser.add_argument("--cif", required=True, help="Path to the CIF file")
    parser.add_argument("--wavelength", type=float, default=1.54184,
                        help="X-ray wavelength in Angstroms (default: 1.54184, Cu K-alpha)")
    parser.add_argument("--max_two_theta", type=float, default=80.0,
                        help="Maximum 2-theta angle in degrees")
    parser.add_argument("--fwhm", type=float, default=0.1,
                        help="Full Width at Half Maximum for Gaussian broadening")
    args = parser.parse_args()

    cif_path = Path(args.cif)
    if not cif_path.exists():
        error = {"error": f"CIF file not found: {args.cif}"}
        print(json.dumps(error))
        sys.exit(1)

    try:
        result = calculate_xrd(
            cif_path=cif_path,
            wavelength=args.wavelength,
            max_two_theta=args.max_two_theta,
            fwhm=args.fwhm,
        )
        print(json.dumps(result))
    except Exception as e:
        error = {"error": str(e), "type": type(e).__name__}
        print(json.dumps(error))
        sys.exit(1)


if __name__ == "__main__":
    main()
