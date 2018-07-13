from setuptools import setup

setup(name='mosaic',
      version='0.1',
      description='Code for generating point spread functions and beam tiling for radio interferometers',
      url='https://gitlab.mpifr-bonn.mpg.de/wchen/Beamforming/',
      author='Weiwei Chen',
      author_email='wchen@mpifr-bonn.mpg.de',
      license='MIT',
      packages=['mosaic'],
      install_requires=[
          'scipy',
          'numpy',
          'matplotlib',
          'katpoint',
          'h5py',
          'nvector',
          'astropy'
      ],
      zip_safe=False)