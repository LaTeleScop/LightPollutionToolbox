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

from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles
from .mkRoadsExtent import FluxDenGrpAlg, RoadsExtent as RE
from .mkReporting_algs import RoadsReporting as RR

  
class FluxDensityAlgorithm(FluxDenGrpAlg):

    ALG_NAME = 'dsfl'

    LIGHTING = 'LIGHTING'
    FLUX_FIELD = 'FLUX_FIELD'
    FLUX_DIV = 'FLUX_DIV'
    FLUX_DIV_FIELD = 'flux_div'
    REPORTING = 'REPORTING'
    SURFACE = 'SURFACE'
    DISSOLVE = 'DISSOLVE'
    CLIP_DISTANCE = 'CLIP_DISTANCE'
    REPORTING_FIELDS = 'REPORTING_FIELDS'
    SKIP_EMPTY = 'SKIP_EMPTY'
    MIN_AREA = 'MIN_AREA'
    MIN_NB_LAMPS= 'MIN_NB_LAMPS'
    OUTPUT_SURFACE = 'OUTPUT_SURFACE'
    
    SURFACE_AREA = 'SURFACE'
    NB_LAMPS = 'NB_LAMPS'
    FLUX_SUM = 'FLUX_SUM'
        
    def shortHelpString(self):
        helpStr = "Estimation of light flux density.\n"
        helpStr += " Flux value is selected from lighting layer according to light flux field.\n"
        helpStr += " Surface to be illuminated (roads, sidewalks, parking areas, ...) can be specified"
        helpStr += " through a polygon layer.\n"
        helpStr += " For each entity of reporting layer, flux light points inside entity are selected."
        return self.tr(helpStr)
        
    def displayName(self):
        return self.tr('Light Flux Surfacic Density')
    
    def initLightingParams(self):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.LIGHTING,
                self.tr('Lighting layer'),
                [QgsProcessing.TypeVectorPoint]))
        self.addParameter(
            QgsProcessingParameterField(
                self.FLUX_FIELD,
                description=self.tr('Light flux field'),
                defaultValue='flux',
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName=self.LIGHTING))
    
    def initReportingAdvancedParams(self):
        self.paramClip = QgsProcessingParameterNumber(
                self.CLIP_DISTANCE,
                self.tr("Maximal distance to lighting layer (reporting layer clip)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=30,
                optional=True)
        self.paramKeepFields = QgsProcessingParameterField(
                self.REPORTING_FIELDS,
                self.tr("Reporting fields to keep in output layer"),
                parentLayerParameterName=self.REPORTING,
                allowMultiple=True,
                optional=True)
        self.paramDissolve = QgsProcessingParameterBoolean(
                self.DISSOLVE,
                self.tr('Dissolve surface layer (no overlapping features)'),
                defaultValue=False)
        self.paramSkip = QgsProcessingParameterBoolean(
                self.SKIP_EMPTY,
                self.tr('Skip features with empty flux'),
                defaultValue=True)
        self.paramMinArea = QgsProcessingParameterNumber(
                self.MIN_AREA,
                self.tr("Features minimal area (smaller features are skipped)"),
                type=QgsProcessingParameterNumber.Double,
                optional=True)
        self.paramMinLamps = QgsProcessingParameterNumber(
                self.MIN_NB_LAMPS,
                self.tr("Minimal number of lamps (features with less lamps are skipped)"),
                type=QgsProcessingParameterNumber.Integer,
                optional=True)
        self.advancedParams = [ self.paramClip, self.paramKeepFields, self.paramDissolve,
            self.paramSkip, self.paramMinArea, self.paramMinLamps ]
                
    def initAdvancedParams(self,advancedParams):
        for param in advancedParams:
            param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
            self.addParameter(param)
            
    def initOutput(self,out_sink=False,out_surf=False):
        if out_surf:
            self.addParameter(
                QgsProcessingParameterVectorDestination(
                    self.OUTPUT_SURFACE,
                    self.tr('Surface layer'),
                    optional=True))
        if out_sink:
            self.addParameter(
                QgsProcessingParameterFeatureSink(
                    self.OUTPUT,
                    self.tr('Output layer')))
        else:
            self.addParameter(
                QgsProcessingParameterVectorDestination(
                    self.OUTPUT,
                    self.tr('Output layer')))

    def initAlgorithm(self, config=None):
        self.initLightingParams()
        # self.addParameter(
            # QgsProcessingParameterNumber(
                # self.FLUX_DIV,
                # self.tr('Divide flux value for crossroads lights (lights inside multiple reporting units)'),
                # type=QgsProcessingParameterNumber.Double,
                # optional=True))
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.REPORTING,
                self.tr('Reporting layer'),
                [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.SURFACE,
                self.tr('Surface to be illuminated'),
                [QgsProcessing.TypeVectorPolygon],
                optional=True))
        # Advanced params
        self.initReportingAdvancedParams()
        advancedParams = [ self.paramClip, self.paramKeepFields, self.paramDissolve,
            self.paramSkip, self.paramMinArea, self.paramMinLamps ]
        self.initAdvancedParams(self.advancedParams)
        self.initOutput(out_sink=True)

    def processAlgorithm(self, parameters, context, feedback):
        self.dest_id = None
        # Parameters
        # lighting = self.parameterAsVectorLayer(parameters, self.LIGHTING, context)
        lighting_source, lighting_layer = qgsTreatments.parameterAsSourceLayer(
            self,parameters,self.LIGHTING,context,feedback=feedback)
        if not lighting_source:
            raise QgsProcessingException("No lighting layer")
        fieldname = self.parameterAsString(parameters,self.FLUX_FIELD,context)
        if not fieldname:
            raise QgsProcessingException("No field given for light flux")
        flux_div_flag = self.parameterAsBool(parameters,self.FLUX_DIV,context)
        reporting, reporting_layer = qgsTreatments.parameterAsSourceLayer(
            self,parameters,self.REPORTING,context,feedback=feedback)
        if not reporting:
            raise QgsProcessingException("No reporting layer")
        init_reporting_fields = reporting_layer.fields().names()
        surface, surface_layer = qgsTreatments.parameterAsSourceLayer(
            self,parameters,self.SURFACE,context,feedback=feedback)
        dissolve_flag = self.parameterAsBool(parameters,self.DISSOLVE,context)
        clip_val = self.parameterAsInt(parameters,self.CLIP_DISTANCE,context)
        reporting_fields = self.parameterAsFields(parameters,self.REPORTING_FIELDS,context)
        skip_flag = self.parameterAsBool(parameters,self.SKIP_EMPTY,context)
        min_area = self.parameterAsDouble(parameters,self.MIN_AREA,context)
        min_lamps = self.parameterAsInt(parameters,self.MIN_NB_LAMPS,context)
        
        # Reprojection if needed
        light_crs = lighting_source.sourceCrs().authid()
        reporting_crs = reporting.sourceCrs()
        # reporting_crs = reporting.dataProvider().sourceCrs()
        if reporting_crs.isGeographic():
            raise QgsProcessingException("Reporting CRS must be a projection (not lat/lon)")
        feedback.pushDebugInfo("reporting_crs = " + str(type(reporting_crs)))
        feedback.pushDebugInfo("reporting_crs = " + str(reporting_crs))
        reporting_crs_id = reporting_crs.authid()
        feedback.pushDebugInfo("reporting_crs_id = " + str(type(reporting_crs_id)))
        feedback.pushDebugInfo("reporting_crs_id = " + str(reporting_crs_id))
        if light_crs != reporting_crs_id:
            lighting_path = QgsProcessingUtils.generateTempFilename('light_reproj.gpkg')
            qgsTreatments.applyReprojectLayer(lighting_layer,reporting_crs,lighting_path,
                context=context,feedback=feedback)
            lighting_layer = lighting_path
        if surface:
            surface_crs = surface.sourceCrs().authid()
            if reporting_crs_id != surface_crs:
                surface_reproj = QgsProcessingUtils.generateTempFilename('surface_reproj.gpkg')
                qgsTreatments.applyReprojectLayer(surface_layer,reporting_crs,surface_reproj,
                    context=context,feedback=feedback)
                surface_fixed = QgsProcessingUtils.generateTempFilename('surface_fixed.gpkg')
                qgsTreatments.fixGeometries(surface_reproj,surface_fixed,
                    context=context,feedback=feedback)
                surface_layer = qgsUtils.loadVectorLayer(surface_fixed)
                qgsTreatments.createSpatialIndex(surface_layer,context=context,feedback=feedback)
                
        # Output fields initialization
        nb_lamps_field = QgsField(self.NB_LAMPS, QVariant.Int)
        flux_sum_field = QgsField(self.FLUX_SUM, QVariant.Double)
        surface_field = QgsField(self.SURFACE_AREA, QVariant.Double)
        flux_den_field = QgsField(self.FLUX_DEN, QVariant.Double)
        out_fields = QgsFields()
        for f in reporting_layer.fields():
            if f.name() in reporting_fields:
                # feedback.pushDebugInfo("f2 = " + str( f.name()))
                out_fields.append(f)
        out_fields.append(nb_lamps_field)
        out_fields.append(flux_sum_field)
        out_fields.append(surface_field)
        out_fields.append(flux_den_field)
        (sink, self.dest_id) = self.parameterAsSink(parameters, self.OUTPUT,
                context, out_fields, reporting.wkbType(), reporting.sourceCrs())

        # Progess bar step
        nb_feats = reporting.featureCount()
        total = 100.0 / nb_feats if nb_feats else 0
        
        # Clip according to distance to lighting
        if clip_val:
            buffered_path = QgsProcessingUtils.generateTempFilename('light_buf.gpkg')
            buffered = qgsTreatments.applyBufferFromExpr(lighting_layer,clip_val,
                buffered_path,context=context,feedback=feedback)
            clipped_path = QgsProcessingUtils.generateTempFilename('reporting_clip.gpkg')
            qgsTreatments.createSpatialIndex(reporting_layer,context=context,feedback=feedback)
            clipped = qgsTreatments.applyVectorClip(reporting_layer,buffered_path,
                clipped_path,context=context,feedback=feedback)
            reporting_layer = clipped_path
        
        # Get reporting units count per light
        if flux_div_flag:
            if 'ID' in init_reporting_fields:
                id_field = 'ID'
            elif 'fid' in init_reporting_fields:
                id_field = 'fid'
            else:
                raise QgsProcessingException("ID field does not exist in reporting layer")
            qgsTreatments.createSpatialIndex(lighting_layer,context=context,feedback=feedback)
            joined_light_path = QgsProcessingUtils.generateTempFilename('joined_light.gpkg')
            qgsTreatments.joinByLocSummary(lighting_layer,reporting_layer,joined_light_path,
                [id_field],summaries=[0],predicates=[0],context=context,feedback=feedback)
            joined_light_layer = qgsUtils.loadVectorLayer(joined_light_path)
            id_cpt_name = id_field + '_count'
            def funcDiv(f):
                if f[fieldname]:
                    try:
                        flux = float(f[fieldname])
                        nb_units = int(f[id_cpt_name])
                        return flux / nb_units
                    except ValueError:
                        return None
                else:
                    return None
            qgsUtils.createOrUpdateField(joined_light_layer,funcDiv,self.FLUX_DIV_FIELD)
            lighting_layer, fieldname = joined_light_layer, self.FLUX_DIV_FIELD
        # Join light points summary by reporting unit
        joined_path = QgsProcessingUtils.generateTempFilename('joined.gpkg')
        # SUM = 5
        summaries = [0,1,2,3,5,6]
        qgsTreatments.createSpatialIndex(reporting_layer,context=context,feedback=feedback)
        joined = qgsTreatments.joinByLocSummary(reporting_layer,lighting_layer,joined_path,
            [fieldname],summaries,predicates=[0],context=context,feedback=feedback)
        joined_layer = qgsUtils.loadVectorLayer(joined_path)
        nb_lamps_fieldname = fieldname + "_count"
        flux_field_sum = fieldname + "_sum"
        
        # Set context and feedback
        if not context:
            context = QgsProcessingContext()
        context = context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)
        multi_feedback = QgsProcessingMultiStepFeedback(nb_feats,feedback)
        
        # Iteration on each reporting unit
        qgsTreatments.createSpatialIndex(joined_layer,context=context,feedback=feedback)
        for current, feat in enumerate(joined_layer.getFeatures()):
            if feedback.isCanceled():
                break
            f_geom = feat.geometry()
            f_area = f_geom.area()
            f_id = feat.id()
            nb_lamps = feat[nb_lamps_fieldname]
            flux_sum = feat[flux_field_sum]
            if skip_flag and flux_sum == 0:
                continue
            if f_area < min_area:
                continue
            if nb_lamps < min_lamps:
                continue
            
            try:
                if surface:
                    # Clip surface layer to reporting feature boundaries to retrieve intersecting area
                    nb_steps = 4 if dissolve_flag else 3
                    mmf = QgsProcessingMultiStepFeedback(nb_steps,multi_feedback)
                    joined_layer.selectByIds([f_id])
                    suffix = "_" + str(f_id) + ".gpkg"
                    input_feat = QgsProcessingUtils.generateTempFilename("selection" + suffix)
                    qgsTreatments.saveSelectedAttributes(joined_layer,
                        input_feat,context=context,feedback=mmf)
                    mmf.setCurrentStep(1)
                    # input_feat = QgsProcessingFeatureSourceDefinition(joined_layer.id(),True)
                    clipped_path = QgsProcessingUtils.generateTempFilename("clipped"
                        + str(f_id) + ".gpkg")
                    clipped = qgsTreatments.applyVectorClip(surface_layer,input_feat,
                        clipped_path,context=context,feedback=mmf)
                    mmf.setCurrentStep(2)
                    if dissolve_flag:
                        feat_surface_path = QgsProcessingUtils.generateTempFilename(
                            "dissolved" + str(f_id) + ".gpkg")
                        qgsTreatments.dissolveLayer(clipped,feat_surface_path,context=context,feedback=mmf)
                        mmf.setCurrentStep(3)
                    else:
                        feat_surface_path = clipped_path
                    feat_surface_layer = qgsUtils.loadVectorLayer(feat_surface_path)
                    joined_layer.removeSelection()
                    
                    surface_area = 0
                    for surface_feat in feat_surface_layer.getFeatures():
                        surface_geom = surface_feat.geometry()
                        intersection = f_geom.intersection(surface_geom)
                        surface_area += intersection.area()
                    mmf.setCurrentStep(nb_steps)
                else:
                    surface_area = f_area
                    
                # Output result feature
                new_feat = QgsFeature(out_fields)
                new_feat.setGeometry(feat.geometry())
                for report_field in reporting_fields:
                    new_feat[report_field] = feat[report_field]
                new_feat[self.NB_LAMPS] = nb_lamps
                new_feat[self.FLUX_SUM] = flux_sum
                new_feat[self.SURFACE_AREA] = surface_area
                new_feat[self.FLUX_DEN] = flux_sum / surface_area if surface_area > 0 else None
                sink.addFeature(new_feat, QgsFeatureSink.FastInsert)
            except Exception as e:
                feedback.reportError('Unexpected error : ' + str(e))
                raise e
                
            multi_feedback.setCurrentStep(current + 1)
        
        return {self.OUTPUT: self.dest_id }
            
    def postProcessAlgorithm(self,context,feedback):
        # out_layer = QgsProject.instance().mapLayer(self.dest_id)
        out_layer = QgsProcessingUtils.mapLayerFromString(self.dest_id,context)
        if not out_layer:
            raise QgsProcessingException("No layer found for " + str(self.dest_id))
        styles.setCustomClassesDSFL(out_layer,self.FLUX_DEN)
        return {self.OUTPUT: self.dest_id }
        
        

