#!/usr/bin/python

import epdb
from xml.dom.minidom import parse, parseString
from urllib2 import urlopen
import urllib2
import StringIO
import gzip
import sgmllib
import re
import os
import itertools

#upstreamcheck
import sys
from conary import conarycfg, conaryclient, trove
from conary import repository
from conary import versions
from conary.lib.compat import namedtuple
from conary.versions import Label
import collections
from difflib import SequenceMatcher

#manfestdirname
import datetime

class yumPackage(object):
    def __init__(self, name, epoch, version, release, arch, location, repourl):
        self.id = id
        self.name = name
        self.epoch = epoch
        self.version = version
        self.release = release
        self.arch = arch
        self.url = location
        self.repourl = repourl
        #self.md5 = ''
        #self.sha1 = ''
        self.sumtype = ''
        self.sum = ''
        self.packager = ''
        self.upstream = False	#exists upstream?
        self.downstream = False	#exists downstream?
        self.matchpercent = 0	#upstream match percentage
        self.dmatchpercent = 0	#downstream match percentage
        self.upstreamtrove = ''	#a full trovespec in string format
        self.localtrove = '' 	#a full trovespec in string format

class yumGroup(object):
    def __init__(self, id):
        self.id = id        #string, not an int
        self.packages = []  #list of packages

    #add a single package
    def addpackage(self, package):
        self.packages.append(package)

    #add a list of packages
    def addpackages(self, packages):
        self.packages.append(list(packages))

