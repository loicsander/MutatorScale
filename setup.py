#!/usr/bin/env python

from distutils.core import setup

setup(name = "MutatorScale",
      version = "0.6",
      description = "Tool for interpolated glyph scaling, based on Robofab, FontTools & MutatorMath.",
      author = "Loic Sander",
      author_email = "loic@akalollip.com",
      url = "https://github.com/loicsander/MutatorScale",
      license = "MIT",
      packages = [
              "mutatorScale",
              "mutatorScale.booleanOperations",
              "mutatorScale.objects",
              "mutatorScale.pens",
              "mutatorScale.utilities",
      ],
      package_dir = {"":"lib"},
)
