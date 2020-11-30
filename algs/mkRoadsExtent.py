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
                       QgsProcessingParameterExpression,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterField,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingMultiStepFeedback ,
                       QgsCoordinateReferenceSystem,
                       QgsProperty)

from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments
#from .mergeGeometry_algorithm import MergeGeometryAlgorithm


class RoadsExtentGrpAlg(QgsProcessingAlgorithm):

    ROADS = 'ROADS'
    OUTPUT = 'OUTPUT'
    
    EXTENT_LAYER = 'EXTENT_LAYER'
    ROADS_WIDTH = 'ROADS_WIDTH'
    CADASTRE = 'CADASTRE'
    DIFF_LAYERS = 'DIFF_LAYERS'
    INCLUDE_LAYERS = 'INCLUDE_LAYERS'
    CLIP = 'CLIP'
    # REPAIR_GEOM = 'REPAIR_GEOM'
    
    SELECT_EXPR = 'SELECT_EXPR'
    DISSOLVE = 'DISSOLVE'
    #DEFAULT_EXPR = '"FICTIF" = \'Non\' AND "ETAT" = \'En service\' AND "POS_SOL" IN (\'0\',\'1\',\'2\')'
    DEFAULT_EXPR = '"FICTIF" = \'Non\''
    DEFAULT_EXPR += ' AND "ETAT" = \'En service\''
    DEFAULT_EXPR += ' AND "POS_SOL" IN (\'0\',\'1\',\'2\')'
    #DEFAULT_EXPR += ' AND "ACCES_VL" IN (\'Libre\')'
    DEFAULT_EXPR += ' AND  "NATURE" IN ( \'Escalier\' , \'Piste cyclable\', \'Rond-point\',  \'Route à 1 chaussée\', \'Route à 2 chaussées\', \'Route empierrée\', \'Sentier\', \'Chemin\' )'
    BUFFER_EXPR = 'if ("LARGEUR", "LARGEUR" / 2, if("NB_VOIES", "NB_VOIES" * 1.75, 2.5))'
    
    DEFAULT_CRS = QgsCoordinateReferenceSystem("epsg:2154")

    def initParamsBDTOPO(self):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.ROADS,
                self.tr('Roads layer'),
                [QgsProcessing.TypeVectorLine]))
        self.addParameter(
            QgsProcessingParameterField(
                self.ROADS_WIDTH,
                self.tr('Roads width field'),
                defaultValue='Largeur',
                parentLayerParameterName=self.ROADS))
        self.addParameter(
            QgsProcessingParameterExpression(
                self.SELECT_EXPR,
                self.tr('Expression to select features (all features if empty)'),
                defaultValue=self.DEFAULT_EXPR,
                optional =True,
                parentLayerParameterName=self.ROADS))
        self.addParameter(
            QgsProcessingParameterExpression(
                self.BUFFER_EXPR,
                self.tr('Roads buffer value'),
                defaultValue=self.BUFFER_EXPR,
                parentLayerParameterName=self.ROADS))
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DISSOLVE,
                self.tr('Dissolve result layer'),
                defaultValue=True))
    

    def initParamsCadastre(self):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.EXTENT_LAYER,
                self.tr('Extent layer'),
                [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.CADASTRE,
                self.tr('Cadastre layer'),
                [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.DIFF_LAYERS,
                self.tr('Exclude layers (surface remove from cadastre result)'),
                layerType=QgsProcessing.TypeVectorPolygon,
                optional=True))
        # self.addParameter(
            # QgsProcessingParameterBoolean(
                # self.REPAIR_GEOM,
                # self.tr('Repair geometry obtained from cadastre layer'),
                # defaultValue=True))
    
    def initOutput(self):
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Output layer')))

    def displayName(self):
        return self.tr(self.name())

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
        
    def group(self):
        return self.tr('Light Flux Surfacic Density')
        
    def groupId(self):
        return self.tr('density')
        
        