class DSFLSymbology(FluxDenGrpAlg):

    ALG_NAME = 'dsflSymbology'

    DSFL_FIELD = 'DSFL_FIELD'
        
    def shortHelpString(self):
        helpStr = "Apply symbology to DSFL layer"
        return self.tr(helpStr)
        
    def displayName(self):
        return self.tr('Apply symbology to DSFL layer')

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input layer')))
        self.addParameter(
            QgsProcessingParameterField(
                self.DSFL_FIELD,
                self.tr('DSFL field'),
                defaultValue=self.FLUX_DEN,
                parentLayerParameterName=self.INPUT))
    
    
    def processAlgorithm(self, parameters, context, feedback):
        self.in_layer = self.parameterAsVectorLayer(parameters,self.INPUT,context)
        self.dsfl_field = self.parameterAsString(parameters,self.DSFL_FIELD,context)
        if not self.in_layer:
            raise QgsProcessingException("No input layer")
        return { self.OUTPUT : None }
        
    
    def postProcessAlgorithm(self,context,feedback):
        if not self.in_layer:
            raise QgsProcessingException("No DSFL layer")
        styles.setCustomClassesDSFL(self.in_layer,self.dsfl_field)
        return { self.OUTPUT : None }
        


FDA = FluxDensityAlgorithm

