from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
import numpy

ext_modules = [Extension("BSSeval", ["bss_eval_images_nosort.pyx"],
                         include_dirs=[numpy.get_include()],
                         language="c++" # this is for mac, for the compiler to use g++ and not gcc
                         )]

setup(
  name = 'BSS Eval python implementation',
  cmdclass = {'build_ext': build_ext},
  ext_modules = ext_modules
)
Extension