class RoadsExtentBDTOPO(RoadsExtentGrpAlg):

    NAME = 'roadsExtentBDTOPO'
    
    def initAlgorithm(self, config=None):
        self.initParamsBDTOPO()
        self.initOutput()

    def processAlgorithm(self, parameters, context, feedback):
        input_layer = self.parameterAsVectorLayer(parameters,self.ROADS,context)
        if not input_layer:
            raise QgsProcessingException("No roads layer")
        roads_width_field = self.parameterAsString(parameters,self.ROADS_WIDTH,context)
        dissolve_flag = self.parameterAsBool(parameters,self.DISSOLVE,context)
        expr = self.parameterAsExpression(parameters,self.SELECT_EXPR,context)
        buf_expr = self.parameterAsExpression(parameters,self.BUFFER_EXPR,context)
        output = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        
        nb_steps = 3 if dissolve_flag else 2
        feedback = QgsProcessingMultiStepFeedback(nb_steps,feedback)
        
        if expr:
            selected = QgsProcessingUtils.generateTempFilename('selected.gpkg')
            qgsTreatments.extractByExpression(input_layer,expr,selected,
                context=context,feedback=feedback)
        else:
            selected = input_layer
        
        feedback.setCurrentStep(1)
        
        buffered = QgsProcessingUtils.generateTempFilename('buffered.gpkg') if dissolve_flag else output
        if roads_width_field not in input_layer.fields().names():
            raise QgsProcessingException("Could not find '" + str(roads_width_field) + "' in roads layer")
        #buf_expr = 'if ("LARGEUR", "LARGEUR" / 2, if("NB_VOIES", "NB_VOIES" * 1.75, 2.5))'
        distance = QgsProperty.fromExpression(buf_expr)
        qgsTreatments.applyBufferFromExpr(selected,distance,buffered,
            context=context,feedback=feedback)
            
        feedback.setCurrentStep(2)
                    
        if dissolve_flag:
            qgsTreatments.dissolveLayer(buffered,output,context=context,feedback=feedback)
            feedback.setCurrentStep(3)
                    
        return {self.OUTPUT: output}
        
    def name(self):
        return self.NAME

    def displayName(self):
        return self.tr('Roads Extent (BDTOPO)')

    def createInstance(self):
        return RoadsExtentBDTOPO()
                
   
class RoadsExtentFromCadastre(RoadsExtentGrpAlg):

    NAME = 'roadsExtentCadastre'
    
    def initAlgorithm(self, config=None):
        self.initParamsCadastre()
        self.initOutput()

    def processAlgorithm(self, parameters, context, feedback):
        extent_layer = self.parameterAsVectorLayer(parameters,self.EXTENT_LAYER,context)
        if not extent_layer:
            raise QgsProcessingException("No extent layer")
        cadastre_layer = self.parameterAsVectorLayer(parameters,self.CADASTRE,context)
        if not cadastre_layer:
            raise QgsProcessingException("No cadastre layer")
        diff_layers = self.parameterAsLayerList(parameters,self.DIFF_LAYERS,context)
        # repair_flag = self.parameterAsBool(parameters,self.REPAIR_GEOM,context)
        output = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        
        nb_diff = len(diff_layers)
        feedback = QgsProcessingMultiStepFeedback(nb_diff + 2,feedback)
            
        not_cadastre = QgsProcessingUtils.generateTempFilename('notCadastre.gpkg') if nb_diff > 0 else output
        qgsTreatments.applyDifference(extent_layer,cadastre_layer,not_cadastre,
            context=context,feedback=feedback)
        feedback.setCurrentStep(1)
                          
        for cpt, diff_layer in enumerate(diff_layers, 1):
            name = diff_layer.sourceName()
            out = QgsProcessingUtils.generateTempFilename('diff' + name + '.gpkg') if cpt < nb_diff else output
            qgsTreatments.applyDifference(not_cadastre,diff_layer,out,
                context=context,feedback=feedback)
            not_cadastre = out
            feedback.setCurrentStep(cpt + 1)
            
        return {self.OUTPUT: not_cadastre}
        
    def name(self):
        return self.NAME

    def displayName(self):
        return self.tr('Roads Extent (Cadastre)')

    def createInstance(self):
        return RoadsExtentFromCadastre()   


