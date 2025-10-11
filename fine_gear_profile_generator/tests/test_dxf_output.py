import unittest
import os
import shutil

from fine_gear_profile_generator.core import geometry_generator, models
from fine_gear_profile_generator.io import dxf_exporter

class TestDxfOutput(unittest.TestCase):

    def setUp(self):
        """Set up parameters and a temporary directory for test files."""
        self.temp_dir = "temp_test_output"
        os.makedirs(self.temp_dir, exist_ok=True)

        segmentation = models.SegmentationSettings(involute=15, edge=15, root_round=15)
        driver_spec = models.GearSpec(teeth=18, profile_shift=0.2)
        driven_spec = models.GearSpec(teeth=36, profile_shift=0.0)

        self.gear_pair_params = models.GearPairParameters(
            module=1.0,
            pressure_angle_deg=20.0,
            backlash_factor=0.05,
            addendum_factor=1.0,
            dedendum_factor=1.25,
            hob_edge_radius=0.2,
            tooth_edge_radius=0.1,
            driver=driver_spec,
            driven=driven_spec,
            segmentation=segmentation,
            root_fillet_method='rack_trochoid'
        )

    def tearDown(self):
        """Remove the temporary directory and its contents after the test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_dxf_file_is_created(self):
        """
        Tests that the DXF exporter function runs and creates a non-empty file
        at the expected location.
        """
        # Generate the geometry for both gears
        g1_profile, g1_teeth, g1_pitch, g1_align, g1_status = geometry_generator.generate_tooth_profile(
            params=self.gear_pair_params, gear_type='driver'
        )
        g2_profile, g2_teeth, g2_pitch, g2_align, g2_status = geometry_generator.generate_tooth_profile(
            params=self.gear_pair_params, gear_type='driven'
        )

        # Define parameters for the exporter
        center_dist = 27.0  # A typical value for this gear pair
        x_offset = 0.0
        y_offset = 0.0

        # Wrap the raw data in GearProfileGeometry objects
        gear1_profile_geom = models.GearProfileGeometry(
            profile=g1_profile,
            teeth=int(g1_teeth),
            pitch_angle=g1_pitch,
            alignment_angle=g1_align,
            undercut_status=g1_status
        )
        gear2_profile_geom = models.GearProfileGeometry(
            profile=g2_profile,
            teeth=int(g2_teeth),
            pitch_angle=g2_pitch,
            alignment_angle=g2_align,
            undercut_status=g2_status
        )

        # Call the DXF exporter
        dxf_exporter.export_gear_pair_to_dxf(
            self.temp_dir,
            gear1_profile_geom,
            gear2_profile_geom,
            center_dist,
            x_offset,
            y_offset
        )

        # Check if the file was created
        expected_filepath = os.path.join(self.temp_dir, 'Result_Gear_Pair.dxf')
        self.assertTrue(os.path.exists(expected_filepath), "DXF file was not created.")

        # Check if the file is not empty
        self.assertTrue(os.path.getsize(expected_filepath) > 0, "DXF file is empty.")

if __name__ == '__main__':
    unittest.main()