class yumRepos(object):
    def __init__(self):
        self.repos = []
        self.packages = []
        self.uniquepackages = []
        self.latestpackages = []
        self.groups = []
        self.upstreamtroves = []	# a list of troves from the upstream label
        self.localtroves = []           # a list of troves in the local label
        #self.rheltroves = []
        print "repos initialized"

    def sortPackages(self):
        self.latestpackages.sort(cmp=lambda x,y: -1 if x.name < y.name else 0 if x.name == y.name else 1)
        self.packages.sort(cmp=lambda x,y: -1 if x.name < y.name else 0 if x.name == y.name else 1)
        self.uniquepackages.sort(cmp=lambda x,y: -1 if x.name < y.name else 0 if x.name == y.name else 1)

    def checkLabelsAPI(self, locallabel, upstreamlabel):
        NEVRA = namedtuple('NEVRA', 'name epoch version release arch')
        dlabel = versions.Label(locallabel)
        ulabel = versions.Label(upstreamlabel)
          
        print "DEBUG: matching packages to local troves" 
        for trvSpec, nevra in self._getNevras(NEVRA, dlabel):

            # ('CSCOsars:rpm', VFS('/celmb1.cisco.com@c:celmb1-trunk-devel/1.0.1_0-1-1'), Flavor('is: x86_64'))
            # trvSpec[0] = 'CSCOsars:rpm'
            # trvSpec[1] = VFS('/celmb1.cisco.com@c:celmb1-trunk-devel/1.0.1_0-1-1')
            # trvSpec[2] = Flavor('is: x86_64')

            #print "\t\t%s" % trvSpec 
            #print "%s" % nevra.name 

            for pkg in self.latestpackages:
                trovespec = ""
                #print "\t%s" % pkg.name

                # Why is nevra.epcoh = None ?

                if ((pkg.name == nevra.name) and
                   (pkg.version == nevra.version) and 
                   (pkg.release == nevra.release) and
                   (pkg.arch == nevra.arch)):
                   
                   trovespec = str(nevra.name) + "=" + str(trvSpec[1]) + "[" + str(trvSpec[2]) + "]"  
                   pkg.localtrove = trovespec

                   print "MATCH: %s %s" %(pkg.url, trovespec)
                   #epdb.st()

        print "DEBUG: matching packages to upstream troves" 
        for trvSpec, nevra in self._getNevras(NEVRA, ulabel):

            # ('CSCOsars:rpm', VFS('/celmb1.cisco.com@c:celmb1-trunk-devel/1.0.1_0-1-1'), Flavor('is: x86_64'))
            # trvSpec[0] = 'CSCOsars:rpm'
            # trvSpec[1] = VFS('/celmb1.cisco.com@c:celmb1-trunk-devel/1.0.1_0-1-1')
            # trvSpec[2] = Flavor('is: x86_64')

            #print "\t\t%s" % trvSpec 
            #print "%s" % nevra.name 

            #self.latestpackages.sort()

            #epdb.st()
            for pkg in self.latestpackages:
                trovespec = ""
                #print "\t%s" % pkg.name

                # Why is nevra.epcoh = None ?

                if ((pkg.name == nevra.name) and
                   (pkg.version == nevra.version) and 
                   (pkg.release == nevra.release) and
                   (pkg.arch == nevra.arch)):
                   
                   trovespec = str(nevra.name) + "=" + str(trvSpec[1]) + "[" + str(trvSpec[2]) + "]"  
                   pkg.upstreamtrove = trovespec

                   print "MATCH: %s %s" %(pkg.url, trovespec)
                   #epdb.st()



    
    def _getNevras(self, NEVRA, label):
        cfg = conarycfg.ConaryConfiguration(True)
        client = conaryclient.ConaryClient(cfg)
    
        tvers = client.repos.getTroveVersionsByLabel({None: {label: None}})
    
        specs = []
        #for n, vs in tvers.iteritems():
        for n, vs in iter(sorted(tvers.iteritems())):
            if not n.endswith(':rpm'):
                continue
            for v, fs in vs.iteritems():
                for f in fs:
                    specs.append((n, v, f))
    
        capsuleInfo = client.repos.getTroveInfo(trove._TROVEINFO_TAG_CAPSULE, specs)

        #sort by name, version and commit date
        specs.sort()
    
        for spec, info in itertools.izip(specs, capsuleInfo):
            r = info.rpm
            nevra = NEVRA(r.name(), r.epoch(), r.version(), r.release(), r.arch())
            yield spec, nevra
    
    def checkLocalSources(self):

        tmppackages = []

        for pkg in self.latestpackages:
            pkgfullversion = pkg.version + '-' + pkg.release
            match = 'NULL'
            bestratio = 0
            downstream = False

            for trove in self.localtroves:
                conarypkgname = str(trove[0])
                if (pkg.name == conarypkgname):
                    #epdb.st()
                    flavor = str(trove[2])
                    trovearch = flavor2arch(flavor)
                    if (pkg.arch == "noarch"):
                        checkarch = 'x86_64'
                    else:
                        checkarch = pkg.arch

                    if ((checkarch == trovearch) and (bestratio != 1)):
                        versionarray = str(trove[1]).split('/')
                        label = versionarray[1]
                        conaryversion = versionarray[2]
                        conaryrpmversion = conary2rpmversion(conaryversion)
                        if (pkgfullversion == conaryrpmversion):
                            bestratio = 1
                            downstream = True
                            match = conarypkgname + '=/' + label + '/' + conaryversion + '[' + flavor + ']'
                            print "DEBUG: %s    %s == %s-%s" % (pkg.name, conaryversion, pkg.version, pkg.release)
                        elif(bestratio < 1):
                            m = SequenceMatcher(None, conaryrpmversion, pkgfullversion)
                            if (m.ratio() > bestratio):
                                bestratio = m.ratio()
                                downstream = True
                                match = conarypkgname + '=/' + label + '/' + conaryversion + '[' + flavor + ']'
                                print "DEBUG: %s    %s == %s-%s by %s percent" %  (pkg.name,
                                              conaryversion, pkg.version, pkg.release, m.ratio())
                    
            #set the package attributes if match found
            if downstream == True:
                pkg.downstream = True
                pkg.localtrove = match
                pkg.dmatchpercent = bestratio
            else:
                pkg.downstream = False
                pkg.localtrove = 'NULL'
                pkg.matchpercent = 0
  

    def checkUpstreamSources(self):

        tmppackages = []
        for pkg in self.latestpackages:
            pkgfullversion = pkg.version + '-' + pkg.release

            match = 'NULL'
            bestratio = 0
            upstream = False

            for trove in self.upstreamtroves:
                # ('nspr:rpm', VFS('/rhel.rpath.com@rpath:rhel-5-server/4.7.6_1.el5_4-1-1'), Flavor('is: x86(i486,i586,i686)'))
                # str(trove[0]) = 'nspr:rpm'
                # str(trove[1]) = '/rhel.rpath.com@rpath:rhel-5-server/4.7.6_1.el5_4-1-1'
                # str(trove[2]) = 'is: x86(i486,i586,i686)'
                #match = 'NULL'
                #bestratio = 0
                #upstream = False
                conarypkgname = str(trove[0]) 
                if (pkg.name == conarypkgname):
                    #print "DEBUG: %s matches %s" % (pkg.name, conarypkgname)
                    flavor = str(trove[2])
                    trovearch = flavor2arch(flavor)
                    if (pkg.arch == "noarch"):
                        checkarch = 'x86_64'
                    else:
                        checkarch = pkg.arch

                    #epdb.st()
                    #if ((pkg.arch == trovearch) or (bestratio != 1)):
                    #if ((pkg.arch == trovearch) and (bestratio != 1)):
                    #if (((pkg.arch == trovearch)  or (pkg.arch == 'noarch')) and (bestratio != 1)):
                    if ((checkarch == trovearch) and (bestratio != 1)):
                        #print "DEBUG:     %s / %s matches %s" % (flavor, trovearch, pkg.arch)
                        # ['', 'rhel.rpath.com@rpath:rhel-5-server', '1.0.10_16.el5-1-1']
                        versionarray = str(trove[1]).split('/')
                        label = versionarray[1]
                        conaryversion = versionarray[2]
                        conaryrpmversion = conary2rpmversion(conaryversion)
                        if (pkgfullversion == conaryrpmversion):
                            bestratio = 1 
                            upstream = True
                            match = conarypkgname + '=/' + label + '/' + conaryversion + '[' + flavor + ']'
                            print "DEBUG: %s    %s == %s-%s" % (pkg.name, conaryversion, pkg.version, pkg.release)  
                        elif(bestratio < 1):
                            #m = SequenceMatcher(None, conaryrpmversion, pkg.version)
                            m = SequenceMatcher(None, conaryrpmversion, pkgfullversion)
                            #epdb.st()
                            if (m.ratio() > bestratio):
                                bestratio = m.ratio()
                                if (m.ratio() >= .9):
                                    upstream = True
                                    match = conarypkgname + '=/' + label + '/' + conaryversion + '[' + flavor + ']'
                                    print "DEBUG: %s    %s == %s-%s by %s percent" %  (pkg.name, 
                                                  conaryversion, pkg.version, pkg.release, m.ratio())  

            #set the package attributes if match found
            #if match != 'NULL':
            if upstream == True:
                pkg.upstream = True
                pkg.upstreamtrove = match
                pkg.matchpercent = bestratio
            else:
                pkg.upstream = False
                pkg.upstreamtrove = 'NULL'
                pkg.matchpercent = 0

            #epdb.st()
            print "DEBUG: add %s, %s, %s to tmppackages[]" % (pkg.name, pkgfullversion, pkg.upstreamtrove)
            tmppackages.append(pkg)
                    
        self.latestpackages = [] 
        self.latestpackages = self.latestpackages + tmppackages
                    


    def checkUpstreamSourcesSLOW(self):
        #fileHandle = open ( fileName, 'w' )

        '''
        for pkg in self.packages:
            print "%s-%s-%s.%s.rpm %s %s/%s" % (pkg.name, pkg.version, pkg.release, pkg.arch, pkg.sum, pkg.repourl, pkg.url)
            fileHandle.write("%s-%s-%s.%s.rpm %s %s/%s\n" % (pkg.name, pkg.version, pkg.release, pkg.arch, pkg.sum, pkg.repourl, pkg.url))
        '''

        #for pkg in self.packages:
        for pkg in self.latestpackages:
            #checkupstream: isInLabel(pkgname, pkgversion, pkgarch, pkglabel)
            pkgfullversion = pkg.version + '-' + pkg.release
            #upstream = isInLabel(pkg.name, pkg.version, pkg.arch, 'rhel.rpath.com@rpath:rhel-5-server')
            upstream = isInLabel(pkg.name, pkgfullversion, pkg.arch, 'rhel.rpath.com@rpath:rhel-5-server')
            if (upstream != 'NULL'):
                pkg.upstream = True
                pkg.upstreampackage = upstream
            #fileHandle.write("\"%s-%s-%s.%s.rpm\";\"%s\";\"%s\",\"%s/%s\",\"%s\"\n" % 
	    #	(pkg.name, pkg.version, pkg.release, pkg.arch, pkg.sum, pkg.packager, pkg.repourl, pkg.url, upstream))

        #fileHandle.close()


    def outputMissingPackages(self, directoryName):
        if not os.path.exists(directoryName):
            os.mkdir(directoryName)

        filename = directoryName + '/' + 'manifest.missing.packages'
        filehandle = open ( filename, 'w' )
       
        #prefer upstream
        for pkg in self.latestpackages:
            if (pkg.upstreamtrove != ''):
                pass
            elif (pkg.localtrove != ''):
                pass
            else:
                filehandle.write("\"%s\";\"%s-%s-%s.%s.rpm\";\"%s\";\"%s\";\"%s/%s\";\"%s\";\"%s\"\n" %
                    (pkg.name, pkg.name, pkg.version, pkg.release, 
                     pkg.arch, pkg.sum, pkg.packager, 
                     pkg.repourl, pkg.url, pkg.upstreamtrove, pkg.localtrove))

        filehandle.close()
        

    def outputPackageManifest(self, directoryName):

        if not os.path.exists(directoryName):
            os.mkdir(directoryName)

        manifestFileName = directoryName + '/' + 'manifest.latest.packages'
        fullmanifestFileName = directoryName + '/' + 'manifest.all.packages'
        uniquemanifestFileName = directoryName + '/' + 'manifest.unique.packages'
        #manifestGroupFileName = directoryName + '/' + 'manifest.groups'
        #groupRecipeFileName = directoryName + '/' + 'group-yumrepos.recipe'
        mbIncludeListFileName = directoryName + '/' + 'updatebotrc-includePackages' 
        mbExcludeListFileName = directoryName + '/' + 'updatebotrc-excludePackages'
       
        manifestFileHandle = open ( manifestFileName, 'w' )
        fullmanifestFileHandle = open ( fullmanifestFileName, 'w' )
        uniquemanifestFileHandle = open ( uniquemanifestFileName, 'w' )
        #manifestGroupFileHandle = open ( manifestGroupFileName, 'w' )
        #groupRecipeFileHandle = open ( groupRecipeFileName, 'w' )
        mbIncludeFileHandle = open ( mbIncludeListFileName, 'w' )
        mbExcludeFileHandle = open ( mbExcludeListFileName, 'w' )

        includelist = []
        excludelist = []

        #epdb.st()
        for pkg in self.uniquepackages:
            uniquemanifestFileHandle.write("\"%s-%s-%s.%s.rpm\";\"%s\";\"%s\";\"%s/%s\";\"%s\";\"%s\"\n" %
                (pkg.name, pkg.version, pkg.release, pkg.arch, pkg.sum, pkg.packager, pkg.repourl, pkg.url, pkg.upstreamtrove, pkg.localtrove))
 
        for pkg in self.packages:
            fullmanifestFileHandle.write("\"%s-%s-%s.%s.rpm\";\"%s\";\"%s\";\"%s/%s\";\"%s\";\"%s\"\n" %
                (pkg.name, pkg.version, pkg.release, pkg.arch, pkg.sum, pkg.packager, pkg.repourl, pkg.url, pkg.upstreamtrove, pkg.localtrove))

        for pkg in self.latestpackages:
            #manifest
            manifestFileHandle.write("\"%s-%s-%s.%s.rpm\";\"%s\";\"%s\";\"%s/%s\";\"%s\";\"%s\"\n" % 
		(pkg.name, pkg.version, pkg.release, pkg.arch, pkg.sum, pkg.packager, pkg.repourl, pkg.url, pkg.upstreamtrove, pkg.localtrove))

            #includes
            if (pkg.upstream == False):
                includelist.append(pkg.name)

            #excludes
            if (pkg.upstream == True):
                excludelist.append(pkg.name)

        includelist = sorted(set(includelist))
        for p in includelist:
            mbIncludeFileHandle.write("package %s\n" % p)
     
        excludelist = sorted(set(excludelist))
        for p in excludelist:
            mbExcludeFileHandle.write("excludePackages %s\n" % p)

        manifestFileHandle.close()
        fullmanifestFileHandle.close()
        uniquemanifestFileHandle.close()
        mbIncludeFileHandle.close()
        mbExcludeFileHandle.close()


    def outputGroupManifest(self, directoryName):

        if not os.path.exists(directoryName):
            os.mkdir(directoryName)

        manifestGroupFileName = directoryName + '/' + 'manifest.groups'
        manifestGroupFileHandle = open ( manifestGroupFileName, 'w' )

        '''
        manifestGroupFileHandle.write("groups = {\n")
        for g in self.uniquegroups:
            cgroupname = "group-" + g.id
            manifestGroupFileHandle.write("    \'%s\':[" % cgroupname) 
            for p in g.packages:
                manifestGroupFileHandle.write("\'%s\', " % p)    
            manifestGroupFileHandle.write("],\n")
        manifestGroupFileHandle.write("}\n")
        '''

        #make a csv list of groups and packages
        for g in self.uniquegroups:
            cgroupname = "group-" + g.id
            manifestGroupFileHandle.write("\"%s\";" % cgroupname)
            for p in g.packages:
                manifestGroupFileHandle.write("\'%s\'; " % p)
            manifestGroupFileHandle.write("\n")

        manifestGroupFileHandle.close()



    def outputGroupRecipe(self, directoryName):

        if not os.path.exists(directoryName):
            os.mkdir(directoryName)

        groupRecipeFileName = directoryName + '/' + 'group-yumrepos.recipe'
        groupRecipeFileHandle = open ( groupRecipeFileName, 'w' )

        #make a group recipe 
        groupRecipeFileHandle.write("class GroupYumRepos(GroupSetRecipe):\n")
        groupRecipeFileHandle.write("    name = 'group-yumrepos'\n")
        groupRecipeFileHandle.write("    version = '1'\n")
        groupRecipeFileHandle.write("\n")
        groupRecipeFileHandle.write("    buildRequires = []\n")
        groupRecipeFileHandle.write("\n")
        groupRecipeFileHandle.write("    def setup(r):\n")
        groupRecipeFileHandle.write("\n")
        groupRecipeFileHandle.write("        Use.xen.setPlatform(False)\n")
        groupRecipeFileHandle.write("        Use.domU.setPlatform(False)\n")
        groupRecipeFileHandle.write("        Use.dom0.setPlatform(False)\n")
        groupRecipeFileHandle.write("        Use.vmware.setPlatform(False)\n")
        groupRecipeFileHandle.write("\n")
        groupRecipeFileHandle.write("        r.dumpAll()\n")
        groupRecipeFileHandle.write("        rhel = r.Repository('rhel.rpath.com@rpath:rhel-5-server', r.flavor)\n")
        groupRecipeFileHandle.write("        rhelCommon = r.Repository('rhel.rpath.com@rpath:rhel-5', r.flavor)\n")
        groupRecipeFileHandle.write("        #mbrepo = r.Repository('cel55.cisco.com@cisco:cel55-development-devel', r.flavor)\n")
        groupRecipeFileHandle.write("        mbrepo = r.Repository(r.cfg.buildLabel, r.flavor)\n")
        groupRecipeFileHandle.write("        upstreamObj = rhel.find('group-os=/rhel.rpath.com@rpath:rhel-5-server/2011.01.11_0500.00-1-1')\n")
        groupRecipeFileHandle.write("        cel = mbrepo.latestPackages()\n")
        groupRecipeFileHandle.write("        tmpSearchObj = r.SearchPath(cel, mbrepo, upstreamObj)\n")
        groupRecipeFileHandle.write("        celPackages = r.yumPackages()\n")
        groupRecipeFileHandle.write("        celGroups = r.yumGroups()\n")
        groupRecipeFileHandle.write("        patchedOS = tmpSearchObj.find(*celPackages)\n")
        groupRecipeFileHandle.write("        mastergroup = patchedOS.createGroup('group-os', checkPathConflicts=False)\n")
        groupRecipeFileHandle.write("        searchObj = r.SearchPath(patchedOS)\n")
        groupRecipeFileHandle.write("        #sortedgroupnames = sorted(set(celGroups))\n")
        groupRecipeFileHandle.write("        #for groupname in sortedgroupnames:\n")
        groupRecipeFileHandle.write("        for key in celGroups.keys():\n")
        groupRecipeFileHandle.write("            #packages = celGroups[groupname]\n")
        groupRecipeFileHandle.write("            packages = celGroups[key]\n")
        groupRecipeFileHandle.write("            pkgtrvset = searchObj.find(*packages)\n")
        groupRecipeFileHandle.write("            pkgtrvset.dump()\n")
        groupRecipeFileHandle.write("            mastergroup += pkgtrvset.createGroup(key)\n")
        groupRecipeFileHandle.write("        mastergroup += rhelCommon['group-rpath-packages']\n")
        groupRecipeFileHandle.write("        r.Group(mastergroup, checkPathConflicts=False)\n")
        groupRecipeFileHandle.write("\n")

        groupRecipeFileHandle.write("    def yumGroups(r):\n")
        groupRecipeFileHandle.write("        groups = {\n")

        grouphash = {}   		#create tempory hash to sort
        for g in self.uniquegroups:
            grouphash[g.id] = g.packages

        #epdb.st()

        keys = sorted(grouphash.keys())
        #grouphash = sorted(set(grouphash))

        #epdb.st() 

        #for key in grouphash.keys():
        for key in keys:
            groupRecipeFileHandle.write("            \'%s\':[" % ("group-" + key))
            for p in grouphash[key]:
                groupRecipeFileHandle.write("\'%s\', " % p)
            groupRecipeFileHandle.write("],\n")
        groupRecipeFileHandle.write("        }\n")
        groupRecipeFileHandle.write("        return groups\n")
        groupRecipeFileHandle.write("\n")        


        '''
        for g in self.uniquegroups:
            cgroupname = "group-" + g.id
            groupRecipeFileHandle.write("            \'%s\':[" % cgroupname)
            for p in g.packages:
                groupRecipeFileHandle.write("\'%s\', " % p)
            groupRecipeFileHandle.write("],\n")
        groupRecipeFileHandle.write("        }\n")
        groupRecipeFileHandle.write("        return groups\n")
        groupRecipeFileHandle.write("\n")
        '''

        groupRecipeFileHandle.write("    def yumPackages(r):\n")
        groupRecipeFileHandle.write("        packages = [\n")
        pkglist = []
        for pkg in self.latestpackages:

            '''
            #notupstream
            if (pkg.upstream == False):
                #groupRecipeFileHandle.write("            \'%s\',\n" % pkg.name)
                pkglist.append(pkg.name)

            #isupstream
            if (pkg.upstream == True):
                #groupRecipeFileHandle.write("            \'%s\',\n" % pkg.upstreamtrove)
                pkglist.append(pkg.upstreamtrove)
            '''

            #prefer upstream
            if (pkg.upstreamtrove != ''):
                #pkglist.append(pkg.upstreamtrove)
                groupRecipeFileHandle.write("            \'%s\',\n" % pkg.upstreamtrove)
            elif (pkg.localtrove != ''):
                #pkglist.append(pkg.localtrove)
                groupRecipeFileHandle.write("            \'%s\',\n" % pkg.localtrove)
            else:
                #missingpkg = "#" + str(pkg.name)
                #pkglist.append(missingpkg)
                groupRecipeFileHandle.write("            #\'%s\', #%s\n" % (pkg.name, pkg.url))

        #pkglist = sorted(set(pkglist))

        #for p in pkglist:
        #    groupRecipeFileHandle.write("            \'%s\',\n" % p) 

        groupRecipeFileHandle.write("        ]\n")
        groupRecipeFileHandle.write("        return packages\n")
            

        #manifestGroupFileHandle.close()
        groupRecipeFileHandle.close()
       

    def createLabelMap(self, label):
        print "DEBUG: mapping upstream troves to list"
        self.upstreamtroves=labelMap(label)

    def createLocalMap(self, label):
        print "DEBUG: mapping downstream troves to list"
        self.localtroves=labelMap(label)

    def addPackagesFromRepo(self, repo):    
        for pkg in repo.packages:
            #self.packages.append(pkg.name)
            self.packages.append(pkg)

        # FIXME, ugly.
        sorted(set(self.packages))

    def addGroupsFromRepo(self, repo):
        for group in repo.groups:
            self.groups.append(group)

    def uniquePackages(self):
        self.uniquepackages = []
        uniquehash = {}
        for pkg in self.packages:
            key = pkg.name + "-" + pkg.version + "-" + pkg.release + "-" + pkg.epoch + "-" + pkg.arch      
            if not uniquehash.has_key(key):
                uniquehash[key] = pkg

        for key in uniquehash.keys():
            self.uniquepackages.append(uniquehash[key])    

    def uniqueGroups(self):
        self.uniquegroups = []
        uniquehash = {}
        for group in self.groups:
            if not uniquehash.has_key(group.id):
                uniquehash[group.id] = group

        for key in uniquehash.keys():
            self.uniquegroups.append(uniquehash[key])

    def latestPackages(self):
        self.latestpackages = []
        latesthash = {}
        #for pkg in self.uniquepackages:
        for pkg in self.uniquepackages:
            key = pkg.name + "-" + pkg.arch
            if not latesthash.has_key(key):
                latesthash[key] = pkg
            else:
                #if key is "kernel-x86_64":
                #    epdb.st()
                #if self.pkgIsOlder(latesthash[key], pkg):
                if self.pkgIsNewer(pkg, latesthash[key]):
                    latesthash[key] = pkg

        for key in latesthash.keys():
            self.latestpackages.append(latesthash[key])    
        #epdb.st()            
       

    def pkgIsNewer(self, p, q):
        # p is newer than q ?
        if p.name == q.name:
            if p.version > q.version:
                return True
            elif p.version == q.version:
                if p.release > q.release:
                    return True
                elif p.release == q.release:
                    if p.epoch > q.epoch:
                        return True          
                    elif p.epoch == q.epoch:
                        return False    
                    else:
                        return False   
                else:
                    return False        
            else:
                return False        
                     

    def addRepo(self, repo):
        self.repos.append(repo)
        self.addPackagesFromRepo(repo)
        self.uniquePackages()
        self.addGroupsFromRepo(repo)
        self.uniqueGroups()

    def createRepo(self, url):
        print "adding repo"
        X = yumRepo(url)
        self.addRepo(X)

    def findAllLatestPackages(self):
        manifest = []
        for pkg in self.packages:
            #epdb.st()
            manifest.append(self.findLatestPackage(pkg.name, pkg.arch))
        return manifest

