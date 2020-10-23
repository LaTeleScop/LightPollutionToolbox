# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import os
import os.path
import tarfile
import processing
import glob

from pathlib import Path

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFile,
                       QgsProcessingMultiStepFeedback,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink)
from qgis import processing
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments


class VIIRS_Untar(QgsProcessingAlgorithm):

    VIIRS_DIR = 'VIIRS_DIR'
    EXTENT = 'EXTENT'
    DEFAULT_DIR = 'F:/IRSTEA/TrameNoire/VIIRS/data'
    DEFAULT_FRANCE = 'F:/IRSTEA/TrameNoire/VIIRS/surfaceFrance/DEPARTEMENT.shp'
    
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return VIIRS_Untar()

    def name(self):
        return 'viirs_untar'

    def displayName(self):
        return self.tr('Untar VIIRS')

    def group(self):
        return self.tr('VIIRS')

    def groupId(self):
        return 'viirs_scripts'

    def shortHelpString(self):
        return self.tr("Untar VIIRS archives and clip it to France extent")

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.VIIRS_DIR,
                self.tr('VIIRS directory'),
                behavior = QgsProcessingParameterFile.Folder,
                defaultValue = self.DEFAULT_DIR
            )
        )

    def clipImage(input,output,context,feedback):
        parameters = { 'INPUT' : input,
                       'OUTPUT' : output,
                       'OVERLAY' : clip_layer }
        return processing.run()("qgis:clip",parameters,context,feedback)
        
    def processAlgorithm(self, parameters, context, feedback):
        
        viirs_dir = self.parameterAsFile(parameters,self.VIIRS_DIR,context)
        archive_pat = viirs_dir + "/**/*.tgz"
        files = glob.glob(archive_pat,recursive=True)
        # files = Path(viirs_dir).rglob('*.tgz')
        # for root, dirs, files in os.walk(viirs_dir):
        nb_files = len(files)
        mf = QgsProcessingMultiStepFeedback(nb_files,feedback)
        mf.pushInfo("archive_pat = " + str(archive_pat))
        # mf.pushInfo("root = " + str(root))
        mf.pushInfo("nb files = " + str(nb_files))
        for cpt, file in enumerate(files):
            if "2016" in file:
                #print(file)
                # fileNamePath = str(os.path.join(root,file))
                prefix = file[:-3]
                prefixx = os.path.basename(prefix)
                mf.pushInfo("prefix = " + str(prefix))
                mf.pushInfo("prefixx = " + str(prefixx))
                fileDir = os.path.dirname(file)
                mf.pushInfo("fileDir = " + str(fileDir))
                out_rad = prefix + "avg_rade9h.tif"
                out_cvg = prefix + "cf_cvg.tif"
                out_rad_annual = prefix + "avg_rade9.tif"
                mf.pushInfo(out_rad)
                out_rad_france = prefix + "avg_rade9_france.tif"
                out_cvg_france = prefix + "cf_cvg_france.tif"
                mf.pushInfo(out_rad_france)
                # if os.path.isfile(out_cvg_france):
                    # continue
                extract = not os.path.isfile(out_cvg)
                extract = False
                if extract:
                    try:
                        mf.pushInfo("Extracting " + str(file))
                        tar = tarfile.open(file, "r:gz")
                        tar.extractall(path=fileDir)
                        tar.close()
                    except Exception as e:
                        mf.reportErrror(str(e))
                        continue
                for ff in os.listdir(fileDir):
                    mf.pushInfo("ff = " + str(ff))
                tif_files = [os.path.join(fileDir,f) for f in os.listdir(fileDir)
                    if "2016" in f and f.endswith(".tif") and "france" not in f]
                #if os.path.isfile(out_rad_france):
                #    os.remove(out_rad_france)
                for tf in tif_files:
                    mf.pushInfo("tf = " + str(tf))
                    out_tf = tf[:-4] + "_france.tif"
                    if not os.path.isfile(out_tf):
                        qgsTreatments.clipRasterFromVector(
                            tf,self.DEFAULT_FRANCE,out_tf,
                            nodata=0,context=context,feedback=mf)
                    os.remove(tf)
                # qgsTreatments.clipRasterFromVector(
                    # out_rad,self.DEFAULT_FRANCE,out_rad_france,
                    # nodata=0,context=context,feedback=mf)
                # qgsTreatments.clipRasterFromVector(
                    # out_cvg,self.DEFAULT_FRANCE,out_cvg_france,
                    # nodata=0,context=context,feedback=mf)
                # if os.path.isfile(out_rad):
                    # os.remove(out_rad)
                    # os.remove(out_cvg)
            mf.setCurrentStep(cpt)

        return { self.OUTPUT : None }
