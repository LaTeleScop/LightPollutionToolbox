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

from PyQt5.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingUtils,
                       QgsProcessingException,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterCrs,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterField,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingMultiStepFeedback ,
                       QgsCoordinateReferenceSystem,
                       QgsProperty)

from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments

class RoadsExtentBDTOPO(QgsProcessingAlgorithm):
    
    INPUT = 'INPUT'
    # ROADS_WIDTH = 'ROADS_WIDTH'
    DISSOLVE = 'DISSOLVE'
    OUTPUT = 'OUTPUT'
    
    DEFAULT_CRS = QgsCoordinateReferenceSystem("epsg:2154")
    
    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input layer')))
        # self.addParameter(
            # QgsProcessingParameterField(
                # self.ROADS_WIDTH,
                # self.tr('Roads width field'),
                # defaultValue='Largeur',
                # parentLayerParameterName=self.INPUT))
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DISSOLVE,
                self.tr('Dissolve result layer'),
                defaultValue=True))
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Output layer')))

    def processAlgorithm(self, parameters, context, feedback):
        input_layer = self.parameterAsVectorLayer(parameters,self.INPUT,context)
        if not input_layer:
            raise QgsProcessingException("No input layer")
        # roads_width_field = self.parameterAsString(parameters,self.ROADS_WIDTH,context)
        dissolve_flag = self.parameterAsBool(parameters,self.DISSOLVE,context)
        output = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        
        nb_steps = 3 if dissolve_flag else 2
        feedback = QgsProcessingMultiStepFeedback(nb_steps,feedback)
        
        expr = ' "FICTIF" = \'Non\' AND "ETAT" = \'En service\' AND "POS_SOL" IN (\'0\',\'1\',\'2\')'
        selected = QgsProcessingUtils.generateTempFilename('selected.gpkg')
        qgsTreatments.extractByExpression(input_layer,expr,selected,
            context=context,feedback=feedback)
        
        feedback.setCurrentStep(1)
        
        buffered = QgsProcessingUtils.generateTempFilename('buffered.gpkg') if dissolve_flag else output
        # if roads_width_field not in input_layer.fields().names():
            # raise QgsProcessingException("Could not find '" + str(roads_width_field) + "' in roads layer")
        buf_expr = 'if ("LARGEUR", "LARGEUR" / 2, if("NB_VOIES", "NB_VOIES" * 1.75, 1.75))'
        distance = QgsProperty.fromExpression(buf_expr)
        qgsTreatments.applyBufferFromExpr(selected,distance,buffered,
            context=context,feedback=feedback)
            
        feedback.setCurrentStep(2)
                    
        if dissolve_flag:
            qgsTreatments.dissolveLayer(buffered,output,context=context,feedback=feedback)
            feedback.setCurrentStep(3)
                    
        return {self.OUTPUT: output}
        
    def name(self):
        return 'roadsExtentBDTOPO'

    def displayName(self):
        return self.tr('Build Roads Extent Layer from BDTOPO')

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return RoadsExtentBDTOPO()
                

class RoadsExtent(QgsProcessingAlgorithm):
    
    EXTENT_LAYER = 'EXTENT_LAYER'
    ROADS = 'ROADS'
    ROADS_WIDTH = 'ROADS_WIDTH'
    CADASTRE = 'CADASTRE'
    DIFF_LAYERS = 'DIFF_LAYERS'
    OUTPUT = 'OUTPUT'
    
    DEFAULT_CRS = QgsCoordinateReferenceSystem("epsg:2154")
    
    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.EXTENT_LAYER,
                self.tr('Extent layer')))
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.ROADS,
                self.tr('Roads layer')))
        self.addParameter(
            QgsProcessingParameterField(
                self.ROADS_WIDTH,
                self.tr('Roads width field'),
                defaultValue='Largeur',
                parentLayerParameterName=self.ROADS))
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.CADASTRE,
                self.tr('Cadastre layer')))
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.DIFF_LAYERS,
                self.tr('Exclude layers (surface remove from result)')))
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Output layer')))

    def processAlgorithm(self, parameters, context, feedback):
        extent_layer = self.parameterAsVectorLayer(parameters,self.EXTENT_LAYER,context)
        if not extent_layer:
            raise QgsProcessingException("No extent layer")
        roads_layer = self.parameterAsVectorLayer(parameters,self.ROADS,context)
        if not roads_layer:
            raise QgsProcessingException("No roads layer")
        roads_width_field = self.parameterAsString(parameters,self.ROADS_WIDTH,context)
        cadastre_layer = self.parameterAsVectorLayer(parameters,self.CADASTRE,context)
        if not cadastre_layer:
            raise QgsProcessingException("No cadastre layer")
        diff_layers = self.parameterAsLayerList(parameters,self.DIFF_LAYERS,context)
        output = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        # dest_crs = self.parameterAsCrs(parameters,self.CRS,context)
        
        feedback = QgsProcessingMultiStepFeedback(5,feedback)
                
        # intersection = QgsProcessingUtils.generateTempFilename('intersected.gpkg')
        # qgsTreatments.extractByLoc(roads_layer,extent_layer,intersection,
            # context=context,feedback=feedback)
        
        buffered = QgsProcessingUtils.generateTempFilename('buffered.gpkg')
        if roads_width_field not in roads_layer.fields().names():
            raise QgsProcessingException("Could not find '" + str(roads_width_field) + "' in roads layer")
        distance = QgsProperty.fromExpression('"LARGEUR" / 2')
        qgsTreatments.applyBufferFromExpr(roads_layer,distance,buffered,
            context=context,feedback=feedback)
            
        feedback.setCurrentStep(1)
            
        not_cadastre = QgsProcessingUtils.generateTempFilename('notCadastre.gpkg')
        qgsTreatments.applyDifference(extent_layer,cadastre_layer,not_cadastre,
            context=context,feedback=feedback)
            
        feedback.setCurrentStep(2)
                          
        for diff_layer in diff_layers:
            name = diff_layer.sourceName()
            out = QgsProcessingUtils.generateTempFilename('diff' + name + '.gpkg')
            qgsTreatments.applyDifference(not_cadastre,diff_layer,out,
                context=context,feedback=feedback)
            not_cadastre = out
        
        feedback.setCurrentStep(3)
        
        # buffered_layer = qgsUtils.loadVectorLayer(buffered)
        # not_cadastre_layer = qgsUtils.loadVectorLayer(not_cadastre)
        # layers = [buffered_layer,not_cadastre_layer]
        # merged = QgsProcessingUtils.generateTempFilename('merged.gpkg')
        # parameters = { 'LAYERS' : layers, 'CRS' : buffered_layer.sourceCrs(), 'OUTPUT' : merged }
        # qgsTreatments.applyProcessingAlg("LPT","Merge geometries",parameters,
            # context=context,feedback=feedback)
            
        diff_layer = QgsProcessingUtils.generateTempFilename('diff.gpkg')
        qgsTreatments.applyDifference(buffered,diff_layer,out,
            context=context,feedback=feedback)
            
        feedback.setCurrentStep(4)
        
        # dissolved = qgsTreatments.dissolveLayer(merged,output,context=context,feedback=feedback)
            
        feedback.setCurrentStep(5)
        
        return {self.OUTPUT: output}
        
    def name(self):
        return 'roadsExtent'

    def displayName(self):
        return self.tr('Build Roads Extent Layer')

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return RoadsExtent()
                
                