class yumRepo(object):
    def __init__(self, url):
        #self.id = id
        self.url = url
        self.repodataurl = ""
        self.metafiles = []
        self.primarymetafiles = []
        self.groupmetafiles = []
        self.packages = []
        self.groups = []

        #self.getUrl()
        self.findMetaFiles()
        self.parseRepomd()
        self.parsePrimaryXML()
        self.parseCompsXML()

    def getUrl(self):
        print self.url

    def addPackage(self, package):
        print "INFO: adding %s" % package.name
        self.packages.append(package)

    def listPackages(self):
        for pkg in self.packages:
            print "%s-%s-%s-%s.rpm" % (pkg.name, pkg.version, pkg.release, pkg.arch)


    def uniquepPackages(self):
        pass

    def findLatestPackageVer(self, pkgname, arch):
        latestpkg = yumPackage(pkgname, '0', '0', '0', '0', '', '')
        for pkg in self.packages:        
            if (pkg.name == pkgname) and (pkg.arch == arch):
                if (pkg.version > latestpkg.version):
                    if (pkg.release >= latestpkg.release): 
                        if (pkg.epoch >= latestpkg.epoch):
                            latestpkg.version = pkg.version
                            latestpkg.release = pkg.release
                            latestpkg.epoch = pkg.epoch
                            latestpkg.arch = pkg.arch
                            latestpkg.repourl = pkg.repourl
                            latestpkg.url = pkg.url
                            print "INFO:    %s is latest for %s " % (latestpkg.url, self.url)
                            #epdb.st()
                else:
                    #epdb.st()
                    print "INFO:    %s !> %s" % (pkg.url, latestpkg.url)
        return latestpkg           

    def addGroup(self, group):
        self.groups.append(group)

    def parseRepomd(self):
        for filename in self.metafiles:
            if re.search('repomd', filename):
                print "INFO: repomd file = %s" % filename
                # get repomd
                compdom = parse(urlopen(self.repodataurl + "/" + filename))
                for node in compdom.getElementsByTagName('data'):
                    nodetype = node.attributes['type'].value
                    #from conary.lib import epdb; epdb.st()
                    #method 1
                    #nodelocation = node.childNodes[1].attributes['href'].value
                    #method 2
                    nodelocation = node.getElementsByTagName('location')[0].attributes['href'].nodeValue
                   
                    print "INFO: xmlurl -- %s %s" % (nodetype, nodelocation) 

                    if nodetype.encode('utf8') in "primary":
                        print "INFO: add %s as primary" % nodelocation
                        self.primarymetafiles.append(nodelocation.encode('utf8'))
                    if nodetype.encode('utf8') in "group":
                        print "INFO: add %s as comps" % nodelocation
                        self.groupmetafiles.append(nodelocation.encode('utf8'))

                # get primary filename
                # get comps filename

        #import epdb; epdb.st()

    def findMetaFiles(self):
        #epdb.st()
        repourl = self.url + "/repodata"
        #epdb.st()
        print "INFO: attemping to parse %s" % repourl
        req = urllib2.Request(repourl)
        response = urllib2.urlopen(req)

        if response.code is "200":
            print "ERROR: repository does not have a repodata directory"
            return
        self.repodataurl = repourl

        data = response.read()
        parser = MyParser()
        parser.parse(data)
        for filename in parser.get_hyperlinks():
            #print filename
            if re.search('xml', filename):
                print "INFO: add %s to metafiles" % filename
                self.metafiles.append(filename)

        # HTML != XML ... can't use parse
        #compdom = parse(urlopen(repourl)) 
        #compdom = parse(response.read())

        #import epdb; epdb.st()


    def parsePrimaryXML(self):
        print "INFO: parsing primary.xml"
        for filename in self.primarymetafiles:
            #import epdb; epdb.st()
            if filename.endswith('.gz'):
                print "INFO: %s is compressed, retrieving %s " % (filename, (self.url + "/" + filename))
                resp = urlopen(self.url + "/" + filename)
                output = StringIO.StringIO()
                output.write(resp.read())
                output.seek(0)
                decompressed = gzip.GzipFile(fileobj=output)
                #xml = decompressed.read()
                #compdom = parse(decompressed.read())
                #compdom = parse(xml)
                compdom = parse(decompressed)
                for node in compdom.getElementsByTagName('package'): 
                    #epdb.st()
                 
                    pkgname = node.getElementsByTagName('name')[0].childNodes[0].nodeValue.encode('utf8')
                    pkgarch = node.getElementsByTagName('arch')[0].childNodes[0].nodeValue.encode('utf8')
                    pkgepoch = node.getElementsByTagName('version')[0].attributes['epoch'].value.encode('utf8')
                    pkgvers = node.getElementsByTagName('version')[0].attributes['ver'].value.encode('utf8')
                    pkgrel = node.getElementsByTagName('version')[0].attributes['rel'].value.encode('utf8')
                    pkgloc = node.getElementsByTagName('location')[0].attributes['href'].value.encode('utf8')
                    pkgsumtype = node.getElementsByTagName('checksum')[0].attributes['type'].value.encode('utf8')
                    pkgsum = node.getElementsByTagName('checksum')[0].childNodes[0].nodeValue.encode('utf8')
                    try:
                        pkgpackager = node.getElementsByTagName('packager')[0].childNodes[0].nodeValue.encode('utf8')
                    except:
                        pkgpackager = 'none'

                    #from conary.lib import epdb; epdb.st()

                    # name, epoch, version, release, arch, location
                    package = yumPackage(pkgname, pkgepoch, pkgvers, pkgrel, pkgarch, pkgloc, self.url)
                    package.sumtype = pkgsumtype
                    package.sum = pkgsum
                    package.packager = pkgpackager
                    self.addPackage(package)
            else:
                print "INFO: %s is not compressed" % filename

    def parseCompsXML(self):

        missingpackages = ['bsh-groupfile',
                           'ctdb',
                           'ctdb-devel',
                           'ecs-groupfile',
                           'kernel-debug',
                           'kernel-debug-devel',
                           'kernel-xen',
                           'kernel-xen-devel',
                           'kmod-be2iscsi-xen-rhel5u5',
                           'kmod-be2net-xen-rhel5u5',
                           'kmod-cmirror',
                           'kmod-cmirror-xen',
                           'kmod-gfs kmod-gfs-xen',
                           'kmod-gnbd kmod-gnbd-xen',
                           'kmod-igb-xen-rhel5u5',
                           'kmod-lpfc-xen-rhel5u5',
                           'serviceguard',
                           'sgcmom',
                           'vmware-open-vm-tools-common',
                           'vmware-open-vm-tools-nox',
                           'kmod-gfs',
                           'kmod-gfs-xen',
                           'kmod-gnbd',
                           'kmod-gnbd-xen'
                          ]

        conflictpackages = ['samba3x', 'samba3x-client', 'samba3x-common',
                            'samba3x-swat', 'samba3x-winbind'
                            'postgresql184', 'postgresql84-contrib', 'postgresql84-devel'
                            'postgresql84-docs', 'postgresql84-plperl', 'postgresql84-plpython'
                            'postgresql84-pltcl', 'postgresql84-python', 'postgresql84-server',
                            'postgresql84-tcl','postgresql84-test',
                            'php53', 'php53-bcmath', 'php53-cli', 'php53-dba', 'php53-devel',
                            'php53-gd', 'php53-imap', 'php53-ldap', 'php53-mbstring',
                            'php53-mysql', 'php53-odbc', 'php53-pdo', 'php53-pgsql'
                            'php53-snmp', 'php53-soap', 'php53-xml', 'php53-xmlrpc',
                            'freeradius2', 'freeradius2-ldap', 'freeradius2-utils',
                            'bind97', 'bind97-devel', 'bind97-utils'
                            ]

        badpackages = ['cisco-vm-grub-config']

        excludepackages = list(missingpackages)
        excludepackages += list(conflictpackages)
        excludepackages += badpackages


        #debug
        excludepackages = conflictpackages
        #excludegroups = ['cisco-patchbundle-nonreboot']    
        excludegroups = []

        for filename in self.groupmetafiles:
            print "DEBUG: handling %s" % filename

            try:
                print "DEBUG: getting comps from %s" % (self.url + "/" + filename)
            except:
                epdb.st()

            print "DEBUG: getting comps from %s" % (self.url + "/" + filename)
            compdom = parse(urlopen(self.url + "/" + filename))
            for node in compdom.getElementsByTagName('group'):
                #find the id for this group in the dom
                group_id = node.getElementsByTagName('id')[0].childNodes[0].nodeValue

                conarygroupname = "" + group_id.encode('utf-8')
                conarygroupname = conarygroupname.lower()
                conarygroupname = re.sub('\s+','-',conarygroupname)
                conarygroupname = re.sub('/','-',conarygroupname)
                conarygroupname = re.sub('\(','',conarygroupname)
                conarygroupname = re.sub('\)','',conarygroupname)
                grp = yumGroup(conarygroupname)

                print "DEBUG: processing group - %s" % grp.id

                packages = node.getElementsByTagName('packagereq')

                for package in packages:
                    #use the value of the first index for each package name
                    pname = package.childNodes[0].nodeValue
                    print "DEBUG: \tpackage: %s" % pname
                    #add packagename to the yumgroup object
                    if pname.encode('utf-8') not in excludepackages:
                        grp.addpackage(pname.encode('utf-8'))

                #add this group to the list of all groups
                if conarygroupname not in excludegroups:
                    #grpMap.append(grp) 
                    self.groups.append(grp)

            print "DEBUG: comps processed from % s" % self.url

