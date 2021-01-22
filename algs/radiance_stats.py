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
import os.path
import tarfile
import processing
import glob

from pathlib import Path

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsFeature,
                       QgsFields,
                       QgsField,
                       QgsProcessingUtils,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingMultiStepFeedback,
                       QgsProcessingParameterBand,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterField,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterRasterLayer)
from qgis import processing
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles


class RadianceStats(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    INPUT_RASTER = 'INPUT_RASTER'
    BAND = 'BAND'
    MODE = 'MODE'
    POPULATION_FIELD = 'POPULATION_FIELD'
    SURFACE_FIELD = 'SURFACE_FIELD'
    OUTPUT = 'OUTPUT'
    
    DEFAULT_POP_FIELD = 'POPULATION'
    DEFAULT_SURF_FIELD = 'SUPERFICIE'
    RAD_POP_FIELDNAME = 'rad_pop'
    RAD_SURF_FIELDNAME = 'rad_surf'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return RadianceStats()

    def name(self):
        return 'radianceStats'

    def displayName(self):
        return self.tr('Radiance zonal statistics')

    def group(self):
        return self.tr('Statistics')

    def groupId(self):
        return 'stats'

    def shortHelpString(self):
        return self.tr("Computes statistics of radiance per population/surface according to source layer.")

    def initAlgorithm(self, config=None):
        self.options = [self.tr('Per population'),self.tr('Per area')]#,self.tr('Per area (from field)')]
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Source layer'),
                [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterEnum(
            self.MODE,
            self.tr('Radiance statistics'),
            options=self.options,
            allowMultiple=True,
            defaultValue=[0,1]))
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_RASTER,
                self.tr('Raster layer')))
        self.addParameter(
            QgsProcessingParameterBand(
                self.BAND,
                self.tr('Radiance band'),
                defaultValue=1,
                parentLayerParameterName=self.INPUT_RASTER))
        paramPopField = QgsProcessingParameterField(
                self.POPULATION_FIELD,
                self.tr('Population field'),
                defaultValue=self.DEFAULT_POP_FIELD,
                parentLayerParameterName=self.INPUT)
        # paramSurfField = QgsProcessingParameterField(
                # self.SURFACE_FIELD,
                # self.tr('Surface field'),
                # defaultValue=self.DEFAULT_SURF_FIELD,
                # parentLayerParameterName=self.INPUT)
        advancedParams = [paramPopField]#, paramSurfField]
        for param in advancedParams:
            param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
            self.addParameter(param)
        # self.addParameter(
            # QgsProcessingParameterVectorDestination(
                # self.OUTPUT,
                # self.tr('Output layer')))
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Output layer')))
        
    def processAlgorithm(self, parameters, context, feedback):
        # Parameters
        input_source, input_layer = qgsTreatments.parameterAsSourceLayer(self,
            parameters,self.INPUT,context,feedback=feedback)
        modes = self.parameterAsEnums(parameters,self.MODE,context)
        input_raster = self.parameterAsRasterLayer(parameters,self.INPUT_RASTER,context)
        band = self.parameterAsInt(parameters,self.BAND,context)
        pop_field = self.parameterAsString(parameters,self.POPULATION_FIELD,context)
        # surf_field = self.parameterAsString(parameters,self.SURFACE_FIELD,context)
        # output = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        # Init
        input_crs = input_source.sourceCrs().authid()
        raster_crs = input_raster.dataProvider().crs().authid()
        pop_mode, surf_mode = 0 in modes, 1 in modes
        nb_feats = input_layer.featureCount()
        multi_feedback = QgsProcessingMultiStepFeedback(nb_feats * 2,feedback)
        # CRS
        if (input_crs != raster_crs):
            raster_reprojected = QgsProcessingUtils.generateTempFilename('raster_reproj.tif')
            qgsTreatments.applyWarpReproject(input_raster,raster_reprojected,
                dst_crs=input_crs,context=context,feedback=multi_feedback)
            input_raster = qgsUtils.loadRasterLayer(raster_reprojected)
            multi_feedback.setCurrentStep(1)
        pixel_size = input_raster.rasterUnitsPerPixelX() * input_raster.rasterUnitsPerPixelY()
        # Zonal stats
        prefix = 'rad_'
        zonal_stats = QgsProcessingUtils.generateTempFilename('zonal_stats.gpkg')
        qgsTreatments.rasterZonalStats(input_layer,input_raster,zonal_stats,
            prefix=prefix,band=band,context=context,feedback=multi_feedback)
        multi_feedback.setCurrentStep(nb_feats)
        # Fields
        stats_layer = qgsUtils.loadVectorLayer(zonal_stats)
        stats_fields = stats_layer.fields()
        stats_fieldnames = stats_fields.names()
        if pop_mode and pop_field not in stats_fieldnames:
            raise QgsProcessingException("No population field '" + str(pop_field) + "' in input layer")
        # if surf_field_mode and surf_field not in stats_fieldnames:
            # raise QgsProcessingException("No area field '" + str(surf_field) + "' in input layer")
        rad_pop_field = QgsField(self.RAD_POP_FIELDNAME, QVariant.Double)
        rad_surf_field = QgsField(self.RAD_SURF_FIELDNAME, QVariant.Double)
        out_fields = QgsFields(stats_fields)
        out_fields.append(rad_pop_field)
        out_fields.append(rad_surf_field)
        (sink, self.dest_id) = self.parameterAsSink(parameters, self.OUTPUT,
            context, out_fields, input_source.wkbType(), input_source.sourceCrs())
        # Division
        stats_layer = qgsUtils.loadVectorLayer(zonal_stats)
        for current, feat in enumerate(stats_layer.getFeatures()):
            new_feat = QgsFeature(out_fields)
            new_feat.setGeometry(feat.geometry())
            for field in stats_layer.fields().names():
                if field != 'fid':
                    new_feat[field] = feat[field]
            rad_sum = float(feat[prefix + 'sum'])
            rad_mean = float(feat[prefix + 'mean'])
            if (pop_mode and feat[pop_field]):
                new_feat[self.RAD_POP_FIELDNAME] = (rad_sum / feat[pop_field]) * 1000
            if surf_mode:
                new_feat[self.RAD_SURF_FIELDNAME] = (rad_mean / pixel_size) * 1000000
            sink.addFeature(new_feat, QgsFeatureSink.FastInsert)
            self.pop_mode, self.surf_mode = pop_mode, surf_mode
            multi_feedback.setCurrentStep(current + nb_feats)
            
        return { self.OUTPUT : self.dest_id }
            
    def postProcessAlgorithm(self,context,feedback):
        # out_layer = QgsProject.instance().mapLayer(self.dest_id)
        out_layer = QgsProcessingUtils.mapLayerFromString(self.dest_id,context)
        if not out_layer:
            raise QgsProcessingException("No layer found for " + str(self.dest_id))
        if self.pop_mode:
            styles.setGraduatedStyle(out_layer,self.RAD_POP_FIELDNAME,'Plasma')
        elif self.surf_mode:
            styles.setGraduatedStyle(out_layer,self.RAD_SURF_FIELDNAME,'Plasma')
        else:
            assert(False)
        return { self.OUTPUT: self.dest_id }