class DSFLSurface(FluxDensityAlgorithm):

    ALG_NAME = 'dsflSurface'

    REPORTING_MODE = 'REPORTING_MODE'
    SURFACE_LAYER = 'SURFACE_LAYER'
        
    def shortHelpString(self):
        helpStr = "Computes light flux surfacic density from already computed surface layer"
        return self.tr(helpStr)
        
    def displayName(self):
        return self.tr('Light Flux Surfacic Density (from surface)')
    
    def initReportingParams(self):
        self.reporting_modes = [
            self.tr('Per road section'),
            self.tr('Per road section (linear)'),
            self.tr('Per road'),
            self.tr('Per lamp')
        ]
        self.addParameter(
            QgsProcessingParameterEnum(
                self.REPORTING_MODE,
                self.tr('Reporting mode'),
                options=self.reporting_modes,
                defaultValue=0))
        self.initLightingParams()

    def initAlgorithm(self, config=None):
        # Inputs
        self.initReportingParams()
        self.initLightingParams()
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.SURFACE,
                self.tr('Surface to be illuminated'),
                [QgsProcessing.TypeVectorPolygon],
                optional=True))
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                RE.ROADS,
                self.tr('Roads layer'),
                [QgsProcessing.TypeVectorLine],
                optional=True))
        # self.addParameter(
            # QgsProcessingParameterFeatureSource(
                # RE.EXTENT_LAYER,
                # self.tr('Extent layer'),
                # [QgsProcessing.TypeVectorPolygon]))
        # Advanced parameters
        self.initReportingAdvancedParams() 
        self.initAdvancedParams(self.advancedParams)
        
        # Outputs
        self.initOutput(out_sink=False)
    
    def processAlgorithm(self, parameters, context, feedback):
        # Params
        reporting_mode = self.parameterAsEnum(parameters,self.REPORTING_MODE,context)
        lighting_source, lighting_layer = qgsTreatments.parameterAsSourceLayer(
            self,parameters,self.LIGHTING,context,feedback=feedback)
        self.fieldname = self.parameterAsString(parameters,FDA.FLUX_FIELD,context)
        surface_source, surface_layer = qgsTreatments.parameterAsSourceLayer(self,
            parameters,self.SURFACE,context,feedback=feedback)
        roads_source, roads_layer = qgsTreatments.parameterAsSourceLayer(self,
            parameters,RE.ROADS,context,feedback=feedback)
        # Advanced params
        clip_distance = self.parameterAsDouble(parameters,self.CLIP_DISTANCE,context)
        # Outputs
        self.output = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        out_linear = reporting_mode == 1
        # Init steps
        nb_steps = 3 if out_linear else 2
        mf = QgsProcessingMultiStepFeedback(nb_steps,feedback)
        if out_linear:
            id_field = 'ID'
            if id_field not in roads_layer.fields().names():
                raise QgsProcessingException("No 'ID' field in roads layer")
        qgsTreatments.fixShapefileFID(surface_layer,context=context,feedback=feedback)
        # Reporting
        reporting_layer = QgsProcessingUtils.generateTempFilename('reporting.gpkg')
        if reporting_mode == 3: # voronoi
            if qgsUtils.isMultipartLayer(lighting_layer):
                in_voronoi = QgsProcessingUtils.generateTempFilename('lighting_single.gpkg')
                qgsTreatments.multiToSingleGeom(lighting_layer,in_voronoi,context=context,feedback=mf)
            else:
                in_voronoi = lighting_layer
            qgsTreatments.applyVoronoi(in_voronoi,reporting_layer,context=context,feedback=mf)
        else:
            reporting_params = parameters.copy()
            reporting_params[RR.ROADS] = roads_layer
            reporting_params[RR.BUFFER_EXPR] = RR.DEFAULT_BUFFER_EXPR
            reporting_params[RR.NAME_FIELD] = RR.DEFAULT_NAME_FIELD
            reporting_params[RR.END_CAP_STYLE] = 1 # Flat buffer cap style
            reporting_params[RR.DISSOLVE] = reporting_mode in [2] # Roads
            reporting_params[RR.OUTPUT] = reporting_layer
            qgsTreatments.applyProcessingAlg('LPT',RR.ALG_NAME,reporting_params,
                context=context,feedback=mf)
        mf.setCurrentStep(1)
        # Light surfacic density
        density_params = parameters.copy()
        density_params[FDA.LIGHTING] = lighting_layer
        density_params[FDA.REPORTING] = reporting_layer
        density_params[FDA.CLIP_DISTANCE] = clip_distance
        density_params[FDA.SURFACE] = surface_layer
        if out_linear:
            output_surf = QgsProcessingUtils.generateTempFilename('output_surface.gpkg')
            density_params[FDA.REPORTING_FIELDS] = [id_field]
            density_params[FDA.OUTPUT] = output_surf
        else:
            density_params[FDA.OUTPUT] = self.output
        self.out_id = qgsTreatments.applyProcessingAlg('LPT',FDA.ALG_NAME,density_params,
            context=context,feedback=mf)
        mf.setCurrentStep(3)
        # Join if output linear
        if out_linear:
            copy_fields = [ FDA.NB_LAMPS, FDA.FLUX_SUM, FDA.SURFACE_AREA, FDA.FLUX_DEN ]
            self.out_id = qgsTreatments.joinByAttribute(roads_layer,id_field,output_surf,id_field,
                copy_fields=copy_fields,out_layer=self.output,context=context,feedback=mf)
        return { self.OUTPUT : self.output }
        
    
    def postProcessAlgorithm(self,context,feedback):
        out_layer = QgsProcessingUtils.mapLayerFromString(self.out_id,context)
        if not out_layer:
            raise QgsProcessingException("No layer found for " + str(self.out_id))
        styles.setCustomClassesDSFL(out_layer,self.FLUX_DEN)
        return {self.OUTPUT: self.output }