class MyParser(sgmllib.SGMLParser):
    "A simple parser class."

    def parse(self, s):
        "Parse the given string 's'."
        self.feed(s)
        self.close()

    def __init__(self, verbose=0):
        "Initialise an object, passing 'verbose' to the superclass."

        sgmllib.SGMLParser.__init__(self, verbose)
        self.hyperlinks = []

    def start_a(self, attributes):
        "Process a hyperlink and its 'attributes'."

        for name, value in attributes:
            if name == "href":
                self.hyperlinks.append(value)

    def get_hyperlinks(self):
        "Return the list of hyperlinks."
        return self.hyperlinks


#######################
#   checkupstream
#######################

def labelMap(label):
    #pass
    #conary.repository.netclient
    #nc.getTroveVersionsByLabel({None: {Label('centos6.rpath.com@rpath:centos-6-common'): None}})
    cfg = conarycfg.ConaryConfiguration(True)
    client = conaryclient.ConaryClient(cfg)
    repos = client.getRepos()
    print "DEBUG: getting all troves for %s" % label
    troves = repos.getTroveVersionsByLabel({None: {Label(label): None}})
    cleantroves = []
    for name, versions in troves.iteritems():
        for version, flavors in versions.iteritems():
            for flavor in flavors:
                nvf = name, version, flavor
                cleantroves.append(nvf)
    #self.repomaps = self.repomaps + troves
    #epdb.st()
    #return troves
    return cleantroves
    #epdb.st()

