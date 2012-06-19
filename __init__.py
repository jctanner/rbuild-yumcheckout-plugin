# full details.
#
"""
yumheckout command and related utilities.
"""
import os
import tempfile

from conary.lib import util

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command

from rbuild_plugins.yumcheckout.repomd import yumrepo
from rbuild_plugins.yumcheckout.generator import parserepo
from rbuild_plugins.yumcheckout.generator import grouprecipes
from rbuild_plugins.yumcheckout.conaryhelpers import labelquery

import epdb

class YumCheckoutCommand(command.BaseCommand):
    
    #epdb.st()

    help = "Parse a yumrepo and create package/group recipes"
    paramHelp = '[<options>] <yumrepourl>'

    commands = ['yumcheckout']
    docs = {'factory' : "choose the default factory for recipes"}

    def addLocalParameters(self, argDef):
        argDef['factory'] = command.OPT_PARAM
        argDef['templatedir'] = command.OPT_PARAM
        argDef['upstreamlabel'] = command.OPT_PARAM
        argDef['packages'] = command.NO_PARAM
        argDef['groups'] = command.NO_PARAM


    def runCommand(self, handle, argSet, args):
        print "runCommand ..."
        yumRepoUrl, = self.requireParameters(args, ['yumRepoUrl'])[1:]
        factory = argSet.pop('factory', None)
        #print "runCommand ..."
        self.runYumCheckoutCommand(handle, argSet, args, yumRepoUrl, factory=None)

    def runYumCheckoutCommand(self, handle, argSet, args, yumRepoUrl, factory=None):
        print "runYumCheckoutCommand ... %s" % yumRepoUrl
        #epdb.st()
        yumrepoObj = yumrepo.yumRepo(yumRepoUrl)
        #epdb.st()
        yumrepoObj.findLatestPackages()

        #productStore = self.handle.productStore
        #currentLabel = productStore.getActiveStageLabel()
        #print "DEBUG: LABEL = %s" % currentLabel
        localLabel = handle.YumCheckout.getLocalLabel()
        upstreamLabel = handle.YumCheckout.getUpstreamLabel()

        #yumrepoObj = labelquery.findYumPackagesInLabel(yumrepoObj, 
        #    'rhel.rpath.com@rpath:rhel-5-server', 
        #    'repoimporttests.eng.rpath.com@r:repoimporttests-trunk-devel')
        yumrepoObj = labelquery.findYumPackagesInLabel(yumrepoObj, 
                                            upstreamLabel, localLabel)


        #import epdb; epdb.st()

        #if (argSet['packages']):
        if (argSet.get('packages', False)):
            outputrecipes = parserepo.processYumRepoKindred(yumrepoObj)

            for key in sorted(outputrecipes.keys()):
                print "INFO: checking out package %s" % key
                handle.YumCheckout.checkoutPackageDefault(key, template=None, factory=factory)
                handle.YumCheckout.writeRecipe(outputrecipes[key],  key + ".recipe", key)

        #if (argSet['groups']):
        if (argSet.get('groups', False)):
            outputrecipes = grouprecipes.GroupRecipes(yumrepoObj)
            #epdb.st()
            for key in sorted(outputrecipes.recipes.keys()):
                print "INFO: checking out %s" % key
                handle.YumCheckout.checkoutPackageDefault(key, template=None, factory=factory)
                handle.YumCheckout.writeRecipe(outputrecipes.recipes[key],  key + ".recipe", key)


class YumCheckout(pluginapi.Plugin):
    name = 'yumcheckout'

    def registerCommands(self):
        self.handle.Commands.registerCommand(YumCheckoutCommand)

    def yumCheckout(self, yumrepourl):
        print "parsing: %s" % yumrepourl


    def getLocalLabel(self):
        productStore = self.handle.productStore
        currentLabel = productStore.getActiveStageLabel()
        return currentLabel

    def getUpstreamLabel(self):
        product = self.handle.product
        upstreamSources = product.getSearchPaths()
        upstreamSources = [(x.troveName, x.label, None)
                            for x in upstreamSources]
        upstreamLabel = upstreamSources[1][1].encode('utf-8')
        return upstreamLabel

    def checkoutPackage(self, packageName):
        productStore = self.handle.productStore
        currentLabel = productStore.getActiveStageLabel()
        targetDir = productStore.getCheckoutDirectory(packageName)
        self.handle.facade.conary.checkout(
            packageName, currentLabel, targetDir=targetDir)
        return targetDir



    def checkoutPackageDefault(self, packageName, template=None,
                               factory=None):
        existingPackage = self._getExistingPackage(packageName)
        if existingPackage:
            targetDir = self.checkoutPackage(packageName)
            self.handle.ui.info('Checked out existing package %r in %r',
                packageName, self._relPath(os.getcwd(), targetDir))
            return targetDir

        self.newPackage(packageName, template=template, factory=factory)

    def newPackage(self, packageName, message=None, template=None,
                   factory=None):

        ui = self.handle.ui
        conaryFacade = self.handle.facade.conary
        productStore = self.handle.productStore
        currentLabel = productStore.getActiveStageLabel()
        targetDir = productStore.getCheckoutDirectory(packageName)

        conaryFacade.createNewPackage(packageName, currentLabel,
                                          targetDir=targetDir,
                                          template=template,
                                          factory=factory)

        return 

    def writeRecipe(self, recipedata, filename, targetDir):
        f = open(targetDir + "/" + filename, 'w')    
        for line in recipedata:
            f.write(line)
        f.close()
        
    def _checkProductStore(self):
        if not self.handle.productStore:
            # Neither new nor checkout functions outside of a product store
            raise errors.PluginError(
                'Current directory is not part of a product.\n'
                'To initialize a new product directory, use "rbuild init"')

    def _getExistingPackage(self, packageName):
        self._checkProductStore()
        currentLabel = self.handle.productStore.getActiveStageLabel()
        return self.handle.facade.conary._findTrove(packageName + ':source',
                                                    currentLabel,
                                                    allowMissing=True)

    @staticmethod
    def _relPath(fromPath, toPath):
        """
        Print the relative path from directory fromPath to directory toPath
        If C{fromPath} is from C{os.getcwd()} then the output of this
        command should be a relative path that would be appropriate for
        the cd command, because this function is used to display paths
        to the user that would be used for this purpose.
        @param fromPath: directory name from which to construct a
        relative symlink
        @param toPath: directory name to which to construct a relative
        symlink
        @return: relative symlink from fromPath to toPath
        """
        # Note that abspath also normalizes
        absFromPath = os.path.abspath(fromPath)
        absToPath = os.path.abspath(toPath)
        if absFromPath == absToPath:
            # identical paths
            return '.'
        fromPathList = absFromPath.split('/')
        toPathList = absToPath.split('/')
        while fromPathList and toPathList and fromPathList[0] == toPathList[0]:
            fromPathList.pop(0)
            toPathList.pop(0)

        upDots = '/'.join((len(fromPathList) * [".."])) or '.'
        downDirs = '/'.join(toPathList)
        if downDirs:
            downDirs = '/' + downDirs
        return upDots + downDirs
