from conary import conarycfg, conaryclient, trove
from conary import repository
from conary import versions
from conary.lib.compat import namedtuple
from conary.versions import Label

import itertools

#def checkLabelsAPI(self, locallabel, upstreamlabel):
def findYumPackagesInLabel(yumrepos, upstreamlabel, downstreamlabel):

    # given a yumrepo object, check if the packages exist upstream or downstream

    NEVRA = namedtuple('NEVRA', 'name epoch version release arch')
    dlabel = versions.Label(downstreamlabel)
    ulabel = versions.Label(upstreamlabel)

    print "DEBUG: matching packages to local troves in label %s " % dlabel
    for trvSpec, nevra in _getNevras(NEVRA, dlabel):

        # ('CSCOsars:rpm', VFS('/celmb1.cisco.com@c:celmb1-trunk-devel/1.0.1_0-1-1'), Flavor('is: x86_64'))
        # trvSpec[0] = 'CSCOsars:rpm'
        # trvSpec[1] = VFS('/celmb1.cisco.com@c:celmb1-trunk-devel/1.0.1_0-1-1')
        # trvSpec[2] = Flavor('is: x86_64')


        for pkg in yumrepos.latestpackages:
            trovespec = ""
            #print "\t%s" % pkg.name

            # Why is nevra.epcoh = None ?

            if ((pkg.name == nevra.name) and
               (pkg.version == nevra.version) and
               (pkg.release == nevra.release) and
               (pkg.arch == nevra.arch)):

               trovespec = str(nevra.name) + "=" + str(trvSpec[1]) + "[" + str(trvSpec[2]) + "]"
               pkg.downstream = True
               pkg.localtrove = trovespec

               print "MATCH: %s %s" %(pkg.url, trovespec)
               #epdb.st()


    print "DEBUG: matching packages to upstream troves in label %s " % ulabel
    for trvSpec, nevra in _getNevras(NEVRA, ulabel):

        # ('CSCOsars:rpm', VFS('/celmb1.cisco.com@c:celmb1-trunk-devel/1.0.1_0-1-1'), Flavor('is: x86_64'))
        # trvSpec[0] = 'CSCOsars:rpm'
        # trvSpec[1] = VFS('/celmb1.cisco.com@c:celmb1-trunk-devel/1.0.1_0-1-1')
        # trvSpec[2] = Flavor('is: x86_64')

        #epdb.st()
        for pkg in yumrepos.latestpackages:
            trovespec = ""
            #print "\t%s" % pkg.name

            # Why is nevra.epcoh = None ?

            if ((pkg.name == nevra.name) and
               (pkg.version == nevra.version) and
               (pkg.release == nevra.release) and
               (pkg.arch == nevra.arch)):

               trovespec = str(nevra.name) + "=" + str(trvSpec[1]) + "[" + str(trvSpec[2]) + "]"
               pkg.upstream = True
               pkg.upstreamtrove = trovespec

               print "MATCH: %s %s" %(pkg.url, trovespec)
               #epdb.st()
    #import epdb; epdb.st()
    return yumrepos

def _getNevras(NEVRA, label):
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