def getTroveNevra(pkgname):
    cfg = conarycfg.ConaryConfiguration(True)
    client = conaryclient.ConaryClient(cfg)
    repos = client.getRepos()    
    epdb.st()

def isInLabel(pkgname, pkgversion, pkgarch, pkglabel):

    # http://cvs.rpath.com/conary-docs/conary.conaryclient.cmdline-module.html
    trvSpec = conaryclient.cmdline.parseTroveSpec(pkgname + "=" + pkglabel)
    #epdb.st()
    cfg = conarycfg.ConaryConfiguration(True)
    client = conaryclient.ConaryClient(cfg)
    repos = client.getRepos()

    match = 'NULL'
    bestratio = 0

    #epdb.st()
    try:
        print "INFO: checking for %s upstream" % pkgname
        trvs = repos.findTrove(None, trvSpec, getLeaves=False)
    except:
        print "INFO: no matching troves upstream for %s" % pkgname
        return match

    for trv in trvs:
        conaryname = str(trv[0])
        flavorarry=str(trv[2]).split(':')       # Flavor('is: x86_64'))
        flavor = flavorarry[1]                  # x86_64, x86(i486,i586,i686), x86(i486,i586,i686)
        flavor = flavor.lstrip()        #remove leading whitespace
        versarry=str(trv[1]).split('/') # label, version
        label= versarry[1]
        conaryversion =  versarry[2]
        #strip the conary source and build versions
        rpmversion = conary2rpmversion(conaryversion)
        #calculate version match percentage
        m = SequenceMatcher(None, rpmversion, pkgversion)

        print "DEBUG: %s %s %s (%s) matches by %s percent" % (pkgname, pkgversion, conaryversion, rpmversion, m.ratio())

        if ((rpmversion == pkgversion) 
             and ((flavor2arch(flavor) == pkgarch) or pkgarch == 'noarch')):

            bestratio = m.ratio()
            match = conaryname + '=/' + label + '/' + conaryversion + '[' + flavor + ']'

        elif ((m.ratio() >= 0.8) 
             and ((flavor2arch(flavor) == pkgarch) or (pkgarch == 'noarch'))
             and ((match == 'NULL') or (m.ratio() >= bestratio))):

            #if there is no exact match, allow a 20% tolerance on the version matching
            # to help correct against the fact that conary versions do not have hyphens
            # and it's impossible to convert reliably
            bestratio = m.ratio()
            match = conaryname + '=/' + label + '/' + conaryversion + '[' + flavor + ']'
   
    return match 


