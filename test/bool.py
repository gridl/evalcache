#!/usr/bin/python3

import sys
sys.path.insert(0, "..")

import evalcache
lazy = evalcache.Lazy(cache = evalcache.DirCache(".evalcache"))

a = lazy(0)

if a:
	print(True)