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
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterExpression,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterField,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterCrs,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterEnum,
                       QgsProcessingMultiStepFeedback,
                       QgsCoordinateReferenceSystem,
                       QgsProperty)

from processing.algs.qgis.VariableDistanceBuffer import VariableDistanceBuffer

from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments
from .mkRoadsExtent import RoadsExtentGrpAlg



class RoadsReporting(RoadsExtentGrpAlg):

    NAME = 'roadsReporting'

    NAME_FIELD = 'NAME_FIELD'
    INCLUDE_NULL = 'INCLUDE_NULL'
    END_CAP_STYLE = 'END_CAP_STYLE'
    JOIN_EXPR = 'JOIN_EXPR'
    POLYGON_LAYERS = 'POLYGON_LAYERS'
    POLYGON_BUFFER = 'POLYGON_BUFFER'
    OUTPUT_LINEAR = 'OUTPUT_LINEAR'
    # DEFAULT_BUFFER_EXPR = 'if( "LARGEUR" ,if( "LARGEUR" >=10, "LARGEUR" *2, "LARGEUR" *3),5)'
    DEFAULT_BUFFER_EXPR = 'if( "LARGEUR" ,if(  "NATURE" in ( \'Route empierrée\' , \'Route à 1 chaussée\' , \'Route à 2 chaussées\' ), if ("LARGEUR" >=10, "LARGEUR" *2, "LARGEUR" *3),	"LARGEUR"*1.5),	6)'
    DEFAULT_JOIN_EXPR = 'NOM_1_G is not NULL AND "SENS" in ( \'Sens direct\' , \'Sens inverse\' )'

    def initAlgorithm(self, config=None):
        self.cap_styles = [self.tr('Round'),'Flat', 'Square']
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.ROADS,
                self.tr('Roads layer'),
                [QgsProcessing.TypeVectorLine]))
        self.addParameter(
            QgsProcessingParameterExpression(
                self.SELECT_EXPR,
                self.tr('Expression to select features (all features if empty)'),
                defaultValue=RoadsExtentGrpAlg.DEFAULT_EXPR,
                optional =True,
                parentLayerParameterName=self.ROADS))
        self.addParameter(
            QgsProcessingParameterExpression(
                self.BUFFER_EXPR,
                self.tr('Roads buffer value'),
                defaultValue=self.DEFAULT_BUFFER_EXPR,
                parentLayerParameterName=self.ROADS))
        self.addParameter(QgsProcessingParameterEnum(
            self.END_CAP_STYLE,
            self.tr('End cap style'),
            options=self.cap_styles, defaultValue=0))
        # Join parameters
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DISSOLVE,
                self.tr('Join roads by name'),
                defaultValue=True))
        paramNameField = QgsProcessingParameterField(
                self.NAME_FIELD,
                self.tr('Roads name field'),
                defaultValue='NOM_1_G',
                parentLayerParameterName=self.ROADS)
        # paramIncludeNull = self.addParameter(
            # QgsProcessingParameterBoolean(
                # self.INCLUDE_NULL,
                # self.tr('Include roads with NULL name'),
                # defaultValue=True))
        paramJoinExpr = QgsProcessingParameterExpression(
                self.JOIN_EXPR,
                self.tr('Expression to select entities to join'),
                defaultValue=self.DEFAULT_JOIN_EXPR,
                parentLayerParameterName=self.ROADS)
        paramsJoin = [paramNameField,paramJoinExpr]
        for param in paramsJoin:
            param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
            self.addParameter(param)
        # self.addParameter(
            # QgsProcessingParameterMultipleLayers(
                # self.POLYGON_LAYERS,
                # self.tr('Polygon layers to include'),
                # layerType=QgsProcessing.TypeVectorPolygon,
                # optional=True))
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Output layer')))
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT_LINEAR,
                self.tr('Linear output'),
                optional=True))

    def processAlgorithm(self, parameters, context, feedback):
        input_layer = self.parameterAsVectorLayer(parameters,self.ROADS,context)
        if not input_layer:
            raise QgsProcessingException("No roads layer")
        name_field = self.parameterAsString(parameters,self.NAME_FIELD,context)
        select_expr = self.parameterAsExpression(parameters,self.SELECT_EXPR,context)
        buf_expr = self.parameterAsExpression(parameters,self.BUFFER_EXPR,context)
        end_cap_style = self.parameterAsEnum(parameters, self.END_CAP_STYLE, context) #+ 1
        dissolve_flag = self.parameterAsBool(parameters,self.DISSOLVE,context)
        # include_null_flag = self.parameterAsBool(parameters,self.INCLUDE_NULL,context)
        join_expr = self.parameterAsExpression(parameters,self.JOIN_EXPR,context)
        output = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        output_linear = self.parameterAsOutputLayer(parameters,self.OUTPUT_LINEAR,context)
        join_flag = join_expr is not None and join_expr != ''
        nb_steps = 3 + (3 if join_flag else 0) + (3 if output_linear else 0)
        mf = QgsProcessingMultiStepFeedback(nb_steps,feedback)
        crs = input_layer.dataProvider().sourceCrs()
        distance = QgsProperty.fromExpression(buf_expr)
        
        # Extract selection
        if select_expr:
            selected = QgsProcessingUtils.generateTempFilename('selected.gpkg')
            qgsTreatments.extractByExpression(input_layer,select_expr,selected,
                context=context,feedback=mf)
        else:
            selected = input_layer
        mf.setCurrentStep(1)
        
        
        # Apply buffer
        buffered = QgsProcessingUtils.generateTempFilename('buffered.gpkg') if dissolve_flag else output
        qgsTreatments.applyBufferFromExpr(selected,distance,buffered,
            cap_style=end_cap_style,context=context,feedback=mf)
        mf.setCurrentStep(2)
        
        # Dissolve
        if dissolve_flag:
            join_flag = join_expr is not None and join_expr != ''
            buffered_nojoin = QgsProcessingUtils.generateTempFilename('buffered_nojoin.gpkg') 
            buffered_join = QgsProcessingUtils.generateTempFilename('buffered_join.gpkg')
            # null_expr = "" + name_field + " is NULL"
            if not join_flag:
                raise QgsProcessingException("No join expression specified")
            qgsTreatments.extractByExpression(buffered,join_expr,buffered_join,
                fail_out=buffered_nojoin,context=context,feedback=mf)
            mf.setCurrentStep(3)
            dissolved = QgsProcessingUtils.generateTempFilename('dissolved.gpkg') if join_flag else output
            fields = [name_field]
            qgsTreatments.dissolveLayer(buffered_join,dissolved,fields=fields,context=context,feedback=mf)
            mf.setCurrentStep(4)
            layers = [buffered_nojoin,dissolved]
            qgsTreatments.mergeVectorLayers(layers,crs,output,context=context,feedback=mf)
            mf.setCurrentStep(5)
            
            if output_linear:
                roads_nojoin = QgsProcessingUtils.generateTempFilename('roads_nojoin.gpkg') 
                roads_join = QgsProcessingUtils.generateTempFilename('roads_join.gpkg')
                qgsTreatments.extractByExpression(selected,join_expr,roads_join,
                    fail_out=roads_nojoin,context=context,feedback=mf)
                mf.setCurrentStep(6)
                qgsTreatments.dissolveLayer(roads_join,dissolved,fields=fields,context=context,feedback=mf)
                mf.setCurrentStep(7)
                layers = [roads_nojoin,dissolved]
                qgsTreatments.mergeVectorLayers(layers,crs,output_linear,context=context,feedback=mf)
                mf.setCurrentStep(8)
                
            # selected = dissolved
            # if include_null_flag:
                # merged = QgsProcessingUtils.generateTempFilename('merged.gpkg')
                # layers = [dissolved,roads_null]
                # qgsTreatments.mergeVectorLayers(layers,crs,merged,context=context,feedback=mf)
                # selected = merged
                
        # Apply buffer
        # qgsTreatments.applyBufferFromExpr(selected,distance,output,
            # cap_style=end_cap_style,context=context,feedback=mf)
        mf.setCurrentStep(nb_steps)
                     
        return {self.OUTPUT: output}
        
    def name(self):
        return self.NAME

    def displayName(self):
        return self.tr('Reporting Per Roads')

    def createInstance(self):
        return RoadsReporting()
        
        
        