def getNevrasOLD(label):
    cfg = conarycfg.ConaryConfiguration(True)
    client = conaryclient.ConaryClient(cfg)

    tvers = client.repos.getTroveVersionsByLabel({None: {label: None}})

    specs = []
    for n, vs in tvers.iteritems():
        if not n.endswith(':rpm'):
            continue
        for v, fs in vs.iteritems():
            for f in fs:
                specs.append((n, v, f))

    capsuleInfo = client.repos.getTroveInfo(trove._TROVEINFO_TAG_CAPSULE, specs)

    for spec, info in itertools.izip(specs, capsuleInfo):
        r = info.rpm
        nevra = NEVRA(r.name(), r.epoch(), r.version(), r.release(), r.arch())
        yield spec, nevra
    
 

def conary2rpmversion(conaryversion):
    p = re.compile(r'(\-)\s*\d{1,2}')
    tmparray =  filter(None, p.split(conaryversion))
    rpmversion = tmparray[0]
    rpmversion = rpmversion.replace('_', '-')   #convert underscores to hyphens 
    return rpmversion

def flavor2arch(flavor):
    #rpms are noarch, x86_64, i386 and i686
    # How do I deal with noarch rpms? The conary packages
    # have binary based flavors for noarch.
    arch = ''
    #print "DEBUG:		flavor -- %s" % flavor
    if flavor == 'is: x86_64':
        arch = 'x86_64'
    elif flavor == 'is: x86 x86_64':
        arch = 'x86_64'
    elif flavor == 'is: x86(i486,i586,i686)':
        arch = 'i386'
    elif flavor == 'is: x86(i486,i586,i686,sse,sse2)':
        arch = 'i686'
    elif flavor == 'is: x86(~!i486,~!i586,~!i686,~!sse2)':
        arch = 'i686'
    elif flavor == '~!kernel.debug,~!kernel.pae,~kernel.smp,~!xen is: x86_64':
        arch = 'x86_64'
    elif flavor == 'domU,~!kernel.debug,~kernel.pae,~kernel.smp,xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~kernel.debug,~!kernel.pae,~kernel.smp,~!xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~kernel.debug,~!kernel.pae,~kernel.smp,~!xen is: x86_64':
        arch = 'x86_64'
    elif flavor == 'domU,~!kernel.debug,~!kernel.pae,~kernel.smp,xen is: x86_64':
        arch = 'x86_64'
    elif flavor == '~!kernel.debug,~!kernel.pae,~kernel.smp,~!xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~!kernel.debug,~kernel.pae,~kernel.smp,~!xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~kernel.debug,~!xen is: x86_64':
        arch = 'x86_64'
    elif flavor == '~kernel.debug,~!xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~!be2iscsi-kmod.pae,~be2iscsi-kmod.smp,~!xen is: x86_64':
        arch = 'x86_64'
    elif flavor == '~be2iscsi-kmod.pae,~be2iscsi-kmod.smp,~!xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~be2iscsi-kmod.pae,~be2iscsi-kmod.smp,~!dom0,domU,xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~!be2iscsi-kmod.pae,~be2iscsi-kmod.smp,~!dom0,domU,xen is: x86_64':
        arch = 'x86_64'
    elif flavor == '~!be2iscsi-kmod.pae,~be2iscsi-kmod.smp,~!xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~!dom0,domU,~igb-kmod.pae,~igb-kmod.smp,xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~!igb-kmod.pae,~igb-kmod.smp,~!xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~!igb-kmod.pae,~igb-kmod.smp,~!xen is: x86_64':
        arch = 'x86_64'
    elif flavor == '~igb-kmod.pae,~igb-kmod.smp,~!xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~!dom0,domU,~!igb-kmod.pae,~igb-kmod.smp,xen is: x86_64':
        arch = 'x86_64'
    elif flavor == '~!be2net-kmod.pae,~be2net-kmod.smp,~!xen is: x86_64':
        arch = 'x86_64'
    elif flavor == '~!be2net-kmod.pae,~be2net-kmod.smp,~!dom0,domU,xen is: x86_64':
        arch = 'x86_64'
    elif flavor == '~be2net-kmod.pae,~be2net-kmod.smp,~!xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~!dom0,domU,~!lpfc-kmod.pae,~lpfc-kmod.smp,xen is: x86_64':
        arch = 'x86_64'
    elif flavor == '~!dom0,domU,~lpfc-kmod.pae,~lpfc-kmod.smp,xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~!lpfc-kmod.pae,~lpfc-kmod.smp,~!xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~!lpfc-kmod.pae,~lpfc-kmod.smp,~!xen is: x86_64':
        arch = 'x86_64'
    elif flavor == '~lpfc-kmod.pae,~lpfc-kmod.smp,~!xen is: x86(i486,i586,i686)':
        arch = 'i686'
    elif flavor == '~!kvm.pae,~kvm.smp,~!xen is: x86_64':
        arch = 'x86_64'
    else:
        epdb.st()
        print "ERROR: %s not a known flavor" % flavor
        arch = 'NULL'

    return arch


