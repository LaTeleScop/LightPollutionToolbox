"""
Model exported as python.
Name : Analyse niveau de radiance par maille
Group : ASE
With QGIS : 32215
"""

from PyQt5.QtCore import QCoreApplication
from qgis.core import QgsProcessing
from qgis.core import NULL
from qgis.core import Qgis
from qgis.core import QgsUnitTypes
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingUtils
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterDefinition
from qgis.core import QgsProcessingParameterVectorDestination
from qgis.core import QgsProcessingParameterRasterDestination
from qgis.core import QgsProcessingParameterFeatureSource
from qgis.core import QgsCoordinateReferenceSystem
from qgis import processing
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles

class StatisticsRadianceGrid(QgsProcessingAlgorithm):
    
    ALG_NAME = 'StatisticsRadianceGrid'
    
    RASTER_INPUT = 'ImageSat'
    RED_BAND_INPUT = 'RedBandInput'
    GREEN_BAND_INPUT = 'GreenBandInput'
    BLUE_BAND_INPUT = 'BlueBandInput'
    DIM_GRID = 'GridDiameter'
    TYPE_GRID = 'TypeOfGrid'
    EXTENT_ZONE = 'ExtentZone'
    GRID_LAYER_INPUT = 'GridLayerInput'
    OUTPUT_STAT = 'OutputStatRadiance'
    OUTPUT_RASTER_RADIANCE = 'OuputRasterRadiance'
    
    MAJORITY_FIELD = "_majority"
 
    SLICED_RASTER = 'SlicedRaster'
    
    IND_FIELD_POL = 'indice_pol'
    CLASS_BOUNDS_IND_POL = [0,1,2,3,4,5]
    results = {}
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.EXTENT_ZONE, self.tr('Extent zone'), [QgsProcessing.TypeVectorPolygon], defaultValue=None, optional=True))
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_INPUT,self.tr('Satellite Image'),defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSource(self.GRID_LAYER_INPUT, self.tr('Grid Layer'), [QgsProcessing.TypeVectorPolygon], defaultValue=None, optional=True))
        
        self.addParameter(QgsProcessingParameterNumber(self.DIM_GRID, self.tr('Grid diameter if no grid layer, meters'), type=QgsProcessingParameterNumber.Double, defaultValue=50))
        self.addParameter(QgsProcessingParameterEnum(self.TYPE_GRID, self.tr('Type of grid if no grid layer'), options=['Rectangle','Diamond','Hexagon'], allowMultiple=False, defaultValue=2))
        
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_STAT, self.tr('Statistics Radiance'), type=QgsProcessing.TypeVectorAnyGeometry))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_RASTER_RADIANCE, self.tr('Raster total Radiance'), createByDefault=True, defaultValue=None))
        
        param = QgsProcessingParameterNumber(self.RED_BAND_INPUT, self.tr('Index of the red band'), type=QgsProcessingParameterNumber.Integer, minValue=1, maxValue=4, defaultValue=1)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterNumber(self.GREEN_BAND_INPUT, self.tr('Index of the green band'), type=QgsProcessingParameterNumber.Integer, minValue=1, maxValue=4, defaultValue=2)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterNumber(self.BLUE_BAND_INPUT, self.tr('Index of the blue band'), type=QgsProcessingParameterNumber.Integer, minValue=1, maxValue=4, defaultValue=3)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

    def parseParams(self, parameters, context, feedback):
        self.inputExtent = qgsTreatments.parameterAsSourceLayer(self, parameters,self.EXTENT_ZONE,context,feedback=feedback)[1] 
        self.inputRaster = self.parameterAsRasterLayer(parameters, self.RASTER_INPUT, context)
        self.inputGrid = qgsTreatments.parameterAsSourceLayer(self, parameters,self.GRID_LAYER_INPUT,context,feedback=feedback)[1] 
        self.outputStat = self.parameterAsOutputLayer(parameters,self.OUTPUT_STAT,context)
        if self.inputRaster and self.inputRaster.bandCount() >=3:
            self.outputRasterRadiance = self.parameterAsOutputLayer(parameters,self.OUTPUT_RASTER_RADIANCE,context)
       
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(21, model_feedback)
        
        outputs = {}
        
        self.parseParams(parameters, context, feedback)
        
        # Test projection des input sont bien en unité métrique
        if self.inputExtent is not None or self.inputExtent != NULL:
            qgsUtils.checkProjectionUnit(self.inputExtent)
        qgsUtils.checkProjectionUnit(self.inputRaster)
        if self.inputGrid is not None or self.inputGrid != NULL:
            qgsUtils.checkProjectionUnit(self.inputGrid)
            
        # Si emprise non présente
        if self.inputExtent is None or self.inputExtent == NULL:
            # Si grille non présente prendre l'emprise de la couche raster
            if self.inputGrid is None or self.inputGrid == NULL:
                extent_zone = QgsProcessingUtils.generateTempFilename('extent_zone.gpkg')
                qgsTreatments.applyGetLayerExtent(self.inputRaster, extent_zone, context=context,feedback=feedback)
                outputs[self.EXTENT_ZONE] = qgsUtils.loadVectorLayer(extent_zone)
                outputs[self.SLICED_RASTER] = self.inputRaster # le raster n'est pas découpé
            # Sinon prendre l'emprise de la grille
            else:
                # Découper un raster selon une emprise (celle de la grille)
                outputs[self.SLICED_RASTER] = qgsTreatments.applyClipRasterByExtent(self.inputRaster, self.inputGrid, QgsProcessing.TEMPORARY_OUTPUT, context=context,feedback=feedback)
                outputs[self.EXTENT_ZONE] = self.inputGrid
                
        else:
            # Découper un raster selon une emprise
            outputs[self.SLICED_RASTER] = qgsTreatments.applyClipRasterByExtent(self.inputRaster, self.inputExtent, QgsProcessing.TEMPORARY_OUTPUT, context=context,feedback=feedback)
            outputs[self.EXTENT_ZONE] = self.inputExtent

        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        
        if self.inputGrid is None or self.inputGrid == NULL:
            # Créer une grille
            # Ajoute +2 pour aligner le bon type de grille
            temp_path_grid = QgsProcessingUtils.generateTempFilename('temp_grid.gpkg')
            qgsTreatments.createGridLayer(outputs[self.EXTENT_ZONE], outputs[self.EXTENT_ZONE].crs(), parameters[self.DIM_GRID], temp_path_grid, gtype=parameters[self.TYPE_GRID]+2, context=context,feedback=feedback)
            # qgsTreatments.createGridLayer(outputs[self.EXTENT_ZONE], QgsCoordinateReferenceSystem('EPSG:2154'), parameters[self.DIM_GRID], temp_path_grid, gtype=parameters[self.TYPE_GRID]+2, context=context,feedback=feedback)
            outputs['GridTemp'] = qgsUtils.loadVectorLayer(temp_path_grid)
            
        else:
        # Sinon on prend la grille donnée en paramètre
            outputs['GridTemp'] = self.inputGrid
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        # grille indexée
        qgsTreatments.createSpatialIndex(outputs['GridTemp'], context=context,feedback=feedback)
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        # Extraire les grilles par localisation de l'emprise
        temp_path_grid_loc = QgsProcessingUtils.generateTempFilename('temp_grid_loc.gpkg')
        qgsTreatments.extractByLoc(outputs['GridTemp'], outputs[self.EXTENT_ZONE],temp_path_grid_loc, context=context,feedback=feedback)
        outputs['GridTempExtract'] = qgsUtils.loadVectorLayer(temp_path_grid_loc)
        
        step+=1
        feedback.setCurrentStep(step)
        
        if feedback.isCanceled():
            return {}

        if self.inputRaster.bandCount() == 1:
            outputs['CalculRasterTotalRadiance'] = outputs[self.SLICED_RASTER]
            step+=4
        else:
            # Calculatrice Raster Radiance totale
            formula = 'A*0.2989+B*0.5870+C*0.1140'
            outputs['CalculRasterTotalRadiance'] = qgsTreatments.applyRasterCalcABC(outputs[self.SLICED_RASTER], outputs[self.SLICED_RASTER], outputs[self.SLICED_RASTER], parameters[self.RED_BAND_INPUT],parameters[self.GREEN_BAND_INPUT], parameters[self.BLUE_BAND_INPUT], self.outputRasterRadiance, formula, out_type=Qgis.UInt16, context=context,feedback=feedback)
            self.results[self.OUTPUT_RASTER_RADIANCE] = outputs['CalculRasterTotalRadiance']
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}

        
        # Statistique pour récupérer les pixels majoritaires
        majorityPixel = qgsTreatments.getMajorityValue(outputs[self.EXTENT_ZONE], outputs['CalculRasterTotalRadiance'], 1,self.MAJORITY_FIELD, context, feedback)
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        # Calculatrice Raster Segmentation
        # Si rad totale > majority+1 : 1 sinon 0
        formula = '1*(logical_or(A>('+str(majorityPixel)+'+1) , False))'
        # formula = '1*(logical_or(A>(median(A)+1) , False))'
        outputs['CalculRasterSegmentation'] = qgsTreatments.applyRasterCalcABC(outputs['CalculRasterTotalRadiance'], None, None, 1, None, None, QgsProcessing.TEMPORARY_OUTPUT, formula, context=context,feedback=feedback)
         
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Polygoniser zone éclairée
        outputs['PolygoniseLightZone'] = qgsTreatments.applyPolygonize(outputs['CalculRasterSegmentation'], 'DN', QgsProcessing.TEMPORARY_OUTPUT, context=context, feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Extraire zone éclairée
        temp_path_extract_light = QgsProcessingUtils.generateTempFilename('temp_extract_light.gpkg')
        qgsTreatments.applyExtractByAttribute(outputs['PolygoniseLightZone'], 'DN', temp_path_extract_light, context=context, feedback=feedback)
        outputs['ExtractLightZone'] = qgsUtils.loadVectorLayer(temp_path_extract_light)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Réparer les géométries
        light_zone_fixed = QgsProcessingUtils.generateTempFilename('light_zone_fixed.gpkg')
        qgsTreatments.fixGeometries(outputs['ExtractLightZone'],light_zone_fixed,context=context,feedback=feedback)
        outputs['ExtractLightZone'] = qgsUtils.loadVectorLayer(light_zone_fixed)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # zones éclairées indexées
        qgsTreatments.createSpatialIndex(outputs['ExtractLightZone'], context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Extraire maille éclairée
        temp_path_light_grid = QgsProcessingUtils.generateTempFilename('temp_path_light_grid.gpkg')
        qgsTreatments.extractByLoc(outputs['GridTempExtract'], outputs['ExtractLightZone'],temp_path_light_grid, context=context,feedback=feedback)
        outputs['ExtractLightGrid'] = qgsUtils.loadVectorLayer(temp_path_light_grid)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        if self.inputRaster.bandCount() >= 3:
            # Statistiques de zone bande rouge
            zonal_stats_r = QgsProcessingUtils.generateTempFilename('zonal_stats_r.gpkg')
            qgsTreatments.rasterZonalStats(outputs['ExtractLightGrid'], outputs[self.SLICED_RASTER],zonal_stats_r, prefix='R_', band=parameters[self.RED_BAND_INPUT], context=context,feedback=feedback)
            outputs['StatisticsRedBand'] = qgsUtils.loadVectorLayer(zonal_stats_r)
            step+=1               
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}

            # Statistiques de zone bande verte
            zonal_stats_g = QgsProcessingUtils.generateTempFilename('zonal_stats_g.gpkg')
            qgsTreatments.rasterZonalStats(outputs['StatisticsRedBand'], outputs[self.SLICED_RASTER],zonal_stats_g, prefix='V_', band=parameters[self.GREEN_BAND_INPUT], context=context,feedback=feedback)
            outputs['StatisticsGreenBand'] = qgsUtils.loadVectorLayer(zonal_stats_g)
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}

            # Statistiques de zone bande bleu
            zonal_stats_b = QgsProcessingUtils.generateTempFilename('zonal_stats_b.gpkg')
            qgsTreatments.rasterZonalStats(outputs['StatisticsGreenBand'], outputs[self.SLICED_RASTER],zonal_stats_b, prefix='B_', band=parameters[self.BLUE_BAND_INPUT], context=context,feedback=feedback)
            outputs['StatisticsBlueBand'] = qgsUtils.loadVectorLayer(zonal_stats_b)
            
            input_layer_stat_radiance = outputs['StatisticsBlueBand']
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
            
        else:
            input_layer_stat_radiance = outputs['ExtractLightGrid']
            
        # Statistiques de zone radiance totale
        zonal_stats_tot = QgsProcessingUtils.generateTempFilename('zonal_stats_tot.gpkg')
        qgsTreatments.rasterZonalStats(input_layer_stat_radiance, outputs['CalculRasterTotalRadiance'],zonal_stats_tot, prefix='tot_', context=context,feedback=feedback)
        outputs['StatisticsZoneTotalRadiance'] = qgsUtils.loadVectorLayer(zonal_stats_tot)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # # TODO Ajout calcul rad_tot/m² ou hectare :
        # # Création champs tot_sum/surface et calcul des indicateurs avec ce champ
        # fieldLength = 10
        # fieldPrecision = 4
        # fieldType = 0 # Flottant
        # formula = '"tot_sum"/$area'
        # temp_path_radiance_surface = QgsProcessingUtils.generateTempFilename('temp_path_radiance_surface.gpkg')
        # qgsTreatments.applyFieldCalculator(outputs['StatisticsZoneTotalRadiance'], 'radiance_surface', temp_path_radiance_surface, formula, fieldLength, fieldPrecision, fieldType, context=context,feedback=feedback)
        # outputs['StatisticsZoneTotalRadiance'] = qgsUtils.loadVectorLayer(temp_path_radiance_surface)
        # step+=1
        # feedback.setCurrentStep(step)
        # if feedback.isCanceled():
            # return {}
        
        # Calculatrice de champ indice radiance
        fieldLength = 6
        fieldPrecision = 0
        fieldType = 1 # Entier
        field_quartile = 'tot_mean' #'radiance_surface'
        # Percentile = (Number of Values Below “x” / Total Number of Values)
        formula = 'with_variable(\'percentile\',array_find(array_agg("'+field_quartile+'",order_by:="'+field_quartile+'"),"'+field_quartile+'") / array_length(array_agg("'+field_quartile+'")), CASE WHEN @percentile < 0.2 THEN 1 WHEN @percentile < 0.4 THEN 2 WHEN @percentile < 0.6 THEN 3 WHEN @percentile < 0.8 THEN 4 WHEN @percentile <= 1 THEN 5 ELSE 0 END)'
        temp_path_ind_radiance = QgsProcessingUtils.generateTempFilename('temp_path_ind_radiance.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['StatisticsZoneTotalRadiance'], self.IND_FIELD_POL, temp_path_ind_radiance, formula, fieldLength, fieldPrecision, fieldType, context=context,feedback=feedback)
        outputs['CalculFieldIndiceRadiance'] = qgsUtils.loadVectorLayer(temp_path_ind_radiance)
    
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        # Extraire par maille non éclairée (utilisé ensuite pour fusionner avec mailles éclairées)
        # est disjoint
        temp_path_dark_grid = QgsProcessingUtils.generateTempFilename('temp_path_dark_grid.gpkg')
        qgsTreatments.extractByLoc(outputs['GridTempExtract'], outputs['ExtractLightZone'],temp_path_dark_grid, predicate=[2], context=context,feedback=feedback)
        outputs['ExtractDarkGrid'] = qgsUtils.loadVectorLayer(temp_path_dark_grid)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ indice radiance null sur les mailles non éclairées
        fieldLength = 6
        fieldPrecision = 0
        fieldType = 1 # Entier
        formula = '0'
        temp_path_indice_radiance_null = QgsProcessingUtils.generateTempFilename('temp_path_indice_radiance_null.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['ExtractDarkGrid'], self.IND_FIELD_POL, temp_path_indice_radiance_null, formula, fieldLength, fieldPrecision, fieldType, context=context,feedback=feedback)
        outputs['CalculFieldIndiceRadianceNull'] = qgsUtils.loadVectorLayer(temp_path_indice_radiance_null)
      
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        # Calculatrice de champ radiance null sur les mailles non éclairées        
        fieldLength = 6
        fieldPrecision = 0
        fieldType = 0 # Float
        formula = '0'
        temp_path_radiance_null = QgsProcessingUtils.generateTempFilename('temp_path_radiance_null.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['CalculFieldIndiceRadianceNull'], 'tot_mean', temp_path_radiance_null, formula, fieldLength, fieldPrecision, fieldType, context=context,feedback=feedback)
        outputs['CalculFieldRadianceNull'] = qgsUtils.loadVectorLayer(temp_path_radiance_null)
      
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}    

        # Fusionner des couches vecteur (grilles avec radiance et grilles sans radiance)
        layersToMerge = [outputs['CalculFieldIndiceRadiance'],outputs['CalculFieldRadianceNull']]
        self.results[self.OUTPUT_STAT] = qgsTreatments.mergeVectorLayers(layersToMerge,outputs['CalculFieldIndiceRadiance'],self.outputStat, context=context, feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        print(step)
        
        return self.results

    def name(self):
        return 'StatisticsRadianceGrid'

    def displayName(self):
        return self.tr('Statistics of radiance per grid')
        
    def group(self):
        return self.tr('Light Pollution Indicators')

    def groupId(self):
        return 'lightPollutionIndicators'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate(self.__class__.__name__, string)
        
    def createInstance(self):
        return StatisticsRadianceGrid()

    def postProcessAlgorithm(self,context,feedback):
        out_layer = QgsProcessingUtils.mapLayerFromString(self.results[self.OUTPUT_STAT],context)
        if not out_layer:
            raise QgsProcessingException("No layer found for " + str(self.results[self.OUTPUT_STAT]))
        
        # Applique la symbologie par défault
        # styles.setCustomClassesInd_Pol_Category(out_layer, self.IND_FIELD_POL, self.CLASS_BOUNDS_IND_POL)
        
        bounds = styles.getQuantileBounds(out_layer, 'tot_mean', round_decimal=2)
        styles.setCustomClassesInd_Pol_Graduate(out_layer, 'tot_mean', bounds, round_decimal=2)
        
        return self.results
