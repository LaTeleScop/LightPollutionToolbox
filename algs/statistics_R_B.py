"""
Model exported as python.
Name : Analyse R/B par maille
Group : ASE
With QGIS : 32215
"""

from PyQt5.QtCore import QCoreApplication
from qgis.core import QgsProcessing
from qgis.core import NULL
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterDefinition
import processing


class StatisticsRBGrid(QgsProcessingAlgorithm):
    RASTER_INPUT = 'ImageJILINradianceRGB'
    SYMBOLOGY_STAT = 'SymbolStat'
    DIM_GRID_CALC = 'DiameterGridCalcul'
    DIM_GRID_RES = 'DiameterGridResultat'
    TYPE_GRID = 'TypeOfGrid'
    EXTENT_ZONE = 'ExtentZone'
    OUTPUT_STAT_CALC = 'OutputStatCalcul'
    OUTPUT_STAT_RES = 'OutputStatResult'
    
    SLICED_RASTER = 'SlicedRaster'
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_INPUT,self.tr('Image JILIN radiance RGB'),defaultValue=None))
        self.addParameter(QgsProcessingParameterFile(self.SYMBOLOGY_STAT, self.tr('Apply a symbology to the result'), optional=True, behavior=QgsProcessingParameterFile.File, fileFilter=self.tr('Style file (*.qml)'), defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.DIM_GRID_CALC, self.tr('Diameter grid calcul (meter)'), type=QgsProcessingParameterNumber.Double, defaultValue=150))
        self.addParameter(QgsProcessingParameterNumber(self.DIM_GRID_RES, self.tr('Diameter grid result (meter)'), type=QgsProcessingParameterNumber.Double, defaultValue=50))
        self.addParameter(QgsProcessingParameterEnum(self.TYPE_GRID, self.tr('Type of grid'), options=['Rectangle','Diamond','Hexagon'], allowMultiple=False, usesStaticStrings=False, defaultValue=2))
        self.addParameter(QgsProcessingParameterVectorLayer(self.EXTENT_ZONE, self.tr('Extent zone'), optional=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT_STAT_CALC, self.tr('statistics R/B'), type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT_STAT_RES, self.tr('statistics R/B 50m'), type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue=None))
        
        
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 1
        feedback = QgsProcessingMultiStepFeedback(16, model_feedback)
       
        results = {}
        outputs = {}
       
        if parameters[self.EXTENT_ZONE] is None or parameters[self.EXTENT_ZONE] == NULL:
            # Extraire l'emprise de la couche raster
            # Si emprise non présente
            alg_params = {
                'INPUT': parameters[self.RASTER_INPUT],
                'ROUND_TO': 0,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            parameters[self.EXTENT_ZONE] = processing.run('native:polygonfromlayerextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
            
            outputs[self.SLICED_RASTER] = parameters[self.RASTER_INPUT] # le raster n'est pas découpé
            
            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}
        else:
            # Découper un raster selon l'emprise
            alg_params = {
                'DATA_TYPE': 0,  # Utiliser le type de donnée de la couche en entrée
                'EXTRA': '',
                'INPUT': parameters[self.RASTER_INPUT],
                'NODATA': None,
                'OPTIONS': '',
                'OVERCRS': False,
                'PROJWIN': parameters[self.EXTENT_ZONE],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs[self.SLICED_RASTER] = processing.run('gdal:cliprasterbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
            
            outputs[self.EXTENT_ZONE] = parameters[self.EXTENT_ZONE]
            
            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}

        if parameters[self.DIM_GRID_CALC] != parameters[self.DIM_GRID_RES]: # uniquement sur les 2 grilles sont de taille différente
            # Créer une grille de résultat
            alg_params = {
                'CRS': parameters[self.EXTENT_ZONE],
                'EXTENT': parameters[self.EXTENT_ZONE],
                'HOVERLAY': 0,
                'HSPACING': parameters[self.DIM_GRID_RES],
                'TYPE': parameters[self.TYPE_GRID]+2,  # Ajoute +2 pour aligner le bon type de grille
                'VOVERLAY': 0,
                'VSPACING': parameters[self.DIM_GRID_RES],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['GridTempRes'] = processing.run('native:creategrid', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            feedback.setCurrentStep(step)
            step+=1
            
            # Extraire les grilles resultat par localisation de l'emprise
            alg_params = {
                'INPUT': outputs['GridTempRes']['OUTPUT'],
                'INTERSECT': parameters[self.EXTENT_ZONE],
                'PREDICATE': [0],  # intersecte
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['GridTempResExtract'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}

            # grille résultat indexée
            alg_params = {
                'INPUT': outputs['GridTempResExtract']['OUTPUT']
            }
            outputs['GridTempResIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}

        # Créer une grille de calcul
        alg_params = {
            'CRS': parameters[self.EXTENT_ZONE],
            'EXTENT': parameters[self.EXTENT_ZONE],
            'HOVERLAY': 0,
            'HSPACING': parameters[self.DIM_GRID_CALC],
            'TYPE': parameters[self.TYPE_GRID]+2,  # Ajoute +2 pour aligner le bon type de grille
            'VOVERLAY': 0,
            'VSPACING': parameters[self.DIM_GRID_CALC],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GridTempCalc'] = processing.run('native:creategrid', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Extraire les grilles de calcul par localisation de l'emprise
        alg_params = {
            'INPUT': outputs['GridTempCalc']['OUTPUT'],
            'INTERSECT': parameters[self.EXTENT_ZONE],
            'PREDICATE': [0],  # intersecte
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GridTempCalcExtract'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # grille de calcul indexée
        alg_params = {
            'INPUT': outputs['GridTempCalcExtract']['OUTPUT']
        }
        outputs['GridTempCalcIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Statistiques de zone bande rouge
        alg_params = {
            'COLUMN_PREFIX': 'R_',
            'INPUT': outputs['GridTempCalcIndex']['OUTPUT'],
            'INPUT_RASTER': outputs[self.SLICED_RASTER],
            'RASTER_BAND': 1,
            'STATISTICS': [2,4,1],  # Moyenne,Ecart-type,Somme
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['StatisticsRedBand'] = processing.run('native:zonalstatisticsfb', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Statistiques de zone bande bleu
        alg_params = {
            'COLUMN_PREFIX': 'B_',
            'INPUT': outputs['StatisticsRedBand']['OUTPUT'],
            'INPUT_RASTER': outputs[self.SLICED_RASTER],
            'RASTER_BAND': 3,
            'STATISTICS': [1,2,4],  # Somme,Moyenne,Ecart-type
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['StatisticsBlueBand'] = processing.run('native:zonalstatisticsfb', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Calcul champ R/B_mean
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'R/B_mean',
            'FIELD_PRECISION': 4,
            'FIELD_TYPE': 0,  # Flottant
            'FORMULA': '"R_mean"/"B_mean"',
            'INPUT': outputs['StatisticsBlueBand']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculFieldRb_mean'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Calcul champ R/B_Q3
        # TODO : trouver comment récupérer le q3 du raster
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'R/B_Q3',
            'FIELD_PRECISION': 4,
            'FIELD_TYPE': 0,  # Flottant
            'FORMULA': '"R_stdev"/"B_stdev"',
            'INPUT': outputs['CalculFieldRb_mean']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculFieldRb_q3'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ indice bleu pour la couche de calcul
        # output1 = self.parameterAsOutputLayer(parameters, self.OUTPUT_STAT_CALC, context) # TODO marche pas : pour récupérer le nom temporaire de la couche (faire aussi pour couhce resultat)
        alg_params = {
            'FIELD_LENGTH': 6,
            'FIELD_NAME': 'indice_pol',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,  # Entier
            'FORMULA': 'with_variable(\r\n\'percentile\',\r\narray_find(array_agg("R/B_mean",order_by:="R/B_mean"),"R/B_mean") / array_length(array_agg("R/B_mean")),\r\n    CASE\r\n    WHEN @percentile < 0.2 THEN 1\r\n    WHEN @percentile < 0.4 THEN 2\r\n    WHEN @percentile < 0.6 THEN 3\r\n    WHEN @percentile < 0.8 THEN 4\r\n    WHEN @percentile <= 1 THEN 5\r\n    ELSE 0\r\n    END\r\n)',
            'INPUT': outputs['CalculFieldRb_q3']['OUTPUT'],
            'OUTPUT': parameters[self.OUTPUT_STAT_CALC] #output1
        }
        outputs['CalculFieldIndicatorCalc'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results[self.OUTPUT_STAT_CALC] = outputs['CalculFieldIndicatorCalc']['OUTPUT']

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}
        
        if parameters[self.DIM_GRID_CALC] != parameters[self.DIM_GRID_RES]: # uniquement sur les 2 grilles sont de taille différente
            # Joindre les attributs par localisation (résumé)
            # Intersection entre les grilles de calcul et de résultat
            alg_params = {
                'DISCARD_NONMATCHING': False,
                'INPUT': outputs['GridTempResIndex']['OUTPUT'],
                'JOIN': outputs['CalculFieldRb_q3']['OUTPUT'],
                'JOIN_FIELDS': [''],
                'PREDICATE': [0],  # intersecte
                'SUMMARIES': [6],  # mean
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['JoinFieldsLocalisationCalculResult'] = processing.run('qgis:joinbylocationsummary', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}
        
            # Calculatrice de champ indice bleu pour la couche de résultat
            alg_params = {
                'FIELD_LENGTH': 6,
                'FIELD_NAME': 'indice_pol',
                'FIELD_PRECISION': 0,
                'FIELD_TYPE': 1,  # Entier
                'FORMULA': 'with_variable(\r\n\'percentile\',\r\narray_find(array_agg("R/B_mean_mean",order_by:="R/B_mean_mean"),"R/B_mean_mean") / array_length(array_agg("R/B_mean_mean")),\r\n    CASE\r\n    WHEN @percentile < 0.2 THEN 1\r\n    WHEN @percentile < 0.4 THEN 2\r\n    WHEN @percentile < 0.6 THEN 3\r\n    WHEN @percentile < 0.8 THEN 4\r\n    WHEN @percentile <= 1 THEN 5\r\n    ELSE 0\r\n    END\r\n)',
                'INPUT': outputs['JoinFieldsLocalisationCalculResult']['OUTPUT'],
                'OUTPUT': parameters[self.OUTPUT_STAT_RES]
            }
            outputs['CalculFieldIndicatorRes'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            results[self.OUTPUT_STAT_RES] = outputs['CalculFieldIndicatorRes']['OUTPUT']

            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}
            
            if parameters[self.SYMBOLOGY_STAT] is not None and parameters[self.SYMBOLOGY_STAT] != NULL: # vérifie si la symbologie est entrée
                # Définir le style de la couche résutlat
                alg_params = {
                    'INPUT': outputs['CalculFieldIndicatorRes']['OUTPUT'],
                    'STYLE': parameters[self.SYMBOLOGY_STAT]
                }
                outputs['setStyleLayerResult'] = processing.run('native:setlayerstyle', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                feedback.setCurrentStep(step)
                step+=1
                feedback.setCurrentStep(step)
            
        
        if parameters[self.SYMBOLOGY_STAT] is not None and parameters[self.SYMBOLOGY_STAT] != NULL: # vérifie si la symbologie est entrée
            # Définir le style de la couche calcul
            alg_params = {
                'INPUT': outputs['CalculFieldIndicatorCalc']['OUTPUT'],
                'STYLE': parameters[self.SYMBOLOGY_STAT]
            }
            outputs['setStyleLayerCalcul'] = processing.run('native:setlayerstyle', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        
        print(step)
        return results

    def name(self):
        return self.tr('Statistics of radiance per grid')

    def displayName(self):
        return self.tr('Statistics of radiance per grid')

    def group(self):
        return 'ASE'

    def groupId(self):
        return 'ASE'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return StatisticsRBGrid()