###############################################################################################
#					    MAIN
###############################################################################################

print "RUNNING ... "

#########################
# init REPOS Object 
#########################

X = yumRepos()

host = 'http://wwwin-kickstart-rcdn.cisco.com/yum/'

urls = ['5.50-5Server/emergency-bsh-dev-update/i386',
	'5.50-5Server/emergency-bsh-dev-update/x86_64',
	'5.50-5Server/emergency-update/i386',
	'5.50-5Server/emergency-update/x86_64',
	'5.50-5Server/emergency-bsh-dev-install/i386',
	'5.50-5Server/emergency-bsh-dev-install/x86_64',
	'5.50-5Server/cisco-linux-server/i386',
	'5.50-5Server/cisco-linux-server/x86_64',
	'5.50-5Server/emergency-bsh-prod-update/i386',
	'5.50-5Server/emergency-bsh-prod-update/x86_64',
	'5.50-5Server/emergency-bsh-dmz-update/i386',
	'5.50-5Server/emergency-bsh-dmz-update/x86_64',
	'5.50-5Server/emergency-install/i386',
	'5.50-5Server/emergency-install/x86_64',
	'5.50-5Server/emergency-engineering-update/i386',
	'5.50-5Server/emergency-engineering-update/x86_64',
	'5.50-5Server/base/i386/Cluster',
	'5.50-5Server/base/i386/Server',
	'5.50-5Server/base/i386/ClusterStorage',
	'5.50-5Server/base/i386/VT',
	'5.50-5Server/base/x86_64/Cluster',
	'5.50-5Server/base/x86_64/Server',
	'5.50-5Server/base/x86_64/ClusterStorage',
	'5.50-5Server/base/x86_64/VT',
	'5.50-5Server/emergency-bsh-prod-install/i386',
	'5.50-5Server/emergency-bsh-prod-install/x86_64',
	'5.50-5Server/emergency-bsh-stage-install/i386',
	'5.50-5Server/emergency-bsh-stage-install/x86_64',
	'5.50-5Server/cisco-linux-common/i386',
	'5.50-5Server/cisco-linux-common/x86_64',
	'5.50-5Server/emergency-bsh-stage-update/i386',
	'5.50-5Server/emergency-bsh-stage-update/x86_64',
	'5.50-5Server/emergency-bsh-dmz-install/i386',
	'5.50-5Server/emergency-bsh-dmz-install/x86_64',
	'5.50-5Server/emergency-engineering-install/i386',
	'5.50-5Server/emergency-engineering-install/x86_64',
        'auto-repos/5Server/bsh-prod-install/x86_64',
        'auto-repos/5Server/bsh-dev-update/x86_64',
        'auto-repos/5Server/bsh-dmz-update/x86_64',
        'auto-repos/5Server/bsh-dev-install/x86_64',
        'auto-repos/5Server/bsh-stage-install/x86_64',
        'auto-repos/5Server/bsh-stage-update/x86_64',
        'auto-repos/5Server/engineering-update/x86_64',
        'auto-repos/5Server/bsh-prod-update/x86_64',
        'auto-repos/5Server/engineering-install/x86_64',
        'auto-repos/5Server/bsh-dmz-install/x86_64',
        'auto-repos/5Server/bsh-prod-install/i386',
        'auto-repos/5Server/bsh-dev-update/i386',
        'auto-repos/5Server/bsh-dmz-update/i386',
        'auto-repos/5Server/bsh-dev-install/i386',
        'auto-repos/5Server/bsh-stage-install/i386',
        'auto-repos/5Server/bsh-stage-update/i386',
        'auto-repos/5Server/engineering-update/i386',
        'auto-repos/5Server/bsh-prod-update/i386',
        'auto-repos/5Server/engineering-install/i386',
        'auto-repos/5Server/bsh-dmz-install/i386',
	]

