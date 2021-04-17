#
# Copyright © 2020 United States Government as represented by the Administrator
# of the National Aeronautics and Space Administration. No copyright is claimed
# in the United States under Title 17, U.S. Code. All Other Rights Reserved.
#
# SPDX-License-Identifier: NASA-1.3
#
"""Spacecraft survey model."""
from importlib import resources

import astroplan
from astroplan import is_event_observable, Observer
from ligo.skymap.util import progress_map
from astropy import units as u
from astropy.coordinates import ICRS
from astropy_healpix import HEALPix
import numpy as np

from .constraints import OrbitNightConstraint
from .constraints.earth_limb import EarthLimbConstraint
from .constraints.radiation import TrappedParticleFluxConstraint
from .orbit import Orbit
from .fov import FOV

visibility_constraints = [
    # SAA constraint, modeled after Fermi:
    # flux of particles with energies ≥ 20 MeV is ≤ 1 cm^-2 s^-1
    TrappedParticleFluxConstraint(flux=1*u.cm**-2*u.s**-1, energy=20*u.MeV,
                                  particle='p', solar='max'),
    # 28° from the Earth's limb
    EarthLimbConstraint(28 * u.deg),
    # 46° from the Sun
    astroplan.SunSeparationConstraint(46 * u.deg),
    # 23° from the Moon
    astroplan.MoonSeparationConstraint(23 * u.deg)
    # 10° from Galactic plane
    # astroplan.GalacticLatitudeConstraint(10 * u.deg)
]


class SurveyModel():
    def __init__(self,
                 satfile='orbits.txt',
                 exposure_time=10 * u.minute,
                 time_steps_per_exposure=10,
                 number_of_orbits=1,
                 ):

        self.satfile = satfile
        self.exposure_time = exposure_time
        self.time_steps_per_exposure = time_steps_per_exposure
        self.number_of_orbits = number_of_orbits

        # Load two-line element for satellite.
        # This is for Aqua, an Earth observing satellite in a low-Earth
        # sun-synchronous orbit that happens to be similar to what might
        # be appropriate for Dorado.
        with resources.path('dorado.scheduling.data', satfile) as path:
            self.orbit = Orbit(path)

        self.time_step_duration = exposure_time / time_steps_per_exposure

        self.exposures_per_orbit = int(
            (self.orbit.period /
             exposure_time).to_value(u.dimensionless_unscaled))
        self.time_steps = int(
            (self.number_of_orbits * self.orbit.period /
             self.time_step_duration).to_value(u.dimensionless_unscaled))

    def is_night(self, time):
        """Determine if the spacecraft is in orbit night.

        Parameters
        ----------
        time : :class:`astropy.time.Time`
            The time of the observation.

        Returns
        -------
        bool, :class:`np.ndarray`
            True when the spacecraft is in orbit night, False otherwise.
        """
        return OrbitNightConstraint().compute_constraint(
            time, Observer(self.orbit(time).earth_location))

    def _observable(self, time, location):
        return is_event_observable(
            visibility_constraints,
            Observer(location),
            self.centers,
            time
        ).ravel()

    def get_field_of_regard(self, times, jobs=None):
        return np.asarray(list(progress_map(
            self._observable, times, self.orbit(times).earth_location,
            jobs=jobs)))


class TilingModel(SurveyModel):
    def __init__(self,
                 satfile='orbits.txt',
                 exposure_time=10 * u.minute,
                 time_steps_per_exposure=10,
                 number_of_orbits=1,
                 field_of_view=7.1 * u.deg,
                 centers=None
                 ):

        self.healpix = HEALPix(nside=32, order='nested', frame=ICRS())
        """Base HEALpix resolution for all calculations."""

        if centers is None:
            self.centers = self.healpix.healpix_to_skycoord(
                np.arange(self.healpix.npix))
            """Centers of pointings."""
        else:
            self.centers = centers

        self.rolls = np.linspace(0, 90, 9, endpoint=False) * u.deg
        """Roll angle grid."""

        self.fov = FOV.from_rectangle(field_of_view)
        """Square field of view."""

        super().__init__(satfile, exposure_time, time_steps_per_exposure,
                         number_of_orbits)