class RoadsExtent(RoadsExtentGrpAlg):
    
    def initAlgorithm(self, config=None):
        self.initParamsBDTOPO()
        self.initParamsCadastre()
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.INCLUDE_LAYERS,
                self.tr('Include layers (surface added to result)'),
                layerType=QgsProcessing.TypeVectorPolygon,
                optional=True))
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.CLIP,
                self.tr('Clip input layers'),
                defaultValue=True))
        self.initOutput()

    def processAlgorithm(self, parameters, context, feedback):
        multi_feedback = QgsProcessingMultiStepFeedback(3,feedback)
        init_output = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        roads_layer = self.parameterAsVectorLayer(parameters,self.ROADS,context)
        dissolve_flag = self.parameterAsBool(parameters,self.DISSOLVE,context)
        extent_layer = self.parameterAsVectorLayer(parameters,self.EXTENT_LAYER,context)
        parameters[self.EXTENT_LAYER] = extent_layer
        parameters[self.CADASTRE] = self.parameterAsVectorLayer(parameters,self.CADASTRE,context)
        parameters[self.DIFF_LAYERS] = self.parameterAsLayerList(parameters,self.DIFF_LAYERS,context)
        include_layers = self.parameterAsLayerList(parameters,self.INCLUDE_LAYERS,context)
        clip_flag = self.parameterAsBool(parameters,self.CLIP,context)
        # BDTOPO
        if clip_flag:
            roads_clipped_path = QgsProcessingUtils.generateTempFilename('roads_clipped.gpkg')
            roads_clipped = qgsTreatments.applyVectorClip(roads_layer,extent_layer,
                roads_clipped_path,context=context,feedback=feedback)
            roads_layer = roads_clipped_path
        parameters[self.ROADS] = roads_layer
        out_bdtopo = QgsProcessingUtils.generateTempFilename('out_bdtopo.gpkg')
        parameters[self.OUTPUT] = out_bdtopo
        qgsTreatments.applyProcessingAlg("LPT",RoadsExtentBDTOPO.NAME,parameters,
            context=context,feedback=multi_feedback)
        multi_feedback.setCurrentStep(1)
        # CADASTRE
        out_cadastre = QgsProcessingUtils.generateTempFilename('out_cadastre.gpkg')
        parameters[self.OUTPUT] = out_cadastre
        qgsTreatments.applyProcessingAlg("LPT",RoadsExtentFromCadastre.NAME,parameters,
            context=context,feedback=multi_feedback)
        multi_feedback.setCurrentStep(2)
        # MERGE
        if clip_flag:
            include_clipped = []
            for inc in include_layers:
                inc_clip_path = QgsProcessingUtils.generateTempFilename('inc_clipped.gpkg')
                inc_clip = qgsTreatments.applyVectorClip(inc,extent_layer,
                    inc_clip_path,context=context,feedback=feedback)
                include_clipped.append(inc_clip)
            include_layers = include_clipped
        layers = [out_bdtopo,out_cadastre] + include_layers
        if dissolve_flag:
            merged = QgsProcessingUtils.generateTempFilename('out_merged.gpkg')
        else:
            merged = init_output
        parameters = { 'LAYERS' : layers, 'CRS' : self.DEFAULT_CRS, 'OUTPUT' : merged }
        qgsTreatments.applyProcessingAlg("LPT",'mergeGeom',parameters,
            context=context,feedback=feedback)
        multi_feedback.setCurrentStep(3)
        # DISSOLVE
        if dissolve_flag:
            out_fixed = QgsProcessingUtils.generateTempFilename('out_fixed.gpkg')
            qgsTreatments.fixGeometries(merged,out_fixed,context=context,feedback=feedback)
            multi_feedback.setCurrentStep(4)
            out_dissolved = QgsProcessingUtils.generateTempFilename('out_dissolved.gpkg')
            qgsTreatments.dissolveLayer(out_fixed,out_dissolved,context=context,feedback=feedback)
            qgsTreatments.assignProjection(out_dissolved,self.DEFAULT_CRS,
                init_output,context=context,feedback=feedback)
            multi_feedback.setCurrentStep(5)
        return {self.OUTPUT: init_output }
        
    def name(self):
        return 'roadsExtent'
        
    def displayName(self):
        return 'Roads Extent (BDTOPO + Cadastre)'

    def createInstance(self):
        return RoadsExtent()
        

class RoadsExtentOld(RoadsExtentGrpAlg):
    
    def initAlgorithm(self, config=None):
        RoadsExtentBDTOPO.initParams()
        RoadsExtentFromCadastre.initParams()
        self.initOutput()

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
        return 'roadsExtentold'
        
    def displayName(self):
        return 'Roads Extent (BDTOPO + Cadastre) DEPRECATED'

    def createInstance(self):
        return RoadsExtentOld()
                
  