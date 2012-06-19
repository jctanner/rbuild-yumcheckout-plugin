def findKindredPkgs(pkglist):
    #kindred = mdict
    kindredpkgs = {}

    for pkg in pkglist:
        #print pkg.name
        if not kindredpkgs.has_key(pkg.name):
            kindredpkgs[pkg.name] = []
        kindredpkgs[pkg.name].append(pkg)
        #uniquepkgnames[pkg.name] = pkg


    #for key in sorted(kindredpkgs.keys()):
    #    for pkg in kindredpkgs[key]:
    #        print pkg.name + pkg.version + pkg.arch

    return kindredpkgs
