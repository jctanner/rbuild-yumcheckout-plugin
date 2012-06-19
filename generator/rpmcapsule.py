from genshi.template import TemplateLoader
from genshi.template import TextTemplate
#from rbuild_plugins.yumcheckout.genshi.template import TemplateLoader
#from rbuild_plugins.yumcheckout.genshi.template import TextTemplate
import os
#import rbuild_plugins.yumcheckout.generator.stringfunctions
from  rbuild_plugins.yumcheckout.generator import stringfunctions

class rpmCapsuleRecipe(object):

    """ 
    An object with methods to add a rpm url into 
    a templatized conary recipe. Initialization
    requires a package name and a version. The 
    version should be the rpm NE(VR)A version +
    release. 

    The goal is to check the template directory
    for any templates that have the same name
    as the package, and prefer those. If no 
    matching template is found, then use a 
    default.

    """

    # need to send both the 32 and 64 bit rpm
    # noarch should be the 32 and 64 bit rpm

    #def __init__(self, packagename, version, x86url, x64url):
    def __init__(self, packagename, conaryversion):
        self.packagename = packagename
        #import epdb; epdb.st()
        self.classname = stringfunctions.rpmToClassName(packagename)
        self.version = conaryversion
        #self.x86url = x86url
        #self.x64url = x64url
        self.loader = TemplateLoader(
            os.path.join(os.path.dirname(__file__), 
            'templates'), auto_reload=True
        )    

    def checkTemplateByName(self, packagename):
    
        #if (packagename == 'Engineering-Server-meta'): 
        #    import epdb; epdb.st()

        path_to_file = '/usr/share/rbuild/plugins/yumcheckout/'
        path_to_file += 'generator/templates/' 
        path_to_file +=  packagename

        if os.path.isfile(path_to_file):    
            return True
        else:
            return False

    def generateRecipeByName(self, x86url, x64url):        
        templ = self.loader.load(self.packagename, cls=TextTemplate)
        recipe = templ.generate(className=self.classname,
                                name=self.packagename,
                                version = self.version,
                                x64url=x64url,
                                x86url=x86url)
        return recipe.render('text')




    def defaultCapsuleRecipe(self, x86url, x64url):
        loader = TemplateLoader(
            os.path.join(os.path.dirname(__file__), 'templates'),
            auto_reload=True
        )

        #import epdb; epdb.st()
        templ = loader.load('capsulerecipe.txt', cls=TextTemplate)
        #import epdb; epdb.st()
        recipe = templ.generate(className=self.classname, 
                                name=self.packagename,
                                version = self.version,
                                x64url=x64url,
                                x86url=x86url)
        #print recipe.render('text')
        return recipe.render('text')

    def defaultCapsuleRecipe64only(self, x64url):
        loader = TemplateLoader(
            os.path.join(os.path.dirname(__file__), 'templates'),
            auto_reload=True
        )

        #import epdb; epdb.st()
        templ = loader.load('capsulerecipe-64-only.txt', cls=TextTemplate)
        #import epdb; epdb.st()
        recipe = templ.generate(className=self.classname, 
                                name=self.packagename,
                                version = self.version,
                                x64url=x64url)
        #print recipe.render('text')
        return recipe.render('text')
