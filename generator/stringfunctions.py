import re

def rpmToClassName(rpmname):
    # puppet-stig-mods = PuppetStigMods
   
    classname = "" 

    wordlist = rpmname.split('-')

    for word in wordlist:
        #print word
        classname += word.title()

    #url = re.sub('\.com$', '', url)    
    classname = re.sub('\.', '', classname)

    return classname

def conary2rpmversion(conaryversion):
    p = re.compile(r'(\-)\s*\d{1,2}')
    tmparray =  filter(None, p.split(conaryversion))
    rpmversion = tmparray[0]
    rpmversion = rpmversion.replace('_', '-')   #convert underscores to hyphens 
    return rpmversion

def rpmVersionToConaryVersion(version, release):
    # a-zA-Z0-9()+,.;_~
    conaryversion = version + "-" + release
    conaryversion = conaryversion.replace('-', '_') 
    return conaryversion
