#!/usr/bin/python

#from yumrepo import yumRepo
from rbuild_plugins.yumcheckout.repomd.yumrepo import yumRepo
from linkparser import *
from yumpackage import *
from yumgroup import *


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
        print "yumrepos.createRepo adding repo: %s" % url
        #epdb.st()
        X = yumRepo(url)
        self.addRepo(X)

    def findAllLatestPackages(self):
        manifest = []
        for pkg in self.packages:
            #epdb.st()
            manifest.append(self.findLatestPackage(pkg.name, pkg.arch))
        return manifest


