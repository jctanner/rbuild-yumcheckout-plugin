#from repomd import kindred
from rbuild_plugins.yumcheckout.repomd import kindred
import rpmcapsule
import stringfunctions

def processYumReposKindred(yumrepos):


    """
    x86_64 and i386 rpms typically go into the same recipe if
    the package has both arches available. This module uses the
    term "kindred" to define that affinity and correllates the
    various architectures found for a package into a dictionary
    with a key by package name.

    Conary also doesn't have the concept of "noarch". Every
    package has a flavor, so a noarch would be added to x86
    and x86_64
    """

    #import epdb; epdb.st()
    kindredpkgs = kindred.findKindredPkgs(yumrepos.latestpackages) 

    # combined dictionary of package names and their recipes 
    outputrecipes = {}

    for key in sorted(kindredpkgs.keys()):
        # skip any packages that exist locally or upstream
        if (kindredpkgs[key][0].upstream == False) and (kindredpkgs[key][0].downstream == False):

            x64pkg = ''
            x86pkg = ''

            x64url = ''
            x86url = ''

            # Handle i386, x86_64 and noarch

            for pkg in kindredpkgs[key]:

                if (pkg.name.startswith('factory')):
                    #import epdb; epdb.st()
                    print "%s starts with the word factory, skipping" % pkg.name
                    #continue
                    break

                #import epdb; epdb.st()    

                if pkg.arch == 'x86_64':
                    x64pkg = pkg
                    #x64url = yumrepo.url +  x64pkg.url
                    x64url = x64pkg.repourl +  x64pkg.url
                elif pkg.arch == 'i386':
                    x86pkg = pkg
                    #x86url = yumrepo.url  +  x86pkg.url
                    x86url = x86pkg.repourl  +  x86pkg.url
                elif pkg.arch == 'i686':
                    x86pkg = pkg
                    #x86url = yumrepo.url  +  x86pkg.url
                    x86url = x86pkg.repourl  +  x86pkg.url
                elif pkg.arch == 'noarch':
                    # use noarch for both flavors
                    x64pkg = pkg
                    x86pkg = pkg
                    #x64url = yumrepo.url  +  x64pkg.url
                    #x86url = yumrepo.url  +  x86pkg.url
                    x64url = x64pkg.repourl +  x64pkg.url
                    x86url = x86pkg.repourl  +  x86pkg.url
                
                # Make an rpmcapsuleRecipe object
                conaryversion = stringfunctions.rpmVersionToConaryVersion(pkg.version, pkg.release)
                test = rpmcapsule.rpmCapsuleRecipe(pkg.name, conaryversion)

                #if (pkg.name == 'Engineering-Server-meta'):
                #    import epdb; epdb.st()

                # See if there are any templates for this pkg name
                if (test.checkTemplateByName(pkg.name)):
                    recipe = test.generateRecipeByName(x86url, x64url)
                    #print recipe
                    outputrecipes[pkg.name] = recipe
                else:

                    # if no i386 exists
                    if ((x86pkg == '') and (x64pkg != '')):
                        recipe = test.defaultCapsuleRecipe64only(x64url)
                        #print recipe
                        outputrecipes[pkg.name] = recipe
                    # if no x86_64 exists
                    elif ((x64pkg == '') and (x86pkg != '')):
                        recipe = test.defaultCapsuleRecipe(x86url, x86url)
                        #print recipe
                        outputrecipes[pkg.name] = recipe
                    # anything else use default
                    else:
                        recipe = test.defaultCapsuleRecipe(x86url, x64url)
                        #print recipe
                        outputrecipes[pkg.name] = recipe

    return outputrecipes
