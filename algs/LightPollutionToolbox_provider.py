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
from .fluxDensity_algorithm import FluxDensityAlgorithm, DSFLSymbology, DSFLSurface, DSFLRaw
from .mkReporting_algs import CreateMeshAlgorithm, RoadsReporting
from .mergeGeometry_algorithm import MergeGeometryAlgorithm, MergeGeometryDissolveAlgorithm, MergeGeometryNoOverlapAlgorithm
from .fluxEstimation_algorithm import FluxEstimationAlgorithm, FluxTimeAlgorithm
from .mkRoadsExtent import RoadsExtent, RoadsExtentBDTOPO, RoadsExtentFromCadastre, AddParcellesAlg
from .viirs import VIIRS_Untar
from .fluxDispersal_algorithm import FluxDispAlg, FluxDispTempCoulAlg, LightDispSymbology
from .classifyLamps import ClassifyLightingAlg
from .radiance_stats import RadianceStats

class LightPollutionToolboxProvider(QgsProcessingProvider):

    def __init__(self):
        """
        Default constructor.
        """
        self.alglist = [FluxDensityAlgorithm(),
            DSFLSurface(),
            DSFLRaw(),
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
            ClassifyLightingAlg()]
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
