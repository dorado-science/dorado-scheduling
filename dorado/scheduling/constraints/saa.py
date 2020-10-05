"""SAA constraints."""
from importlib import resources

from astropy.coordinates import EarthLocation
from astroplan import Constraint
from ligo.skymap.postprocess import simplify
import healpy as hp
import numpy as np

from .. import data

__all__ = ('OutsideEarthPolygonConstraint',
           'OutsideSouthAtlanticAnomalyConstraint')


class OutsideEarthPolygonConstraint(Constraint):

    def __init__(self, nside, poly):
        npix = hp.nside2npix(nside)
        ipix = hp.query_polygon(nside, poly.geocentric)
        self._nside = nside
        self._mask = np.ones(npix, dtype=np.bool)
        self._mask[ipix] = False

    def compute_constraint(self, times, observer=None, targets=None):
        ipix = hp.vec2pix(self._nside, *observer.location.geocentric)
        return self._mask[ipix]


class OutsideSouthAtlanticAnomalyConstraint(OutsideEarthPolygonConstraint):

    def __init__(self, nside):
        # Load Fermi SAA polygon
        with resources.open_binary(data, 'L_SAA_2008198.03') as f:
            lat, lon = np.loadtxt(f, delimiter='=', usecols=[1]).reshape(2, -1)
        poly = EarthLocation.from_geodetic(lon, lat)

        # Simplify polygon
        xyz = EarthLocation.from_geodetic(lon, lat).geocentric
        xyz /= np.sqrt(np.sum(np.square(xyz), 0))
        xyz = simplify(xyz.T, 0.1).T
        poly = EarthLocation.from_geocentric(*xyz)

        super().__init__(nside, poly)
