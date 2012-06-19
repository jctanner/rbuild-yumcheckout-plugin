from genshi.template import TemplateLoader
from genshi.template import TextTemplate
#from rbuild_plugins.yumcheckout.genshi.template import TemplateLoader
#from rbuild_plugins.yumcheckout.genshi.template import TextTemplate
import os
#import rbuild_plugins.yumcheckout.generator.stringfunctions
from  rbuild_plugins.yumcheckout.generator import stringfunctions

import datetime

class GroupRecipes(object):

    #def __init__(self, packagename, version, x86url, x64url):
    def __init__(self, yumrepoObj):
        self.yumrepo = yumrepoObj
        self.recipes = {}
        self.loader = TemplateLoader(
            os.path.join(os.path.dirname(__file__), 
            'templates'), auto_reload=True
        )    
       
        self.recipes['group-rpms'] = self.generateGroupRpmsRecipe() 
        #import epdb; epdb.st()
        #return self.recipes

    

    def generateGroupRpmsRecipe(self):        

        name = 'group-rpms'
        classname = stringfunctions.rpmToClassName(name)
        now = datetime.datetime.now()
        datestamp = now.strftime("%Y_%m_%d_%H_%M_%S")
        #datestamp = "NOW"
        pkglist = ""

        for pkg in sorted(self.yumrepo.latestpackages):
            #prefer upstream
            if (pkg.upstreamtrove != ''):
                pkglist += "\t\t\'%s\',\n" % pkg.upstreamtrove
            elif (pkg.localtrove != ''):
                pkglist += "\t\t\'%s\',\n" % pkg.localtrove



        templ = self.loader.load('group-rpms', cls=TextTemplate)
        recipe = templ.generate(className=classname,
                                repourl = self.yumrepo.url,
                                name = name,
                                version = datestamp,
                                packages = pkglist)
        return recipe.render('text')
