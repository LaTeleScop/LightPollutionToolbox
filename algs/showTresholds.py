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
                       QgsFeatureSink,
                       QgsFeatureRequest,
                       QgsFeature,
                       QgsProject,
                       QgsVectorLayer,
                       QgsProcessingUtils,
                       QgsProcessingContext,
                       QgsProcessingMultiStepFeedback,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingFeatureSourceDefinition,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterField,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterExpression,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterVectorDestination,
                       QgsFields,
                       QgsField)

from ..qgis_lib_mc import styles                       

class ShowTresholdAlg(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    FIELD = 'FIELD'
    OUTPUT = 'OUTPUT'
    
    def name(self):
        return self.NAME

    def initAlgFromFieldInfo(self,field_descr,suffix='_copy',defaultVal=None):
        self.suffix = suffix
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Lighting layer'),
                [QgsProcessing.TypeVectorPoint]))
        self.addParameter(
            QgsProcessingParameterField(
                self.FIELD,
                description=self.tr(field_descr),
                defaultValue=defaultVal,
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName=self.INPUT))
    
    def processAlgorithm(self, parameters, context, feedback):
        self.in_layer = self.parameterAsVectorLayer(parameters,self.INPUT,context)
        self.field = self.parameterAsString(parameters,self.FIELD,context)
        if not self.in_layer:
            raise QgsProcessingException("No input layer")
        self.clone = QgsVectorLayer(self.in_layer.source(),
            self.in_layer.name() + self.suffix, self.in_layer.providerType())
        return { self.OUTPUT : self.clone }

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
        
    # def group(self):
        # return self.tr('Light Flux Surfacic Density')
        
    # def groupId(self):
        # return self.tr('density')
        

   
class ShowULRAlg(ShowTresholdAlg):

    NAME = 'showULR'
    
    def initAlgorithm(self, config=None):
        self.initAlgFromFieldInfo(self.tr('ULR field'),suffix='_ulr')
        
    def postProcessAlgorithm(self,context,feedback):
        if not self.clone:
            raise QgsProcessingException("No duplicate layer")
        class_bounds = [1,4]
        color_ramp = styles.getGradientColorRampRdYlGn()
        styles.setCustomClasses2(self.clone,self.field,color_ramp,class_bounds)
        QgsProject.instance().addMapLayer(self.clone, addToLegend=True)
        return { self.OUTPUT : self.clone }
        
    def shortHelpString(self):
        helpStr = "Apply ULR symbology to input layer"
        return self.tr(helpStr)
        
    def displayName(self):
        return self.tr('Show Upward Light Ratio')

    def createInstance(self):
        return ShowULRAlg()
    