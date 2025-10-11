import sys
import os

# Add the project root to the Python path to allow for absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
sys.path.insert(0, project_root)

from fine_gear_profile_generator.core import gear_core
from fine_gear_profile_generator.core.models import GearPairParameters, GearSpec, SegmentationSettings, ShaperCutterParameters
from fine_gear_profile_generator.utils import config_manager

def run_debug():
    """
    Simulates a call to the gear generation core with shaper cutter options
    to reproduce the error without a GUI.
    """
    print("--- Starting Debug Script for Shaper Cutter Error ---")

    try:
        # Load default configurations
        config = config_manager.load_app_config()
        defaults = config_manager.get_defaults(config)
        shaper_defaults = config.get('shaper_cutter_defaults', {})

        # 1. Create parameter objects based on defaults
        segmentation = SegmentationSettings(
            involute=defaults.get('seg_involute'),
            edge=defaults.get('seg_edge_r'),
            root_round=defaults.get('seg_root_r'),
        )
        driver = GearSpec(
            teeth=defaults.get('teeth_number_z'),
            profile_shift=defaults.get('offset_factor_x'),
        )
        driven = GearSpec(
            teeth=defaults.get('teeth_number_z2'),
            profile_shift=defaults.get('offset_factor_x2'),
        )
        shaper_params = ShaperCutterParameters(
            Pnd0=shaper_defaults.get('Pnd0'),
            n0=shaper_defaults.get('n0'),
            phi_n0_deg=shaper_defaults.get('phi_n0_deg'),
            psi0_deg=shaper_defaults.get('psi0_deg'),
            sn0=shaper_defaults.get('sn0'),
            da0=shaper_defaults.get('da0'),
            rho0=shaper_defaults.get('rho0'),
            delta0=shaper_defaults.get('delta0')
        )

        # 2. Assemble the main parameters object, forcing the shaper method
        params = GearPairParameters(
            module=defaults.get('module_m'),
            pressure_angle_deg=defaults.get('pressure_angle_alpha'),
            backlash_factor=defaults.get('backlash_factor_b'),
            addendum_factor=defaults.get('addendum_factor_a'),
            dedendum_factor=defaults.get('dedendum_factor_d'),
            hob_edge_radius=defaults.get('hob_edge_radius_c'),
            tooth_edge_radius=defaults.get('tooth_edge_radius_e'),
            driver=driver,
            driven=driven,
            segmentation=segmentation,
            root_fillet_method='shaper_trochoid', # Force the shaper option
            shaper_cutter=shaper_params
        )

        print("\nParameters being used:")
        print(params)

        # 3. Call the core function that is expected to fail
        print("\n--- Calling gear_core.generate_gear_pair() ---")
        result = gear_core.generate_gear_pair(params)
        print("\n--- Success! No error was raised. ---")
        print("Result:", result)

    except Exception as e:
        print(f"\n--- ERROR! An exception was caught: ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_debug()