class DSFLRaw(DSFLSurface):

    ALG_NAME = 'dsflRaw'

    REPORTING_MODE = 'REPORTING_MODE'
    SURFACE_HYDRO = 'SURFACE_HYDRO'
    DISSOLVE_STEP = 'DISSOLVE_STEP'
    OUTPUT_SURFACE = 'OUTPUT_SURFACE'
        
    def shortHelpString(self):
        helpStr = "Computes light flux surfacic density from raw data"
        return self.tr(helpStr)
        
    def displayName(self):
        return self.tr('Light Flux Surfacic Density (from raw data)')
        
    def group(self):
        return None
    def groupId(self):
        return None

    def initAlgorithm(self, config=None):
        # Inputs
        self.initReportingParams()
        self.initLightingParams()
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                RE.ROADS,
                self.tr('Roads layer'),
                [QgsProcessing.TypeVectorLine]))
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                RE.EXTENT_LAYER,
                self.tr('Extent layer'),
                [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                RE.CADASTRE,
                self.tr('Cadastre layer'),
                [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.SURFACE_HYDRO,
                self.tr('Hydrographic surface layer'),
                [QgsProcessing.TypeVectorPolygon],
                optional=True))
        # Advanced parameters
        self.initReportingAdvancedParams()
        self.paramSelectExpr = QgsProcessingParameterExpression(
                RE.SELECT_EXPR,
                self.tr('Roads selection (surface layer)'),
                defaultValue=RE.DEFAULT_EXPR,
                optional =True,
                parentLayerParameterName=RE.ROADS)
        self.paramBufferExpr = QgsProcessingParameterExpression(
                RE.BUFFER_EXPR,
                self.tr('Roads buffer value (surface layer)'),
                defaultValue=RE.DEFAULT_BUFFER_EXPR,
                parentLayerParameterName=RE.ROADS)
        self.paramDissolveStep = QgsProcessingParameterEnum(
                self.DISSOLVE_STEP,
                self.tr('Dissolve step'),
                options=[self.tr('Dissolve surface layer'),self.tr('Dissolve reporting unit')],
                defaultValue=0)
        self.advancedParams = [ self.paramClip, self.paramSelectExpr, self.paramBufferExpr,
            self.paramDissolveStep, self.paramSkip, self.paramMinArea, self.paramMinLamps ]
        self.initAdvancedParams(self.advancedParams)
        # Outputs
        self.initOutput(out_surf=True)
    
    def processAlgorithm(self, parameters, context, feedback):
        # Parameters
        reporting_mode = self.parameterAsEnum(parameters,self.REPORTING_MODE,context)
        lighting_source, lighting_layer = qgsTreatments.parameterAsSourceLayer(
            self,parameters,self.LIGHTING,context,feedback=feedback)
        self.fieldname = self.parameterAsString(parameters,FDA.FLUX_FIELD,context)
        roads_source, roads_layer = qgsTreatments.parameterAsSourceLayer(self,
            parameters,RE.ROADS,context,feedback=feedback)
        cadastre_source, cadastre_layer = qgsTreatments.parameterAsSourceLayer(self,
            parameters,RE.CADASTRE,context,feedback=feedback)
        hydro_source, hydro_layer = qgsTreatments.parameterAsSourceLayer(self,
            parameters,self.SURFACE_HYDRO,context,feedback=feedback)
        extent_source, extent_layer = qgsTreatments.parameterAsSourceLayer(self,
            parameters,RE.EXTENT_LAYER,context,feedback=feedback)
        clip_distance = self.parameterAsDouble(parameters,self.CLIP_DISTANCE,context)
        dissolve_step = self.parameterAsEnum(parameters,self.DISSOLVE_STEP,context)
        include_layers = self.parameterAsLayerList(parameters,RE.INCLUDE_LAYERS,context)
        diff_layers = self.parameterAsLayerList(parameters,RE.DIFF_LAYERS,context)
        output_surface = self.parameterAsOutputLayer(parameters,self.OUTPUT_SURFACE,context)
        self.output = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        out_linear = reporting_mode == 1
        # Init steps
        nb_steps = 3 if out_linear else 2
        mf = QgsProcessingMultiStepFeedback(nb_steps,feedback)
        if out_linear:
            id_field = 'ID'
            if id_field not in roads_layer.fields().names():
                raise QgsProcessingException("No 'ID' field in roads layer")
        # Surface
        surface_params = parameters.copy()
        surface_params[RE.ROADS] = roads_layer
        surface_params[RE.CADASTRE] = cadastre_layer
        surface_params[RE.EXTENT_LAYER] = extent_layer
        surface_params[RE.INCLUDE_LAYERS] = include_layers
        surface_params[RE.DIFF_LAYERS] = diff_layers
        if hydro_source:
            surface_params[RE.DIFF_LAYERS] += [hydro_layer]
        surface_params[RE.DISSOLVE] = dissolve_step == 0
        surface_params[RE.OUTPUT] = output_surface
        surface = qgsTreatments.applyProcessingAlg('LPT',
            RE.ALG_NAME,surface_params,context=context,feedback=mf)
        mf.setCurrentStep(1)
        # Light surfacic density
        qgsTreatments.fixShapefileFID(surface,context=context,feedback=mf)
        density_params = parameters.copy()
        density_params[FDA.LIGHTING] = lighting_layer
        # density_params[FDA.REPORTING] = reporting_layer
        density_params[FDA.CLIP_DISTANCE] = clip_distance
        density_params[FDA.SURFACE] = surface
        density_params[RE.ROADS] = roads_layer
        density_params[FDA.DISSOLVE] = dissolve_step == 1
        density_params[FDA.SKIP_EMPTY] = True
        if out_linear:
            output_surf = QgsProcessingUtils.generateTempFilename('output_surface.gpkg')
            density_params[FDA.REPORTING_FIELDS] = [id_field]
            density_params[FDA.OUTPUT] = output_surf
        else:
            density_params[FDA.OUTPUT] = self.output
        self.out_id = qgsTreatments.applyProcessingAlg('LPT',
            DSFLSurface.ALG_NAME,density_params,context=context,feedback=mf)
        mf.setCurrentStep(2)
        # Join if output linear
        if out_linear:
            copy_fields = [ FDA.NB_LAMPS, FDA.FLUX_SUM, FDA.SURFACE_AREA, FDA.FLUX_DEN ]
            self.out_id = qgsTreatments.joinByAttribute(roads_layer,id_field,output_surf,id_field,
                copy_fields=copy_fields,out_layer=self.output,context=context,feedback=mf)
            mf.setCurrentStep(3)
        return { self.OUTPUT : self.output }
        
    
    def postProcessAlgorithm(self,context,feedback):
        out_layer = QgsProcessingUtils.mapLayerFromString(self.out_id,context)
        if not out_layer:
            raise QgsProcessingException("No layer found for " + str(self.out_id))
        styles.setCustomClassesDSFL(out_layer,self.FLUX_DEN)
        return {self.OUTPUT: self.output }
