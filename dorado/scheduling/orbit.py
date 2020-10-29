"""Spacecraft orbit."""
from importlib import resources

from astropy.coordinates import EarthLocation
from astropy.time import Time
from astropy import units as u
import numpy as np
import skyfield.api

from . import data

__all__ = ('get_position', 'orbital_period', 'exposure_time',
           'exposures_per_orbit')


# Load two-line element for satellite (use Swift's orbit)
with resources.path(data, 'orbits.txt') as path:
    satellite = skyfield.api.load.tle(str(path))['SWIFT']

timescale = skyfield.api.load.timescale()

orbital_period = 2 * np.pi / satellite.model.no * u.minute
exposure_time = 10 * u.minute
time_steps_per_exposure = 10
time_step_duration = exposure_time / time_steps_per_exposure
exposures_per_orbit = int(
    (orbital_period / exposure_time).to_value(u.dimensionless_unscaled))
time_steps = int(
    (orbital_period / time_step_duration).to_value(u.dimensionless_unscaled))


def get_position(time):
    """Get the position of the satellite.

    Parameters
    ----------
    time : astropy.time.Time, skyfield.timelib.Time
        The time of the observation.

    Returns
    -------
    earth_location : astropy.coordinates.EarthLocation
        The geocentric position of the satellite.
    """
    if isinstance(time, Time):
        time = timescale.from_astropy(time)
    position = satellite.at(time).position
    return EarthLocation.from_geocentric(*position.to(u.meter))