class CreateMeshAlgorithm(QgsProcessingAlgorithm):
    
    OUTPUT = 'OUTPUT'
    INPUT = 'INPUT'
    EXTENT = 'EXTENT'
    CRS = 'CRS'
    SIZE = 'SIZE'
    
    DEFAULT_CRS = QgsCoordinateReferenceSystem("epsg:2154")
    
    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.EXTENT,
                self.tr('Extent layer')))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SIZE,
                self.tr("Mesh size (in georeferenced units, meters by default)"),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=1000))
        self.addParameter(
            QgsProcessingParameterCrs(
                self.CRS,
                description=self.tr("Output CRS"),
                defaultValue=self.DEFAULT_CRS))
                
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Output layer')))
        
    def processAlgorithm(self, parameters, context, feedback):
        extent_layer = self.parameterAsVectorLayer(parameters, self.EXTENT, context)
        size = self.parameterAsInt(parameters,self.SIZE,context)
        crs = self.parameterAsCrs(parameters,self.CRS,context)
        out = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        
        extent_crs = extent_layer.dataProvider().crs()
        if extent_crs.authid() != crs.authid():
            reproj_path = QgsProcessingUtils.generateTempFilename('reproj.shp')
            qgsTreatments.applyReprojectLayer(extent_layer,
                crs,reproj_path,context=context,feedback=feedback)
            reprojected = qgsUtils.loadVectorLayer(reproj_path)
        else:
            reprojected = extent_layer
        extent = reprojected.extent()
        grid_path = QgsProcessingUtils.generateTempFilename('grid.shp')
        grid_layer = qgsTreatments.createGridLayer(extent,crs,size,grid_path,
            context=context,feedback=feedback)
        
        res = qgsTreatments.applyVectorClip(grid_layer,reprojected,out,
            context=context,feedback=feedback)
        
        return {self.OUTPUT: out }
        
    
    def name(self):
        return 'Create Mesh Layer'

    def displayName(self):
        return self.tr(self.name())

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
        
    def group(self):
        return self.tr('Utils')
        
    def groupId(self):
        return self.tr('utils')

    def createInstance(self):
        return CreateMeshAlgorithm()