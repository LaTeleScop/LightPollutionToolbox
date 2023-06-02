# -*- coding: utf-8 -*-

"""
/***************************************************************************
 LightPollutionToolbox
                                 A QGIS plugin
 Light pollution indicators (focus on public lighting)
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-04-20
        copyright            : (C) 2020 by Mathieu Chailloux
        email                : mathieu@chailloux.org
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Mathieu Chailloux'
__date__ = '2020-04-20'
__copyright__ = '(C) 2020 by Mathieu Chailloux'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
import inspect
from PyQt5.QtGui import QIcon

from qgis.core import QgsProcessingProvider
from .DSFLI.fluxDensity_algorithm import DSFLRaw, FluxDensityAlgorithm, DSFLSymbology, DSFLSurface
from .DSFLI.mkReporting_algs import CreateMeshAlgorithm, RoadsReporting
from .DSFLI.mergeGeometry_algorithm import MergeGeometryAlgorithm, MergeGeometryDissolveAlgorithm, MergeGeometryNoOverlapAlgorithm
from .DSFLI.fluxEstimation_algorithm import FluxEstimationAlgorithm, FluxTimeAlgorithm
from .DSFLI.mkRoadsExtent import RoadsExtent, RoadsExtentBDTOPO, RoadsExtentFromCadastre, AddParcellesAlg
from .DSFLI.viirs import VIIRS_Untar
from .DSFLI.fluxDispersal_algorithm import FluxDispAlg, FluxDispTempCoulAlg, LightDispSymbology
from .DSFLI.classifyLamps import ClassifyLightingAlg
from .DSFLI.radiance_stats import RadianceStats
from .pretreatments_dark_zones import PretreatmentsDarkZones
from .statistics_radiance_grid import StatisticsRadianceGrid
from .statistics_blue_emission_grid import StatisticsBlueEmissionGrid
from .calcul_MNS import CalculMNS
# from .old.light_points_extraction import LightPointsExtraction
# from .old.viewshed_raster import ViewshedRaster
from .light_points_viewshed import LightPointsViewshed
from .analyse_visibility_light_sources import AnalyseVisibilityLightSources
from .create_MNT_from_RGEALTI import createMNTfromRGEALTI

class LightPollutionToolboxProvider(QgsProcessingProvider):
    NAME = "LPT"
    
    def __init__(self):
        """
        Default constructor.
        """
        self.alglist = [DSFLRaw(),
            FluxDensityAlgorithm(),
            DSFLSurface(),
            DSFLSymbology(),
            CreateMeshAlgorithm(),
            RoadsReporting(),
            MergeGeometryAlgorithm(),
            MergeGeometryDissolveAlgorithm(),
            MergeGeometryNoOverlapAlgorithm(),
            RoadsExtent(),
            RoadsExtentBDTOPO(),
            RoadsExtentFromCadastre(),
            AddParcellesAlg(),
            RadianceStats(),
            ClassifyLightingAlg(),
            PretreatmentsDarkZones(),
            StatisticsRadianceGrid(),
            StatisticsBlueEmissionGrid(),
            CalculMNS(),
            # LightPointsExtraction(),
            # ViewshedRaster(),
            LightPointsViewshed(),
            AnalyseVisibilityLightSources(),
            createMNTfromRGEALTI()]
        self.alglist2 = [
            VIIRS_Untar(),
            FluxDispAlg(),
            FluxDispTempCoulAlg(),
            FluxEstimationAlgorithm(),
            FluxTimeAlgorithm(),
            LightDispSymbology()
            ]
        for a in self.alglist:
            a.initAlgorithm()
        QgsProcessingProvider.__init__(self)

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        for a in self.alglist:
            self.addAlgorithm(a)

    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return 'LPT'

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return self.tr('Light Pollution Toolbox')

    def icon(self):
        cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]
        icon = QIcon(os.path.join(os.path.join(cmd_folder, '../lamp.png')))
        return icon

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.name()
        
        