#########################
# Scan labels for data 
#########################

# Find out what already exists upstream and downstream
#X.createLocalMap('celmb1.cisco.com@c:celmb1-trunk-devel')
#epdb.st()
#X.createLabelMap('rhel.rpath.com@rpath:rhel-5-server')
#epdb.st()

#NEVRA = namedtuple('NEVRA', 'name epoch version release arch')
#label = versions.Label('celmb1.cisco.com@c:celmb1-trunk-devel')

#epdb.st()
#for trvSpec, nevra in getNevras(label):
#    epdb.st()


########################
# Yum repo parsing 
########################

# Scan and import each repo
for url in urls:
    #epdb.st()
    fullurl = host + url
    X.createRepo(fullurl)

# NEVRA sort
X.latestPackages()
X.sortPackages()

# Group dedupe
X.uniqueGroups()
#epdb.st()


########################
# match rpms to troves 
########################

'''
print "DEBUG: checking upstream sources"
X.checkUpstreamSources()
'''

print "DEBUG: checking local sources"
#X.checkLocalSources()
X.checkLabelsAPI('celmb1.cisco.com@c:celmb1-trunk-devel', 'rhel.rpath.com@rpath:rhel-5-server')
#epdb.st()


########################
# output results
########################


now = datetime.datetime.now()
dirName = now.strftime("%Y-%m-%d-%H-%M")
#dirName = str(now.year) + "-" + str(now.month) + "-" + str(now.day) + "-" + str(now.hour) + "-" + str(now.minute) 
X.outputPackageManifest(dirName)
X.outputGroupManifest(dirName)
X.outputGroupRecipe(dirName)
X.outputMissingPackages(dirName)

